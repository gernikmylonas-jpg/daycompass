from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import MeditationSession, User
from app.application.schemas import (
    MeditationCreate, MeditationResponse, MeditationSummary, MeditationItem, BadgeInfo,
)
from app.application.services.badges import award_badges
from app.application.services.points import POINTS_PER_MEDITATION
from app.application.services.streaks import compute_streaks
from app.application.services.realtime import notify_user_groups

router = APIRouter(prefix="/api/meditation", tags=["meditation"])

KINDS = {"breathing", "silent"}


@router.post("", response_model=MeditationResponse)
def record_session(
    payload: MeditationCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if payload.kind not in KINDS:
        raise HTTPException(status_code=422, detail="Invalid kind")
    if not 1 <= payload.duration_minutes <= 180:
        raise HTTPException(status_code=422, detail="Duration must be between 1 and 180 minutes")

    session = MeditationSession(
        user_id=user_id, kind=payload.kind, duration_minutes=payload.duration_minutes, session_date=date.today(),
    )
    db.add(session)
    db.query(User).filter(User.id == user_id).update({User.total_points: User.total_points + POINTS_PER_MEDITATION})
    new_badges = award_badges(db, user_id)
    db.commit()
    db.refresh(session)
    notify_user_groups(db, user_id)
    return MeditationResponse(
        id=session.id, kind=session.kind, duration_minutes=session.duration_minutes,
        session_date=session.session_date, completed_at=session.completed_at,
        points_awarded=POINTS_PER_MEDITATION, new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
    )


@router.get("/summary", response_model=MeditationSummary)
def summary(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    today = date.today()
    mine = db.query(MeditationSession).filter(MeditationSession.user_id == user_id)
    today_rows = mine.filter(MeditationSession.session_date == today)
    total_minutes = db.query(func.coalesce(func.sum(MeditationSession.duration_minutes), 0)).filter(
        MeditationSession.user_id == user_id).scalar()
    dates = {d for (d,) in db.query(MeditationSession.session_date).filter(MeditationSession.user_id == user_id)}
    recent = mine.order_by(MeditationSession.completed_at.desc()).limit(10).all()
    return MeditationSummary(
        today_minutes=sum(r.duration_minutes for r in today_rows.all()),
        today_sessions=today_rows.count(),
        total_minutes=int(total_minutes or 0),
        total_sessions=mine.count(),
        current_streak=compute_streaks(dates, today)[0],
        recent=[
            MeditationItem(id=r.id, kind=r.kind, duration_minutes=r.duration_minutes,
                           session_date=r.session_date, completed_at=r.completed_at)
            for r in recent
        ],
    )
