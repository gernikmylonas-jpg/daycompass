from collections import defaultdict
from datetime import date, timedelta
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Habit, CheckIn, HabitCategory
from app.application.schemas import (
    HabitCreate, HabitUpdate, HabitResponse, CheckInResponse, BadgeInfo, HeatmapDay,
)
from app.application.services.streaks import compute_streaks
from app.application.services.badges import award_badges

router = APIRouter(prefix="/api/habits", tags=["habits"])


def to_response(habit: Habit, dates: list[date], today: date) -> HabitResponse:
    current, best = compute_streaks(dates, today)
    return HabitResponse(
        id=habit.id,
        name=habit.name,
        frequency=habit.frequency,
        category=habit.category.value,
        checked_in_today=today in dates,
        current_streak=current,
        best_streak=best,
    )


@router.post("", response_model=HabitResponse)
def create_habit(payload: HabitCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if payload.category not in [c.value for c in HabitCategory]:
        raise HTTPException(status_code=422, detail="Invalid category")

    habit = Habit(
        user_id=user_id,
        name=payload.name,
        frequency=payload.frequency,
        category=payload.category,
    )
    db.add(habit)
    db.commit()
    db.refresh(habit)
    return to_response(habit, [], date.today())


@router.get("", response_model=list[HabitResponse])
def list_habits(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    today = date.today()
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    dates_by_habit: dict = defaultdict(list)
    if habits:
        rows = db.query(CheckIn.habit_id, CheckIn.check_date).filter(
            CheckIn.habit_id.in_([h.id for h in habits]),
            CheckIn.completed.is_(True),
        )
        for habit_id, check_date in rows:
            dates_by_habit[habit_id].append(check_date)
    return [to_response(h, dates_by_habit[h.id], today) for h in habits]


def _own_habit(db: Session, habit_id: UUID, user_id: str) -> Habit:
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    return habit


@router.put("/{habit_id}", response_model=HabitResponse)
def update_habit(
    habit_id: UUID,
    payload: HabitUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    habit = _own_habit(db, habit_id, user_id)

    if payload.name is not None:
        name = payload.name.strip()
        if not name:
            raise HTTPException(status_code=422, detail="Name cannot be empty")
        habit.name = name
    if payload.category is not None:
        if payload.category not in [c.value for c in HabitCategory]:
            raise HTTPException(status_code=422, detail="Invalid category")
        habit.category = payload.category

    db.commit()
    db.refresh(habit)
    dates = [
        d for (d,) in db.query(CheckIn.check_date).filter(
            CheckIn.habit_id == habit.id, CheckIn.completed.is_(True)
        )
    ]
    return to_response(habit, dates, date.today())


@router.get("/{habit_id}/heatmap", response_model=list[HeatmapDay])
def habit_heatmap(
    habit_id: UUID,
    days: int = Query(119, ge=1, le=366),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    habit = _own_habit(db, habit_id, user_id)
    since = date.today() - timedelta(days=days - 1)
    rows = (
        db.query(CheckIn.check_date)
        .filter(
            CheckIn.habit_id == habit.id,
            CheckIn.completed.is_(True),
            CheckIn.check_date >= since,
        )
        .order_by(CheckIn.check_date)
        .all()
    )
    return [HeatmapDay(date=d, count=1) for (d,) in rows]


@router.delete("/{habit_id}")
def delete_habit(habit_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")
    db.delete(habit)
    db.commit()
    return {"detail": "Habit deleted"}


@router.post("/{habit_id}/check-in", response_model=CheckInResponse)
def check_in(habit_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    habit = db.query(Habit).filter(Habit.id == habit_id, Habit.user_id == user_id).first()
    if not habit:
        raise HTTPException(status_code=404, detail="Habit not found")

    existing = db.query(CheckIn).filter(
        CheckIn.habit_id == habit_id, CheckIn.check_date == date.today()
    ).first()
    if existing:
        raise HTTPException(status_code=409, detail="Already checked in today")

    check_in_entry = CheckIn(habit_id=habit_id, check_date=date.today(), completed=True)
    db.add(check_in_entry)

    user = habit.user
    user.total_points += 10

    new_badges = award_badges(db, user_id)

    db.commit()
    db.refresh(check_in_entry)
    return CheckInResponse(
        id=check_in_entry.id,
        habit_id=check_in_entry.habit_id,
        check_date=check_in_entry.check_date,
        completed=check_in_entry.completed,
        new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
    )
