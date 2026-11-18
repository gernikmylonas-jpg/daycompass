"""The daily quest: one small challenge a day (same for the whole day, different each day), worth one extra gold nugget.
It only exists for people who switched quests on; the server just answers when asked."""
import hashlib
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.services.challenges import member_progress
from app.domain.models import QuestReward, WaterLog, Workout
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/quests", tags=["quests"])

# id, metric, target
QUESTS = [
    ("checkins3", "checkins", 3),
    ("steps6k", "steps", 6000),
    ("meditate10", "meditation_minutes", 10),
    ("focus2", "pomodoros", 2),
    ("journal1", "journal_entries", 1),
    ("mood1", "mood_logs", 1),
    ("water6", "water", 6),
    ("workout20", "workout_minutes", 20),
]


def quest_for(user_id: str, day: date) -> tuple[str, str, int]:
    h = int(hashlib.sha1(f"{user_id}|{day.isoformat()}".encode()).hexdigest(), 16)
    return QUESTS[h % len(QUESTS)]


def _progress(db: Session, user_id, metric: str, day: date) -> int:
    if metric == "water":
        return db.query(func.coalesce(func.sum(WaterLog.glasses), 0)).filter(WaterLog.user_id == user_id, WaterLog.log_date == day).scalar() or 0
    if metric == "workout_minutes":
        return db.query(func.coalesce(func.sum(Workout.minutes), 0)).filter(Workout.user_id == user_id, Workout.workout_date == day).scalar() or 0
    uid = UUID(str(user_id))  # progress is keyed by the UUIDs the database returns
    return int(member_progress(db, metric, [uid], day, day).get(uid, 0))


def _state(db: Session, user_id: str) -> dict:
    today = date.today()
    qid, metric, target = quest_for(user_id, today)
    progress = _progress(db, user_id, metric, today)
    claimed = db.query(QuestReward).filter(QuestReward.user_id == user_id, QuestReward.reward_date == today).first() is not None
    total = db.query(func.count(QuestReward.id)).filter(QuestReward.user_id == user_id).scalar() or 0
    return {"id": qid, "metric": metric, "target": target, "progress": int(progress), "done": progress >= target,
            "claimed": claimed, "reward_nuggets": 1, "completed_total": total}


@router.get("/today")
def today(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return _state(db, user_id)


@router.post("/today/claim")
def claim(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    state = _state(db, user_id)
    if state["claimed"]:
        raise HTTPException(status_code=409, detail="Quest reward already claimed")
    if not state["done"]:
        raise HTTPException(status_code=422, detail="Quest is not finished yet")
    db.add(QuestReward(user_id=user_id, reward_date=date.today(), quest_id=state["id"]))
    db.commit()
    return _state(db, user_id)
