"""Personal goals with a deadline: "20,000 steps by the 1st", "15 check-ins this month".
They count the same things as group challenges, from your own activity. Nothing is created unless you create it."""
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.services.challenges import METRICS, member_progress
from app.application.services.badges import award_badges
from app.domain.models import Goal
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/goals", tags=["goals"])

MAX_TITLE = 80
MAX_TARGET = 10_000_000
MAX_DAYS = 3 * 366
MAX_GOALS = 50


class GoalIn(BaseModel):
    title: str
    metric: str
    target: int
    start_date: date
    end_date: date


def _out(db: Session, g: Goal, user_id: str) -> dict:
    today = date.today()
    progress = member_progress(db, g.metric, [g.user_id], g.start_date, g.end_date).get(g.user_id, 0)
    done = progress >= g.target
    status = "done" if done else "upcoming" if today < g.start_date else "missed" if today > g.end_date else "active"
    days_left = max(0, (g.end_date - today).days + 1) if status in ("active", "upcoming") else 0
    # what is needed per remaining day to still make it (a gentle nudge, shown only while active)
    per_day = None
    if status == "active" and days_left:
        per_day = -(-(g.target - progress) // days_left)
    return {
        "id": g.id, "title": g.title, "metric": g.metric, "target": g.target,
        "start_date": g.start_date, "end_date": g.end_date, "progress": int(progress),
        "percent": min(100, round(progress * 100 / g.target)), "status": status,
        "days_left": days_left, "needed_per_day": per_day,
    }


@router.get("")
def list_goals(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    goals = db.query(Goal).filter(Goal.user_id == user_id).order_by(Goal.end_date).all()
    out = [_out(db, g, user_id) for g in goals]
    award_badges(db, user_id)  # reaching a goal earns its badge the next time goals are looked at
    db.commit()
    return out


@router.post("")
def create_goal(payload: GoalIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(title) > MAX_TITLE:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_TITLE} characters)")
    if payload.metric not in METRICS:
        raise HTTPException(status_code=422, detail="Invalid metric")
    if not 1 <= payload.target <= MAX_TARGET:
        raise HTTPException(status_code=422, detail=f"Target must be between 1 and {MAX_TARGET}")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (payload.end_date - payload.start_date).days + 1 > MAX_DAYS:
        raise HTTPException(status_code=422, detail=f"Range is limited to {MAX_DAYS} days")
    if db.query(Goal).filter(Goal.user_id == user_id).count() >= MAX_GOALS:
        raise HTTPException(status_code=422, detail="Too many goals")
    g = Goal(user_id=user_id, title=title, metric=payload.metric, target=payload.target,
             start_date=payload.start_date, end_date=payload.end_date)
    db.add(g)
    db.commit()
    db.refresh(g)
    return _out(db, g, user_id)


@router.delete("/{goal_id}")
def delete_goal(goal_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    g = db.query(Goal).filter(Goal.id == goal_id, Goal.user_id == user_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Goal not found")
    db.delete(g)
    db.commit()
    return {"detail": "Goal deleted"}
