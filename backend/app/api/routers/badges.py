from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Badge, UserBadge
from app.application.schemas import BadgeStatus

router = APIRouter(prefix="/api/badges", tags=["badges"])


@router.get("", response_model=list[BadgeStatus])
def list_badges(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    earned = {
        badge_id: awarded_at
        for badge_id, awarded_at in db.query(UserBadge.badge_id, UserBadge.awarded_at).filter(
            UserBadge.user_id == user_id
        )
    }
    return [
        BadgeStatus(
            code=b.code,
            name=b.name,
            description=b.description,
            icon=b.icon,
            earned=b.id in earned,
            awarded_at=earned.get(b.id),
        )
        for b in db.query(Badge).order_by(Badge.name).all()
    ]
