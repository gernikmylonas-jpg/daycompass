from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import StepLog, SleepLog, User
from app.application.schemas import (
    StepLogUpsert, StepLogResponse, SleepLogUpsert, SleepLogResponse, WellnessDay, WellnessSummary,
)
from app.application.services.points import (
    STEP_GOAL, SLEEP_GOAL_MINUTES, POINTS_PER_STEP_GOAL, POINTS_PER_SLEEP_GOAL,
)
from app.application.services.realtime import notify_user_groups

router = APIRouter(prefix="/api/wellness", tags=["wellness"])

MAX_STEPS = 100_000
MAX_SLEEP_MINUTES = 24 * 60
MAX_BACKFILL_DAYS = 30
SUMMARY_DAYS = 14


def _resolve_date(requested: date | None) -> date:
    today = date.today()
    day = requested or today
    if day > today:
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if (today - day).days > MAX_BACKFILL_DAYS:
        raise HTTPException(status_code=422, detail=f"Date cannot be older than {MAX_BACKFILL_DAYS} days")
    return day


def _award(db: Session, user_id: str, log, goal_met: bool, points: int) -> int:
    """Points are granted once per log row (the first time its goal is met) and never revoked on edits."""
    if not goal_met or log.points_awarded:
        return 0
    log.points_awarded = points
    db.query(User).filter(User.id == user_id).update({User.total_points: User.total_points + points})
    return points


@router.put("/steps", response_model=StepLogResponse)
def log_steps(payload: StepLogUpsert, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not 0 <= payload.steps <= MAX_STEPS:
        raise HTTPException(status_code=422, detail=f"Steps must be between 0 and {MAX_STEPS}")
    day = _resolve_date(payload.log_date)

    log = db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.log_date == day).first()
    if log is None:
        log = StepLog(user_id=user_id, log_date=day, steps=payload.steps, points_awarded=0)
        db.add(log)
    else:
        log.steps = payload.steps

    gained = _award(db, user_id, log, log.steps >= STEP_GOAL, POINTS_PER_STEP_GOAL)
    db.commit()
    if gained:
        notify_user_groups(db, user_id)
    return StepLogResponse(
        log_date=day, steps=log.steps, goal_reached=log.steps >= STEP_GOAL, points_awarded=gained,
    )


@router.put("/sleep", response_model=SleepLogResponse)
def log_sleep(payload: SleepLogUpsert, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not 0 <= payload.minutes <= MAX_SLEEP_MINUTES:
        raise HTTPException(status_code=422, detail="Sleep must be between 0 and 24 hours")
    if payload.quality is not None and not 1 <= payload.quality <= 5:
        raise HTTPException(status_code=422, detail="Quality must be between 1 and 5")
    day = _resolve_date(payload.log_date)

    log = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.log_date == day).first()
    if log is None:
        log = SleepLog(user_id=user_id, log_date=day, minutes=payload.minutes, quality=payload.quality, points_awarded=0)
        db.add(log)
    else:
        log.minutes = payload.minutes
        log.quality = payload.quality

    gained = _award(db, user_id, log, log.minutes >= SLEEP_GOAL_MINUTES, POINTS_PER_SLEEP_GOAL)
    db.commit()
    if gained:
        notify_user_groups(db, user_id)
    return SleepLogResponse(
        log_date=day, minutes=log.minutes, quality=log.quality,
        goal_reached=log.minutes >= SLEEP_GOAL_MINUTES, points_awarded=gained,
    )


@router.get("/summary", response_model=WellnessSummary)
def summary(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    today = date.today()
    since = today - timedelta(days=SUMMARY_DAYS - 1)
    steps = {
        l.log_date: l.steps
        for l in db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.log_date >= since)
    }
    sleeps = {
        l.log_date: l
        for l in db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.log_date >= since)
    }

    days = []
    for offset in range(SUMMARY_DAYS):
        d = since + timedelta(days=offset)
        sl = sleeps.get(d)
        days.append(WellnessDay(
            date=d,
            steps=steps.get(d),
            sleep_minutes=sl.minutes if sl else None,
            sleep_quality=sl.quality if sl else None,
        ))

    last7 = days[-7:]
    step_values = [d.steps for d in last7 if d.steps is not None]
    sleep_values = [d.sleep_minutes for d in last7 if d.sleep_minutes is not None]
    return WellnessSummary(
        step_goal=STEP_GOAL,
        sleep_goal_minutes=SLEEP_GOAL_MINUTES,
        avg_steps_7d=round(sum(step_values) / len(step_values)) if step_values else 0,
        avg_sleep_minutes_7d=round(sum(sleep_values) / len(sleep_values)) if sleep_values else 0,
        days=days,
    )
