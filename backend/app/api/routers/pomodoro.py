from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import PomodoroSession, User
from app.application.schemas import PomodoroCreate, PomodoroResponse, PomodoroSummary, BadgeInfo
from app.application.services.badges import award_badges
from app.application.services.points import POINTS_PER_POMODORO

router = APIRouter(prefix="/api/pomodoro", tags=["pomodoro"])

KINDS = {"work", "reading"}
MAX_TITLE_LENGTH = 100


@router.post("", response_model=PomodoroResponse)
def record_session(
    payload: PomodoroCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if payload.kind not in KINDS:
        raise HTTPException(status_code=422, detail="Invalid kind")
    if not 1 <= payload.duration_minutes <= 180:
        raise HTTPException(status_code=422, detail="Duration must be between 1 and 180 minutes")

    title = (payload.title or "").strip()
    if len(title) > MAX_TITLE_LENGTH:
        raise HTTPException(status_code=422, detail="Title is too long (max 100 characters)")

    session = PomodoroSession(
        user_id=user_id,
        kind=payload.kind,
        title=title or None,
        duration_minutes=payload.duration_minutes,
        session_date=date.today(),
    )
    db.add(session)

    user = db.query(User).filter(User.id == user_id).first()
    if user:
        user.total_points += POINTS_PER_POMODORO

    new_badges = award_badges(db, user_id)

    db.commit()
    db.refresh(session)
    return PomodoroResponse(
        id=session.id,
        kind=session.kind,
        title=session.title,
        duration_minutes=session.duration_minutes,
        session_date=session.session_date,
        completed_at=session.completed_at,
        new_badges=[BadgeInfo.model_validate(b) for b in new_badges],
    )


@router.get("/summary", response_model=PomodoroSummary)
def summary(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    mine = PomodoroSession.user_id == user_id

    total_minutes, total_sessions = db.query(
        func.coalesce(func.sum(PomodoroSession.duration_minutes), 0),
        func.count(PomodoroSession.id),
    ).filter(mine).one()

    today_minutes, today_sessions = db.query(
        func.coalesce(func.sum(PomodoroSession.duration_minutes), 0),
        func.count(PomodoroSession.id),
    ).filter(mine, PomodoroSession.session_date == date.today()).one()

    recent = (
        db.query(PomodoroSession)
        .filter(mine)
        .order_by(PomodoroSession.completed_at.desc())
        .limit(10)
        .all()
    )

    return PomodoroSummary(
        today_minutes=int(today_minutes),
        today_sessions=today_sessions,
        total_minutes=int(total_minutes),
        total_sessions=total_sessions,
        recent=recent,
    )
