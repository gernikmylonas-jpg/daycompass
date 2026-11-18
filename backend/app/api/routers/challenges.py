from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Challenge, Group, GroupMember, User
from app.application.schemas import ChallengeCreate, ChallengeResponse, ChallengeMember
from app.application.services.challenges import METRICS, member_progress
from app.application.services.realtime import notify_groups

router = APIRouter(prefix="/api/groups/{group_id}/challenges", tags=["challenges"])

MAX_TITLE = 80
MAX_TARGET = 1_000_000
MAX_DAYS = 366
MAX_PER_GROUP = 50


def _member_group(db: Session, group_id: UUID, user_id: str) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    is_member = group and db.query(GroupMember.id).filter(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id).first()
    if not is_member:
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _response(db: Session, c: Challenge, members: list[User], me: str) -> ChallengeResponse:
    today = date.today()
    progress = member_progress(db, c.metric, [m.id for m in members], c.start_date, c.end_date)
    rows = sorted(
        (ChallengeMember(user_id=m.id, name=m.name, progress=progress[m.id], done=progress[m.id] >= c.target,
                         is_me=str(m.id) == str(me)) for m in members),
        key=lambda r: (-r.progress, r.name.lower()),
    )
    status = "upcoming" if today < c.start_date else "finished" if today > c.end_date else "active"
    return ChallengeResponse(
        id=c.id, title=c.title, metric=c.metric, target=c.target, start_date=c.start_date, end_date=c.end_date,
        status=status, days_left=max(0, (c.end_date - today).days + 1) if status != "finished" else 0,
        completed_count=sum(1 for r in rows if r.done), members=rows,
    )


@router.get("", response_model=list[ChallengeResponse])
def list_challenges(group_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    _member_group(db, group_id, user_id)
    members = db.query(User).join(GroupMember, GroupMember.user_id == User.id).filter(GroupMember.group_id == group_id).all()
    challenges = db.query(Challenge).filter(Challenge.group_id == group_id).order_by(Challenge.end_date.desc()).all()
    return [_response(db, c, members, user_id) for c in challenges]


@router.post("", response_model=ChallengeResponse)
def create_challenge(
    group_id: UUID, payload: ChallengeCreate,
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db),
):
    group = _member_group(db, group_id, user_id)
    if str(group.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Only the owner can manage challenges")
    title = payload.title.strip()
    if not title:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(title) > MAX_TITLE:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_TITLE} characters)")
    if payload.metric not in METRICS:
        raise HTTPException(status_code=422, detail="Invalid metric")
    if not 1 <= payload.target <= MAX_TARGET:
        raise HTTPException(status_code=422, detail=f"Target must be between 1 and {MAX_TARGET}")
    if payload.end_date < payload.start_date:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (payload.end_date - payload.start_date).days + 1 > MAX_DAYS:
        raise HTTPException(status_code=422, detail=f"Range is limited to {MAX_DAYS} days")
    if db.query(Challenge).filter(Challenge.group_id == group_id).count() >= MAX_PER_GROUP:
        raise HTTPException(status_code=422, detail="Too many challenges")

    challenge = Challenge(
        group_id=group_id, created_by=user_id, title=title, metric=payload.metric, target=payload.target,
        start_date=payload.start_date, end_date=payload.end_date,
    )
    db.add(challenge)
    db.commit()
    db.refresh(challenge)
    notify_groups([group_id])
    members = db.query(User).join(GroupMember, GroupMember.user_id == User.id).filter(GroupMember.group_id == group_id).all()
    return _response(db, challenge, members, user_id)


@router.delete("/{challenge_id}")
def delete_challenge(
    group_id: UUID, challenge_id: UUID,
    user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db),
):
    group = _member_group(db, group_id, user_id)
    if str(group.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Only the owner can manage challenges")
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id, Challenge.group_id == group_id).first()
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    db.delete(challenge)
    db.commit()
    notify_groups([group_id])
    return {"detail": "Challenge deleted"}
