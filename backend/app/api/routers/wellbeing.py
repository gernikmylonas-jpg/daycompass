"""Small daily trackers: water, workouts and gratitude. Nothing is created unless the user logs it."""
from datetime import date, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.schemas import BadgeInfo
from app.application.services.badges import award_badges
from app.domain.models import GratitudeEntry, WaterLog, Workout
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api", tags=["wellbeing"])

WATER_GOAL = 8  # glasses of about 250 ml
MAX_GLASSES = 30
WORKOUT_KINDS = {"walk", "run", "cycle", "swim", "gym", "yoga", "sport", "other"}
MAX_MINUTES = 600
MAX_GRATITUDE_PER_DAY = 5
MAX_GRATITUDE_LEN = 200
EARLIEST = date(1900, 1, 1)


def _day(d: Optional[date]) -> date:
    d = d or date.today()
    if (d - date.today()).days > 1:  # one day of slack for time zones ahead of the server
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if d < EARLIEST:
        raise HTTPException(status_code=422, detail="Date cannot be before 1900")
    return d


# ── water ─────────────────────────────────────────────────────────────────
class WaterIn(BaseModel):
    glasses: int


@router.get("/water")
def water(days: int = Query(14, ge=1, le=366), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days - 1)
    rows = {r.log_date: r.glasses for r in db.query(WaterLog).filter(WaterLog.user_id == user_id, WaterLog.log_date >= since)}
    series = [{"date": since + timedelta(days=i), "glasses": rows.get(since + timedelta(days=i))} for i in range(days)]
    met = {d for (d,) in db.query(WaterLog.log_date).filter(
        WaterLog.user_id == user_id, WaterLog.glasses >= WATER_GOAL, WaterLog.log_date >= date.today() - timedelta(days=400))}
    streak, d = 0, date.today() if date.today() in met else date.today() - timedelta(days=1)  # today may still be in progress
    while d in met:
        streak += 1
        d -= timedelta(days=1)
    return {"goal": WATER_GOAL, "today": rows.get(date.today(), 0), "goal_streak": streak, "days": series}


@router.put("/water/{day}")
def set_water(day: date, payload: WaterIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not 0 <= payload.glasses <= MAX_GLASSES:
        raise HTTPException(status_code=422, detail=f"Glasses must be between 0 and {MAX_GLASSES}")
    day = _day(day)
    row = db.query(WaterLog).filter(WaterLog.user_id == user_id, WaterLog.log_date == day).first()
    if row is None:
        row = WaterLog(user_id=user_id, log_date=day, glasses=payload.glasses)
        db.add(row)
    else:
        row.glasses = payload.glasses
    new_badges = award_badges(db, user_id)
    db.commit()
    return {"date": day, "glasses": row.glasses, "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}


# ── workouts ──────────────────────────────────────────────────────────────
class WorkoutIn(BaseModel):
    kind: str
    minutes: int
    workout_date: Optional[date] = None
    note: Optional[str] = None


@router.get("/workouts")
def workouts(days: int = Query(90, ge=7, le=3650), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=days - 1)
    rows = db.query(Workout).filter(Workout.user_id == user_id, Workout.workout_date >= since).order_by(Workout.workout_date.desc(), Workout.created_at.desc()).all()
    week_start = date.today() - timedelta(days=date.today().weekday())
    by_kind: dict[str, int] = {}
    for w in rows:
        by_kind[w.kind] = by_kind.get(w.kind, 0) + w.minutes
    return {
        "week_minutes": sum(w.minutes for w in rows if w.workout_date >= week_start),
        "week_sessions": sum(1 for w in rows if w.workout_date >= week_start),
        "total_minutes": sum(w.minutes for w in rows), "total_sessions": len(rows), "by_kind": by_kind,
        "items": [{"id": w.id, "date": w.workout_date, "kind": w.kind, "minutes": w.minutes, "note": w.note} for w in rows[:100]],
    }


@router.post("/workouts")
def add_workout(payload: WorkoutIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if payload.kind not in WORKOUT_KINDS:
        raise HTTPException(status_code=422, detail="Invalid kind")
    if not 1 <= payload.minutes <= MAX_MINUTES:
        raise HTTPException(status_code=422, detail=f"Minutes must be between 1 and {MAX_MINUTES}")
    note = (payload.note or "").strip() or None
    if note and len(note) > 200:
        raise HTTPException(status_code=422, detail="Note is too long (max 200 characters)")
    w = Workout(user_id=user_id, workout_date=_day(payload.workout_date), kind=payload.kind, minutes=payload.minutes, note=note)
    db.add(w)
    new_badges = award_badges(db, user_id)
    db.commit()
    return {"id": w.id, "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}


@router.delete("/workouts/{workout_id}")
def delete_workout(workout_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    w = db.query(Workout).filter(Workout.id == workout_id, Workout.user_id == user_id).first()
    if not w:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(w)
    db.commit()
    return {"detail": "Workout deleted"}


# ── gratitude ─────────────────────────────────────────────────────────────
class GratitudeIn(BaseModel):
    text: str
    entry_date: Optional[date] = None


@router.get("/gratitude")
def gratitude(limit: int = Query(60, ge=1, le=500), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    rows = db.query(GratitudeEntry).filter(GratitudeEntry.user_id == user_id).order_by(GratitudeEntry.entry_date.desc(), GratitudeEntry.created_at.desc()).limit(limit).all()
    total = db.query(func.count(GratitudeEntry.id)).filter(GratitudeEntry.user_id == user_id).scalar() or 0
    return {"total": total, "items": [{"id": g.id, "date": g.entry_date, "text": g.text} for g in rows]}


@router.post("/gratitude")
def add_gratitude(payload: GratitudeIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=422, detail="Write something first")
    if len(text) > MAX_GRATITUDE_LEN:
        raise HTTPException(status_code=422, detail=f"Entry is too long (max {MAX_GRATITUDE_LEN} characters)")
    day = _day(payload.entry_date)
    if db.query(func.count(GratitudeEntry.id)).filter(GratitudeEntry.user_id == user_id, GratitudeEntry.entry_date == day).scalar() >= MAX_GRATITUDE_PER_DAY:
        raise HTTPException(status_code=422, detail=f"At most {MAX_GRATITUDE_PER_DAY} entries a day")
    g = GratitudeEntry(user_id=user_id, entry_date=day, text=text)
    db.add(g)
    new_badges = award_badges(db, user_id)
    db.commit()
    return {"id": g.id, "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}


@router.delete("/gratitude/{entry_id}")
def delete_gratitude(entry_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    g = db.query(GratitudeEntry).filter(GratitudeEntry.id == entry_id, GratitudeEntry.user_id == user_id).first()
    if not g:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(g)
    db.commit()
    return {"detail": "Entry deleted"}
