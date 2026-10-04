from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Habit, CheckIn, HabitCategory
from app.application.schemas import HabitCreate, HabitResponse, CheckInResponse

router = APIRouter(prefix="/api/habits", tags=["habits"])


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
    return habit


@router.get("", response_model=list[HabitResponse])
def list_habits(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    checked_ids = {
        c.habit_id
        for c in db.query(CheckIn).filter(
            CheckIn.habit_id.in_([h.id for h in habits]),
            CheckIn.check_date == date.today(),
        )
    }
    return [
        HabitResponse(
            id=h.id,
            name=h.name,
            frequency=h.frequency,
            category=h.category.value,
            checked_in_today=h.id in checked_ids,
        )
        for h in habits
    ]

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

    db.commit()
    db.refresh(check_in_entry)
    return check_in_entry