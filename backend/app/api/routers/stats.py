import calendar as cal
from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Habit, CheckIn, PomodoroSession, StepLog, SleepLog, User, MeditationSession
from app.application.schemas import HeatmapDay, CalendarEntry, PointsBreakdown, PointsSource, StreakResponse
from app.application.services.points import POINTS_PER_CHECK_IN, POINTS_PER_POMODORO, POINTS_PER_MEDITATION
from app.application.services.streaks import compute_streaks

router = APIRouter(prefix="/api/stats", tags=["stats"])

MAX_RANGE_DAYS = 62


def _calendar_entries(db: Session, user_id: str, first: date, last: date) -> list[CalendarEntry]:
    rows = (
        db.query(CheckIn.check_date, Habit.id, Habit.name, Habit.category)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(
            Habit.user_id == user_id,
            CheckIn.completed.is_(True),
            CheckIn.check_date >= first,
            CheckIn.check_date <= last,
        )
        .order_by(CheckIn.check_date, Habit.name)
        .all()
    )
    return [
        CalendarEntry(date=d, habit_id=hid, habit_name=name, category=category.value)
        for d, hid, name, category in rows
    ]


@router.get("/heatmap", response_model=list[HeatmapDay])
def heatmap(
    days: int = Query(119, ge=1, le=366),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    since = date.today() - timedelta(days=days - 1)
    rows = (
        db.query(CheckIn.check_date, func.count(CheckIn.id))
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(
            Habit.user_id == user_id,
            CheckIn.completed.is_(True),
            CheckIn.check_date >= since,
        )
        .group_by(CheckIn.check_date)
        .order_by(CheckIn.check_date)
        .all()
    )
    return [HeatmapDay(date=d, count=c) for d, c in rows]


@router.get("/calendar", response_model=list[CalendarEntry])
def calendar_month(
    year: int = Query(..., ge=2000, le=2100),
    month: int = Query(..., ge=1, le=12),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    first = date(year, month, 1)
    last = date(year, month, cal.monthrange(year, month)[1])
    return _calendar_entries(db, user_id, first, last)


@router.get("/calendar-range", response_model=list[CalendarEntry])
def calendar_range(
    start: date,
    end: date,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if end < start:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Range is limited to {MAX_RANGE_DAYS} days")
    return _calendar_entries(db, user_id, start, end)


@router.get("/points", response_model=PointsBreakdown)
def points_breakdown(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Where the user's points come from. `other` is whatever the stored total has beyond the
    activity history (points are kept when a habit is deleted)."""
    check_ins = (
        db.query(func.count(CheckIn.id))
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True))
        .scalar()
    ) or 0
    pomodoros = db.query(func.count(PomodoroSession.id)).filter(PomodoroSession.user_id == user_id).scalar() or 0
    meditations = db.query(func.count(MeditationSession.id)).filter(MeditationSession.user_id == user_id).scalar() or 0

    def goal_days(model):
        days = db.query(func.count(model.id)).filter(model.user_id == user_id, model.points_awarded > 0).scalar() or 0
        pts = db.query(func.coalesce(func.sum(model.points_awarded), 0)).filter(model.user_id == user_id).scalar() or 0
        return PointsSource(count=int(days), points=int(pts))

    steps, sleep = goal_days(StepLog), goal_days(SleepLog)
    total = db.query(User.total_points).filter(User.id == user_id).scalar() or 0
    from_checkins = check_ins * POINTS_PER_CHECK_IN
    from_pomodoros = pomodoros * POINTS_PER_POMODORO
    from_meditation = meditations * POINTS_PER_MEDITATION
    explained = from_checkins + from_pomodoros + from_meditation + steps.points + sleep.points
    return PointsBreakdown(
        total=total,
        check_ins=PointsSource(count=check_ins, points=from_checkins),
        pomodoros=PointsSource(count=pomodoros, points=from_pomodoros),
        meditations=PointsSource(count=meditations, points=from_meditation),
        steps=steps,
        sleep=sleep,
        other=total - explained,
    )


@router.get("/streak", response_model=StreakResponse)
def overall_streak(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Days in a row with at least one habit check-in (still alive if today has none yet)."""
    dates = {
        d for (d,) in db.query(CheckIn.check_date)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True))
    }
    current, best = compute_streaks(dates, date.today())
    return StreakResponse(current=current, best=best, active_today=date.today() in dates)
