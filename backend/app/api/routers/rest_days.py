from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import RestDay

router = APIRouter(prefix="/api/rest-days", tags=["rest-days"])

MAX_PER_WEEK = 2      # in any window of 7 days
PAST_DAYS = 7         # a rest day can be set up to a week back...
FUTURE_DAYS = 3       # ...and planned a few days ahead


@router.get("", response_model=list[date])
def list_rest_days(start: date, end: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if end < start or (end - start).days > 366:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    rows = db.query(RestDay.rest_date).filter(
        RestDay.user_id == user_id, RestDay.rest_date >= start, RestDay.rest_date <= end
    ).order_by(RestDay.rest_date)
    return [d for (d,) in rows]


@router.put("/{day}", response_model=list[date])
def set_rest_day(day: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    today = date.today()
    if not today - timedelta(days=PAST_DAYS) <= day <= today + timedelta(days=FUTURE_DAYS):
        raise HTTPException(status_code=422, detail="Rest days can be set from a week ago to three days ahead")

    existing = {d for (d,) in db.query(RestDay.rest_date).filter(
        RestDay.user_id == user_id,
        RestDay.rest_date >= day - timedelta(days=6), RestDay.rest_date <= day + timedelta(days=6),
    )}
    if day in existing:
        return sorted(existing)
    taken = existing | {day}
    for offset in range(7):  # every 7-day window that contains the new day
        window_start = day - timedelta(days=offset)
        if sum(1 for d in taken if window_start <= d <= window_start + timedelta(days=6)) > MAX_PER_WEEK:
            raise HTTPException(status_code=422, detail=f"Too many rest days: at most {MAX_PER_WEEK} in any 7 days")

    db.add(RestDay(user_id=user_id, rest_date=day))
    db.commit()
    return sorted(taken)


@router.delete("/{day}")
def clear_rest_day(day: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    row = db.query(RestDay).filter(RestDay.user_id == user_id, RestDay.rest_date == day).first()
    if not row:
        raise HTTPException(status_code=404, detail="Rest day not found")
    db.delete(row)
    db.commit()
    return {"detail": "Rest day removed"}
