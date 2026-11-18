from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.domain.models import (
    CheckIn, Habit, StepLog, SleepLog, PomodoroSession, MeditationSession, JournalEntry, MoodLog,
)
from app.application.services.points import SLEEP_GOAL_MINUTES

# what a challenge can count, per member, between its start and end date (inclusive)
METRICS = ("checkins", "steps", "meditation_minutes", "pomodoros", "sleep_nights", "journal_entries", "mood_logs")


def member_progress(db: Session, metric: str, user_ids: list, start: date, end: date) -> dict:
    result = {uid: 0 for uid in user_ids}
    if not user_ids:
        return result

    if metric == "checkins":
        q = (
            db.query(Habit.user_id, func.count(CheckIn.id))
            .join(CheckIn, CheckIn.habit_id == Habit.id)
            .filter(Habit.user_id.in_(user_ids), CheckIn.completed.is_(True), CheckIn.check_date.between(start, end))
            .group_by(Habit.user_id)
        )
    elif metric == "steps":
        q = db.query(StepLog.user_id, func.sum(StepLog.steps)).filter(
            StepLog.user_id.in_(user_ids), StepLog.log_date.between(start, end)).group_by(StepLog.user_id)
    elif metric == "meditation_minutes":
        q = db.query(MeditationSession.user_id, func.sum(MeditationSession.duration_minutes)).filter(
            MeditationSession.user_id.in_(user_ids), MeditationSession.session_date.between(start, end)
        ).group_by(MeditationSession.user_id)
    elif metric == "pomodoros":
        q = db.query(PomodoroSession.user_id, func.count(PomodoroSession.id)).filter(
            PomodoroSession.user_id.in_(user_ids), PomodoroSession.session_date.between(start, end)
        ).group_by(PomodoroSession.user_id)
    elif metric == "sleep_nights":
        q = db.query(SleepLog.user_id, func.count(SleepLog.id)).filter(
            SleepLog.user_id.in_(user_ids), SleepLog.minutes >= SLEEP_GOAL_MINUTES, SleepLog.log_date.between(start, end)
        ).group_by(SleepLog.user_id)
    elif metric == "journal_entries":
        q = db.query(JournalEntry.user_id, func.count(JournalEntry.id)).filter(
            JournalEntry.user_id.in_(user_ids), JournalEntry.entry_date.between(start, end)
        ).group_by(JournalEntry.user_id)
    elif metric == "mood_logs":
        q = db.query(MoodLog.user_id, func.count(MoodLog.id)).filter(
            MoodLog.user_id.in_(user_ids), MoodLog.log_date.between(start, end)).group_by(MoodLog.user_id)
    else:
        return result

    for uid, value in q:
        result[uid] = int(value or 0)
    return result
