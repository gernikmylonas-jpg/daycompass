from datetime import date, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import MoodLog
from app.application.schemas import MoodUpsert, MoodLogResponse, MoodDay, MoodSummary, BadgeInfo
from app.application.services.badges import award_badges

router = APIRouter(prefix="/api/mood", tags=["mood"])

MAX_BACKFILL_DAYS = 365
MAX_NOTE = 200


@router.put("", response_model=MoodLogResponse)
def put_mood(payload: MoodUpsert, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not 1 <= payload.score <= 10:
        raise HTTPException(status_code=422, detail="Score must be between 1 and 10")
    today = date.today()
    day = payload.log_date or today
    if (day - today).days > 1:  # one day of slack for time zones ahead of the server
        raise HTTPException(status_code=422, detail="Date cannot be in the future")
    if (today - day).days > MAX_BACKFILL_DAYS:
        raise HTTPException(status_code=422, detail=f"Date cannot be older than {MAX_BACKFILL_DAYS} days")
    note = (payload.note or "").strip() or None
    if note and len(note) > MAX_NOTE:
        raise HTTPException(status_code=422, detail=f"Note is too long (max {MAX_NOTE} characters)")

    log = db.query(MoodLog).filter(MoodLog.user_id == user_id, MoodLog.log_date == day).first()
    if log is None:
        log = MoodLog(user_id=user_id, log_date=day, score=payload.score, note=note)
        db.add(log)
    else:
        log.score, log.note = payload.score, note
    new_badges = award_badges(db, user_id)
    db.commit()
    return MoodLogResponse(
        date=day, score=log.score, note=log.note,
        new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
    )


@router.get("", response_model=MoodSummary)
def mood_summary(
    days: int = Query(60, ge=1, le=366),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    today = date.today()
    rows = (
        db.query(MoodLog)
        .filter(MoodLog.user_id == user_id, MoodLog.log_date >= today - timedelta(days=days - 1))
        .order_by(MoodLog.log_date.desc())
        .all()
    )

    def average(span: int) -> float | None:
        scores = [r.score for r in rows if (today - r.log_date).days < span]
        return round(sum(scores) / len(scores), 1) if scores else None

    return MoodSummary(
        days=[MoodDay(date=r.log_date, score=r.score, note=r.note) for r in rows],
        today=next((r.score for r in rows if r.log_date == today), None),
        avg_7d=average(7),
        avg_30d=average(30),
        logged_total=db.query(MoodLog).filter(MoodLog.user_id == user_id).count(),
    )


@router.delete("/{log_date}")
def delete_mood(log_date: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    log = db.query(MoodLog).filter(MoodLog.user_id == user_id, MoodLog.log_date == log_date).first()
    if not log:
        raise HTTPException(status_code=404, detail="Entry not found")
    db.delete(log)
    db.commit()
    return {"detail": "Mood entry deleted"}
