"""Period (menstrual cycle) tracking. Private to the user and entirely opt-in: nothing exists until someone logs a day.
The predictions are simple averages of their own past cycles, not medical advice and not a contraception method."""
from datetime import date, timedelta
from statistics import mean, pstdev
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.domain.models import PeriodDay
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/cycle", tags=["cycle"])

FLOWS = {"light", "medium", "heavy", "spotting"}
EARLIEST = date(1900, 1, 1)
MAX_RANGE = 14           # days marked in one go
PLAUSIBLE = (15, 60)     # cycle lengths outside this are ignored when averaging (a missed month, a gap in logging)
HISTORY_DAYS = 800
MAX_NOTE = 120


def _day(d: date) -> date:
    if (d - date.today()).days > 1:
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if d < EARLIEST:
        raise HTTPException(status_code=422, detail="Date cannot be before 1900")
    return d


class DayIn(BaseModel):
    flow: Optional[str] = None
    note: Optional[str] = None


class RangeIn(BaseModel):
    start: date
    end: date
    flow: Optional[str] = None


def _check_flow(flow: Optional[str]) -> Optional[str]:
    if flow in (None, ""):
        return None
    if flow not in FLOWS:
        raise HTTPException(status_code=422, detail="Invalid flow")
    return flow


@router.put("/day/{day}")
def mark_day(day: date, payload: DayIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    day = _day(day)
    note = (payload.note or "").strip() or None
    if note and len(note) > MAX_NOTE:
        raise HTTPException(status_code=422, detail=f"Note is too long (max {MAX_NOTE} characters)")
    row = db.query(PeriodDay).filter(PeriodDay.user_id == user_id, PeriodDay.day == day).first()
    if row is None:
        row = PeriodDay(user_id=user_id, day=day)
        db.add(row)
    row.flow, row.note = _check_flow(payload.flow), note
    db.commit()
    return {"day": day, "flow": row.flow, "note": row.note}


@router.post("/range")
def mark_range(payload: RangeIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Marks every day from start to end (a whole period in one go). Days that are already marked are kept."""
    if payload.end < payload.start:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (payload.end - payload.start).days + 1 > MAX_RANGE:
        raise HTTPException(status_code=422, detail=f"Range is limited to {MAX_RANGE} days")
    flow = _check_flow(payload.flow)
    have = {d for (d,) in db.query(PeriodDay.day).filter(PeriodDay.user_id == user_id, PeriodDay.day.between(payload.start, payload.end))}
    d = payload.start
    added = 0
    while d <= payload.end:
        if d not in have:
            db.add(PeriodDay(user_id=user_id, day=_day(d), flow=flow))
            added += 1
        d += timedelta(days=1)
    db.commit()
    return {"added": added}


@router.delete("/day/{day}")
def clear_day(day: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = db.query(PeriodDay).filter(PeriodDay.user_id == user_id, PeriodDay.day == day).first()
    if not row:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(row)
    db.commit()
    return {"detail": "Removed"}


def _periods(days: list[date]) -> list[list[date]]:
    """Consecutive logged days form one period (a one-day gap is tolerated: a forgotten day)."""
    out: list[list[date]] = []
    for d in sorted(days):
        if out and (d - out[-1][-1]).days <= 2:
            out[-1].append(d)
        else:
            out.append([d])
    return out


@router.get("")
def overview(history_days: int = Query(HISTORY_DAYS, ge=30, le=40000), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    since = date.today() - timedelta(days=history_days)
    rows = db.query(PeriodDay).filter(PeriodDay.user_id == user_id, PeriodDay.day >= since).order_by(PeriodDay.day).all()
    periods = _periods([r.day for r in rows])
    starts = [p[0] for p in periods]
    lengths = [(b - a).days for a, b in zip(starts, starts[1:]) if PLAUSIBLE[0] <= (b - a).days <= PLAUSIBLE[1]]
    recent = lengths[-6:]
    period_len = [len(p) for p in periods[-6:]]
    today = date.today()

    stats = {"cycles_logged": len(lengths), "average_cycle": round(mean(recent)) if recent else None,
             "average_period": round(mean(period_len)) if period_len else None, "regular": None,
             "shortest": min(recent) if recent else None, "longest": max(recent) if recent else None,
             "current_cycle_day": None, "days_since_start": None}
    predictions: list[dict] = []
    if starts:
        stats["current_cycle_day"] = (today - starts[-1]).days + 1
    if recent:
        avg = round(mean(recent))
        spread = max(1, min(3, round(pstdev(recent)))) if len(recent) >= 3 else 2
        stats["regular"] = (max(recent) - min(recent)) <= 7 if len(recent) >= 3 else None
        nxt = starts[-1]
        for _ in range(3):
            nxt = nxt + timedelta(days=avg)
            predictions.append({"start": nxt, "earliest": nxt - timedelta(days=spread), "latest": nxt + timedelta(days=spread),
                                "length": stats["average_period"] or 5})
    next_in = (predictions[0]["start"] - today).days if predictions else None
    return {
        "days": [{"date": r.day, "flow": r.flow, "note": r.note} for r in rows],
        "periods": [{"start": p[0], "end": p[-1], "length": len(p)} for p in periods[-12:]],
        "cycle_lengths": recent, "stats": stats, "predictions": predictions, "next_in_days": next_in,
        "late_by_days": (-next_in if next_in is not None and next_in < 0 and today > starts[-1] else None),
    }
