"""Shared habits inside a group (everyone checks in on the same habit, the group builds a streak together)
and small cheers (one emoji per person per day). Only members of the group can see or do anything here."""
from datetime import date, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.services.realtime import notify_groups
from app.application.schemas import BadgeInfo
from app.application.services.badges import award_badges
from app.domain.models import Cheer, Group, GroupHabit, GroupHabitCheck, GroupMember, User
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/groups/{group_id}", tags=["group-habits"])

MAX_NAME = 60
MAX_HABITS = 10
CHEERS = {"👏", "💪", "🔥", "❤️", "🎉"}


class HabitIn(BaseModel):
    name: str


class CheerIn(BaseModel):
    to_user_id: UUID
    emoji: str


def _members(db: Session, group_id: UUID, user_id: str) -> list[User]:
    group = db.query(Group).filter(Group.id == group_id).first()
    people = db.query(User).join(GroupMember, GroupMember.user_id == User.id).filter(GroupMember.group_id == group_id).all() if group else []
    if not any(str(u.id) == str(user_id) for u in people):
        raise HTTPException(status_code=404, detail="Group not found")
    return people


def _habit_view(db: Session, h: GroupHabit, people: list[User], me: str) -> dict:
    today = date.today()
    ids = [u.id for u in people]
    checks = db.query(GroupHabitCheck.user_id, GroupHabitCheck.check_date).filter(
        GroupHabitCheck.habit_id == h.id, GroupHabitCheck.check_date >= today - timedelta(days=400)).all()
    by_day: dict[date, set] = {}
    for uid, d in checks:
        by_day.setdefault(d, set()).add(uid)
    everyone = set(ids)
    day = today if by_day.get(today, set()) >= everyone else today - timedelta(days=1)  # today may still be in progress
    streak = 0
    while by_day.get(day, set()) >= everyone and everyone:
        streak += 1
        day -= timedelta(days=1)
    done_today = by_day.get(today, set())
    return {
        "id": h.id, "name": h.name, "group_streak": streak, "all_done_today": bool(everyone) and done_today >= everyone,
        "done_today": len(done_today & everyone), "members_total": len(everyone),
        "me_done": any(str(u) == str(me) for u in done_today),
        "members": [{"user_id": u.id, "name": u.name, "done": u.id in done_today} for u in people],
    }


@router.get("/habits")
def list_habits(group_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    people = _members(db, group_id, user_id)
    habits = db.query(GroupHabit).filter(GroupHabit.group_id == group_id).order_by(GroupHabit.created_at).all()
    return [_habit_view(db, h, people, user_id) for h in habits]


@router.post("/habits")
def add_habit(group_id: UUID, payload: HabitIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    people = _members(db, group_id, user_id)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_NAME} characters)")
    if db.query(GroupHabit).filter(GroupHabit.group_id == group_id).count() >= MAX_HABITS:
        raise HTTPException(status_code=422, detail="Too many shared habits")
    h = GroupHabit(group_id=group_id, name=name, created_by=user_id)
    db.add(h)
    db.commit()
    notify_groups([group_id])
    return _habit_view(db, h, people, user_id)


@router.post("/habits/{habit_id}/check")
def check(group_id: UUID, habit_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    people = _members(db, group_id, user_id)
    h = db.query(GroupHabit).filter(GroupHabit.id == habit_id, GroupHabit.group_id == group_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habit not found")
    today = date.today()
    if db.query(GroupHabitCheck.id).filter(GroupHabitCheck.habit_id == h.id, GroupHabitCheck.user_id == user_id, GroupHabitCheck.check_date == today).first():
        raise HTTPException(status_code=409, detail="Already checked in today")
    db.add(GroupHabitCheck(habit_id=h.id, user_id=user_id, check_date=today))
    new_badges = award_badges(db, user_id)
    db.commit()
    notify_groups([group_id])
    return {**_habit_view(db, h, people, user_id), "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}


@router.delete("/habits/{habit_id}")
def delete_habit(group_id: UUID, habit_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _members(db, group_id, user_id)
    h = db.query(GroupHabit).filter(GroupHabit.id == habit_id, GroupHabit.group_id == group_id).first()
    group = db.query(Group).filter(Group.id == group_id).first()
    if not h:
        raise HTTPException(status_code=404, detail="Habit not found")
    if str(h.created_by) != str(user_id) and str(group.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Only the creator or the group owner can delete this habit")
    db.query(GroupHabitCheck).filter(GroupHabitCheck.habit_id == h.id).delete(synchronize_session=False)
    db.delete(h)
    db.commit()
    notify_groups([group_id])
    return {"detail": "Habit deleted"}


# ── cheers ────────────────────────────────────────────────────────────────
@router.get("/cheers")
def cheers_today(group_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _members(db, group_id, user_id)
    rows = db.query(Cheer, User).join(User, User.id == Cheer.from_user).filter(
        Cheer.group_id == group_id, Cheer.cheer_date == date.today()).all()
    mine = [{"from": u.name, "emoji": c.emoji} for c, u in rows if str(c.to_user) == str(user_id)]
    sent = [str(c.to_user) for c, _u in rows if str(c.from_user) == str(user_id)]
    return {"received": mine, "sent_to": sent, "options": sorted(CHEERS)}


@router.post("/cheers")
def send_cheer(group_id: UUID, payload: CheerIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    people = _members(db, group_id, user_id)
    if payload.emoji not in CHEERS:
        raise HTTPException(status_code=422, detail="Invalid emoji")
    if str(payload.to_user_id) == str(user_id) or not any(u.id == payload.to_user_id for u in people):
        raise HTTPException(status_code=422, detail="Choose someone else in the group")
    today = date.today()
    if db.query(Cheer.id).filter(Cheer.group_id == group_id, Cheer.from_user == user_id, Cheer.to_user == payload.to_user_id, Cheer.cheer_date == today).first():
        raise HTTPException(status_code=409, detail="You already cheered them today")
    db.add(Cheer(group_id=group_id, from_user=user_id, to_user=payload.to_user_id, emoji=payload.emoji, cheer_date=today))
    new_badges = award_badges(db, user_id)
    db.commit()
    notify_groups([group_id])
    return {"detail": "Sent", "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}
