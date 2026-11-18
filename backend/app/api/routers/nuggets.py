from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.services.wallpapers import BY_ID, CATALOG, POINTS_PER_NUGGET
from app.application.schemas import BadgeInfo
from app.application.services.badges import award_badges
from app.domain.models import QuestReward, User, WallpaperUnlock
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/nuggets", tags=["nuggets"])


def overview(db: Session, user_id: str) -> dict:
    points = db.query(User.total_points).filter(User.id == user_id).scalar() or 0
    unlocks = db.query(WallpaperUnlock).filter(WallpaperUnlock.user_id == user_id).order_by(WallpaperUnlock.unlocked_at).all()
    quests = db.query(func.count(QuestReward.id)).filter(QuestReward.user_id == user_id).scalar() or 0
    earned = max(points, 0) // POINTS_PER_NUGGET + quests  # one extra nugget for every completed daily quest
    spent = sum(u.cost for u in unlocks)
    return {
        "points": points,
        "earned": earned,
        "spent": spent,
        "balance": earned - spent,
        "points_per_nugget": POINTS_PER_NUGGET,
        "next_in": POINTS_PER_NUGGET - (max(points, 0) % POINTS_PER_NUGGET),
        "unlocked": [{"id": u.wallpaper_id, "cost": u.cost, "unlocked_at": u.unlocked_at} for u in unlocks],
        "catalog": CATALOG,
    }


@router.get("")
def get_nuggets(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return overview(db, user_id)


@router.post("/wallpapers/{wallpaper_id}/unlock")
def unlock_wallpaper(wallpaper_id: str, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    item = BY_ID.get(wallpaper_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Wallpaper not found")
    # serialise concurrent purchases of the same user so the balance cannot be overspent
    db.query(User).filter(User.id == user_id).with_for_update().first()
    if db.query(func.count(WallpaperUnlock.id)).filter(
        WallpaperUnlock.user_id == user_id, WallpaperUnlock.wallpaper_id == wallpaper_id
    ).scalar():
        raise HTTPException(status_code=409, detail="Wallpaper already unlocked")
    if overview(db, user_id)["balance"] < item["cost"]:
        raise HTTPException(status_code=422, detail="Not enough nuggets")
    db.add(WallpaperUnlock(user_id=user_id, wallpaper_id=wallpaper_id, cost=item["cost"], unlocked_at=datetime.utcnow()))
    new_badges = award_badges(db, user_id)
    db.commit()
    return {**overview(db, user_id), "new_badges": [BadgeInfo.model_validate(b).model_dump() for b in new_badges]}
