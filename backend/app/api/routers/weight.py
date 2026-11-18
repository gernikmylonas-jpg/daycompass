"""Weight tracking: one reading a day, a 7-day trend (daily weight is noisy), a goal and an optional BMI.
Nothing here awards points: the point is to look at the trend, not to reward a number."""
from datetime import date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.models import WeightLog, WeightProfile
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.application.schemas import BadgeInfo
from app.application.services.badges import award_badges

router = APIRouter(prefix="/api/weight", tags=["weight"])

MIN_KG, MAX_KG = 20.0, 400.0
MIN_CM, MAX_CM = 80, 250
EARLIEST = date(2000, 1, 1)
RAPID_LOSS_PER_WEEK = 0.015  # more than 1.5% of body weight in a week is worth a gentle word of caution


class WeightIn(BaseModel):
    kg: float


class ProfileIn(BaseModel):
    height_cm: Optional[int] = None
    goal_kg: Optional[float] = None
    unit: str = "kg"
    show_bmi: bool = False


def _profile(db: Session, user_id: str) -> dict:
    p = db.query(WeightProfile).filter(WeightProfile.user_id == user_id).first()
    if p is None:
        return {"height_cm": None, "goal_kg": None, "unit": "kg", "show_bmi": False}
    return {"height_cm": p.height_cm, "goal_kg": p.goal_kg, "unit": p.unit, "show_bmi": p.show_bmi}


@router.put("/profile")
def put_profile(payload: ProfileIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if payload.unit not in ("kg", "lb"):
        raise HTTPException(status_code=422, detail="Invalid unit")
    if payload.height_cm is not None and not MIN_CM <= payload.height_cm <= MAX_CM:
        raise HTTPException(status_code=422, detail=f"Height must be between {MIN_CM} and {MAX_CM} cm")
    if payload.goal_kg is not None and not MIN_KG <= payload.goal_kg <= MAX_KG:
        raise HTTPException(status_code=422, detail=f"Weight must be between {int(MIN_KG)} and {int(MAX_KG)} kg")
    p = db.query(WeightProfile).filter(WeightProfile.user_id == user_id).first()
    if p is None:
        p = WeightProfile(user_id=user_id)
        db.add(p)
    p.height_cm, p.goal_kg, p.unit, p.show_bmi = payload.height_cm, payload.goal_kg, payload.unit, payload.show_bmi
    db.commit()
    return _profile(db, user_id)


@router.put("/{day}")
def log_weight(day: date, payload: WeightIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not MIN_KG <= payload.kg <= MAX_KG:
        raise HTTPException(status_code=422, detail=f"Weight must be between {int(MIN_KG)} and {int(MAX_KG)} kg")
    if day > date.today():
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if day < EARLIEST:
        raise HTTPException(status_code=422, detail="Date cannot be before 2000")
    row = db.query(WeightLog).filter(WeightLog.user_id == user_id, WeightLog.log_date == day).first()
    if row is None:
        row = WeightLog(user_id=user_id, log_date=day, kg=round(payload.kg, 2))
        db.add(row)
    else:
        row.kg = round(payload.kg, 2)
    new_badges = award_badges(db, user_id)
    db.commit()
    return {"date": day, "kg": row.kg, "new_badges": [BadgeInfo.model_validate(x).model_dump() for x in new_badges]}


@router.delete("/{day}")
def delete_weight(day: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = db.query(WeightLog).filter(WeightLog.user_id == user_id, WeightLog.log_date == day).first()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(row)
    db.commit()
    return {"detail": "Weight entry deleted"}


@router.get("")
def weight_overview(
    days: int = Query(90, ge=7, le=3650),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Readings of the last `days` days with their 7-day trend, plus the figures that matter."""
    rows = db.query(WeightLog).filter(WeightLog.user_id == user_id).order_by(WeightLog.log_date).all()
    kg_by_day = {r.log_date: r.kg for r in rows}

    def trend(d: date) -> float:  # mean of the readings in the 7 days up to and including d
        window = [kg for day, kg in kg_by_day.items() if d - timedelta(days=6) <= day <= d]
        return round(sum(window) / len(window), 2)

    since = date.today() - timedelta(days=days - 1)
    entries = [{"date": r.log_date, "kg": r.kg, "avg7": trend(r.log_date)} for r in rows if r.log_date >= since]
    profile = _profile(db, user_id)

    stats: dict = {"logged_total": len(rows), "latest": None, "trend": None, "change_7d": None, "change_30d": None,
                   "to_goal": None, "bmi": None, "rapid_loss": False}
    if rows:
        last = rows[-1]
        stats["latest"] = {"date": last.log_date, "kg": last.kg}
        stats["trend"] = trend(last.log_date)

        def change(span: int) -> Optional[float]:
            target = last.log_date - timedelta(days=span)
            earlier = [d for d in kg_by_day if d <= target]
            if not earlier or (target - max(earlier)).days > span // 2 + 3:  # no reading near enough to compare
                return None
            return round(stats["trend"] - trend(max(earlier)), 2)

        stats["change_7d"] = change(7)
        stats["change_30d"] = change(30)
        if stats["change_7d"] is not None and stats["change_7d"] < -RAPID_LOSS_PER_WEEK * last.kg:
            stats["rapid_loss"] = True
        if profile["goal_kg"]:
            stats["to_goal"] = round(stats["trend"] - profile["goal_kg"], 2)  # positive = still above the goal
        if profile["height_cm"] and profile["show_bmi"]:
            stats["bmi"] = round(stats["trend"] / ((profile["height_cm"] / 100) ** 2), 1)
    return {"profile": profile, "entries": entries, "stats": stats}
