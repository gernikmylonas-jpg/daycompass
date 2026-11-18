from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import StepLog, SleepLog, User
from app.application.schemas import (
    StepLogUpsert, StepLogResponse, SleepLogUpsert, SleepLogResponse, WellnessDay, WellnessSummary, BadgeInfo, WellnessHistory,
)
from app.application.services.points import (
    STEP_GOAL, SLEEP_GOAL_MINUTES, POINTS_PER_STEP_GOAL, POINTS_PER_SLEEP_GOAL,
)
from app.application.services.realtime import notify_user_groups
from app.application.services.badges import award_badges

router = APIRouter(prefix="/api/wellness", tags=["wellness"])

MAX_STEPS = 100_000
MAX_SLEEP_MINUTES = 24 * 60
EARLIEST_DATE = date(2000, 1, 1)  # sanity floor only; there is no retention limit
SUMMARY_DAYS = 14


def _resolve_date(requested: date | None) -> date:
    today = date.today()
    day = requested or today
    if (day - today).days > 1:  # one day of slack for time zones ahead of the server
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if day < EARLIEST_DATE:
        raise HTTPException(status_code=422, detail="Date cannot be before 2000")
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
    new_badges = award_badges(db, user_id)
    db.commit()
    if gained:
        notify_user_groups(db, user_id)
    return StepLogResponse(
        log_date=day, steps=log.steps, goal_reached=log.steps >= STEP_GOAL, points_awarded=gained,
        new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
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
    new_badges = award_badges(db, user_id)
    db.commit()
    if gained:
        notify_user_groups(db, user_id)
    return SleepLogResponse(
        log_date=day, minutes=log.minutes, quality=log.quality,
        goal_reached=log.minutes >= SLEEP_GOAL_MINUTES, points_awarded=gained,
        new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
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


@router.get("/history", response_model=WellnessHistory)
def history(
    limit: int = Query(30, ge=1, le=200),
    offset: int = Query(0, ge=0),
    kind: str | None = Query(None, pattern="^(steps|sleep)$"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """The complete history of logged days (newest first, paged) plus all-time figures."""
    steps = {l.log_date: l.steps for l in db.query(StepLog).filter(StepLog.user_id == user_id)}
    sleeps = {l.log_date: l for l in db.query(SleepLog).filter(SleepLog.user_id == user_id)}
    dates = sorted({'steps': set(steps), 'sleep': set(sleeps)}.get(kind or '', set(steps) | set(sleeps)), reverse=True)

    days = []
    for d in dates[offset:offset + limit]:
        sl = sleeps.get(d)
        days.append(WellnessDay(
            date=d, steps=steps.get(d),
            sleep_minutes=sl.minutes if sl else None, sleep_quality=sl.quality if sl else None,
        ))
    sleep_minutes = [l.minutes for l in sleeps.values()]
    return WellnessHistory(
        days=days,
        total=len(dates),
        steps_logged=len(steps),
        avg_steps=round(sum(steps.values()) / len(steps)) if steps else 0,
        best_steps=max(steps.values(), default=0),
        sleep_logged=len(sleeps),
        avg_sleep_minutes=round(sum(sleep_minutes) / len(sleep_minutes)) if sleep_minutes else 0,
    )


@router.delete("/steps/{log_date}")
def delete_steps(log_date: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    log = db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.log_date == log_date).first()
    if not log:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(log)  # points already earned for that day are kept
    db.commit()
    return {"detail": "Steps entry deleted"}


@router.delete("/sleep/{log_date}")
def delete_sleep(log_date: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    log = db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.log_date == log_date).first()
    if not log:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(log)
    db.commit()
    return {"detail": "Sleep entry deleted"}


@router.get("/steps/series")
def steps_series(
    period: str = Query("week", pattern="^(week|month|year)$"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Steps for a chart: 7 days, 30 days, or 12 months (monthly average of the days logged),
    plus today's total and how many days in a row the goal was reached."""
    today = date.today()
    by_day = {l.log_date: l.steps for l in db.query(StepLog).filter(StepLog.user_id == user_id)}

    buckets = []
    if period in ("week", "month"):
        n = 7 if period == "week" else 30
        for i in range(n - 1, -1, -1):
            d = today - timedelta(days=i)
            v = by_day.get(d)
            buckets.append({"start": d, "steps": v, "days_logged": 0 if v is None else 1,
                            "goal_days": 1 if v is not None and v >= STEP_GOAL else 0})
    else:
        y, m = today.year, today.month
        months = []
        for _ in range(12):
            months.append((y, m))
            m -= 1
            if m == 0:
                y, m = y - 1, 12
        for (y, m) in reversed(months):
            vals = [v for d, v in by_day.items() if d.year == y and d.month == m]
            buckets.append({"start": date(y, m, 1), "steps": round(sum(vals) / len(vals)) if vals else None,
                            "days_logged": len(vals), "goal_days": sum(1 for v in vals if v >= STEP_GOAL)})

    streak = 0
    day = today if by_day.get(today, 0) >= STEP_GOAL else today - timedelta(days=1)  # today may still be in progress
    while by_day.get(day, 0) >= STEP_GOAL:
        streak += 1
        day -= timedelta(days=1)
    return {"goal": STEP_GOAL, "period": period, "today": by_day.get(today), "goal_streak": streak, "buckets": buckets}
