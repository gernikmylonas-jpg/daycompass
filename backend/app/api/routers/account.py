from datetime import datetime
from fastapi import APIRouter, Depends, Header, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id, verify_password
from app.application.services.group_cleanup import drop_group_extras
from app.domain.models import (
    WeightLog, WeightProfile, WallpaperUnlock, Goal, WaterLog, Workout, GratitudeEntry, QuestReward, ProfilePhoto, GroupHabit, GroupHabitCheck, Cheer, PushSubscription, PushLog,
    MoneyProfile, MoneyEntry, BudgetLimit, SavingsGoal, SavingsDeposit, Trip, PeriodDay,
    User, Habit, CheckIn, PomodoroSession, StepLog, SleepLog, MoodLog, MeditationSession, JournalEntry, JournalAudio,
    CalendarEvent, RestDay, UserBadge, Badge, UserSettings, ReminderSetting, ReminderLog, EventMailLog, JournalLock,
    Group, GroupMember, Challenge,
)
from app.api.routers.journal import get_cipher, _decrypt_text

router = APIRouter(prefix="/api/account", tags=["account"])


class DeleteAccount(BaseModel):
    password: str


@router.get("/export")
def export_data(
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Everything stored about the user as one JSON file. A locked journal is only included when
    the PIN is sent (recordings are listed but not embedded)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    check_ins = db.query(CheckIn.habit_id, CheckIn.check_date).filter(
        CheckIn.habit_id.in_([h.id for h in habits]), CheckIn.completed.is_(True)) if habits else []
    by_habit: dict = {}
    for habit_id, day in check_ins:
        by_habit.setdefault(habit_id, []).append(day)

    try:
        cipher = get_cipher(db, user_id, x_journal_pin)
        audio_ids = {a for (a,) in db.query(JournalAudio.entry_id)}
        journal = [
            {"date": e.entry_date, "mood": e.mood, "content": _decrypt_text(e, cipher), "has_audio": e.id in audio_ids,
             "created_at": e.created_at}
            for e in db.query(JournalEntry).filter(JournalEntry.user_id == user_id).order_by(JournalEntry.entry_date)
        ]
    except HTTPException:
        journal = {"locked": True, "note": "Send the journal PIN (X-Journal-Pin) to include the journal."}

    settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    mp = db.query(MoneyProfile).filter(MoneyProfile.user_id == user_id).first()
    wp = db.query(WeightProfile).filter(WeightProfile.user_id == user_id).first()
    data = {
        "exported_at": datetime.utcnow(),
        "profile": {"name": user.name, "email": user.email, "total_points": user.total_points},
        "settings": None if not settings else {
            "theme": settings.theme, "mode": settings.mode, "needle_cursor": settings.needle_cursor,
            "language": settings.language, "mood_style": settings.mood_style},
        "habits": [
            {"name": h.name, "category": h.category.value, "frequency": h.frequency,
             "check_ins": sorted(by_habit.get(h.id, []))} for h in habits],
        "pomodoro": [{"date": s.session_date, "kind": s.kind, "title": s.title, "minutes": s.duration_minutes}
                     for s in db.query(PomodoroSession).filter(PomodoroSession.user_id == user_id)],
        "steps": [{"date": s.log_date, "steps": s.steps} for s in db.query(StepLog).filter(StepLog.user_id == user_id)],
        "sleep": [{"date": s.log_date, "minutes": s.minutes, "quality": s.quality}
                  for s in db.query(SleepLog).filter(SleepLog.user_id == user_id)],
        "mood": [{"date": m.log_date, "score": m.score, "note": m.note} for m in db.query(MoodLog).filter(MoodLog.user_id == user_id)],
        "meditation": [{"date": m.session_date, "minutes": m.duration_minutes, "kind": m.kind}
                       for m in db.query(MeditationSession).filter(MeditationSession.user_id == user_id)],
        "journal": journal,
        "calendar_events": [
            {"date": e.event_date, "title": e.title, "kind": e.kind, "notes": e.notes, "repeat_yearly": e.repeat_yearly, "repeat_weekly": e.repeat_weekly}
            for e in db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id)],
        "weight": {
            "profile": {"height_cm": wp.height_cm, "goal_kg": wp.goal_kg, "unit": wp.unit, "show_bmi": wp.show_bmi} if wp else None,
            "entries": [{"date": w.log_date, "kg": w.kg} for w in db.query(WeightLog).filter(WeightLog.user_id == user_id).order_by(WeightLog.log_date)],
        },
        "wallpapers_unlocked": [{"id": w.wallpaper_id, "cost": w.cost, "unlocked_at": w.unlocked_at}
                                for w in db.query(WallpaperUnlock).filter(WallpaperUnlock.user_id == user_id)],
        "goals": [{"title": g.title, "metric": g.metric, "target": g.target, "start": g.start_date, "end": g.end_date}
                  for g in db.query(Goal).filter(Goal.user_id == user_id)],
        "water": [{"date": w.log_date, "glasses": w.glasses} for w in db.query(WaterLog).filter(WaterLog.user_id == user_id)],
        "workouts": [{"date": w.workout_date, "kind": w.kind, "minutes": w.minutes, "note": w.note} for w in db.query(Workout).filter(Workout.user_id == user_id)],
        "gratitude": [{"date": g.entry_date, "text": g.text} for g in db.query(GratitudeEntry).filter(GratitudeEntry.user_id == user_id)],
        "quests_completed": [{"date": q.reward_date, "quest": q.quest_id} for q in db.query(QuestReward).filter(QuestReward.user_id == user_id)],
        "has_profile_photo": db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first() is not None,
        "push_devices": db.query(PushSubscription).filter(PushSubscription.user_id == user_id).count(),
        "money": {
            "currency": mp.currency if mp else None, "monthly_budget_cents": mp.monthly_budget_cents if mp else None,
            "entries": [{"date": m.entry_date, "kind": m.kind, "amount_cents": m.amount_cents, "category": m.category, "note": m.note, "trip": str(m.trip_id) if m.trip_id else None}
                        for m in db.query(MoneyEntry).filter(MoneyEntry.user_id == user_id)],
            "limits": [{"category": l.category, "monthly_cents": l.monthly_cents} for l in db.query(BudgetLimit).filter(BudgetLimit.user_id == user_id)],
            "trips": [{"id": str(t.id), "name": t.name, "start": t.start_date, "end": t.end_date, "currency": t.currency, "budget_cents": t.budget_cents}
                      for t in db.query(Trip).filter(Trip.user_id == user_id)],
            "savings": [{"name": g.name, "kind": g.kind, "target_cents": g.target_cents, "deadline": g.deadline,
                         "deposits": [{"date": d.entry_date, "amount_cents": d.amount_cents, "note": d.note} for d in db.query(SavingsDeposit).filter(SavingsDeposit.goal_id == g.id)]}
                        for g in db.query(SavingsGoal).filter(SavingsGoal.user_id == user_id)],
        },
        "period_days": [{"date": d.day, "flow": d.flow, "note": d.note} for d in db.query(PeriodDay).filter(PeriodDay.user_id == user_id)],
        "rest_days": [r.rest_date for r in db.query(RestDay).filter(RestDay.user_id == user_id)],
        "badges": [{"code": code, "awarded_at": at} for code, at in
                   db.query(Badge.code, UserBadge.awarded_at).join(UserBadge, UserBadge.badge_id == Badge.id).filter(UserBadge.user_id == user_id)],
        "groups": [{"name": g.name, "owner": str(g.owner_id) == str(user_id)} for g in
                   db.query(Group).join(GroupMember, GroupMember.group_id == Group.id).filter(GroupMember.user_id == user_id)],
    }
    return JSONResponse(
        content=jsonable_encoder(data),
        headers={"Content-Disposition": 'attachment; filename="daycompass-export.json"'},
    )


def delete_user_data(db: Session, user_id) -> None:
    """Removes the user and everything that belongs to them. Groups they own pass to the member
    who joined first; a group with nobody else in it is deleted."""
    for group in db.query(Group).filter(Group.owner_id == user_id).all():
        heir = (
            db.query(GroupMember).filter(GroupMember.group_id == group.id, GroupMember.user_id != user_id)
            .order_by(GroupMember.joined_at).first()
        )
        if heir:
            group.owner_id = heir.user_id
            for c in db.query(Challenge).filter(Challenge.group_id == group.id, Challenge.created_by == user_id):
                c.created_by = heir.user_id
        else:
            db.query(GroupMember).filter(GroupMember.group_id == group.id).delete(synchronize_session=False)
            db.query(Challenge).filter(Challenge.group_id == group.id).delete(synchronize_session=False)
            drop_group_extras(db, group.id)
            db.delete(group)
    db.flush()
    # what this person did inside groups that carry on without them
    db.query(GroupHabitCheck).filter(GroupHabitCheck.user_id == user_id).delete(synchronize_session=False)
    db.query(Cheer).filter((Cheer.from_user == user_id) | (Cheer.to_user == user_id)).delete(synchronize_session=False)
    for h in db.query(GroupHabit).filter(GroupHabit.created_by == user_id).all():
        h.created_by = db.query(Group.owner_id).filter(Group.id == h.group_id).scalar()
    db.flush()

    entry_ids = [e for (e,) in db.query(JournalEntry.id).filter(JournalEntry.user_id == user_id)]
    if entry_ids:
        db.query(JournalAudio).filter(JournalAudio.entry_id.in_(entry_ids)).delete(synchronize_session=False)
    db.query(SavingsDeposit).filter(SavingsDeposit.user_id == user_id).delete(synchronize_session=False)
    db.query(MoneyEntry).filter(MoneyEntry.user_id == user_id).delete(synchronize_session=False)
    habit_ids = [h for (h,) in db.query(Habit.id).filter(Habit.user_id == user_id)]
    if habit_ids:
        db.query(CheckIn).filter(CheckIn.habit_id.in_(habit_ids)).delete(synchronize_session=False)
    for model in (JournalEntry, Habit, MoodLog, MeditationSession, CalendarEvent, StepLog, SleepLog, PomodoroSession,
                  RestDay, WeightLog, WeightProfile, WallpaperUnlock, Goal, WaterLog, Workout, GratitudeEntry, QuestReward, ProfilePhoto, PushSubscription, PushLog,
                  SavingsGoal, Trip, BudgetLimit, MoneyProfile, PeriodDay, UserBadge, UserSettings, ReminderSetting, ReminderLog, EventMailLog, JournalLock, GroupMember):
        db.query(model).filter(model.user_id == user_id).delete(synchronize_session=False)
    db.query(User).filter(User.id == user_id).delete(synchronize_session=False)
    db.commit()


@router.delete("")
def delete_account(body: DeleteAccount, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is incorrect")
    delete_user_data(db, user_id)
    return {"detail": "Account deleted"}
