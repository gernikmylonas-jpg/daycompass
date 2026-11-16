import secrets
import string
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import Group, GroupMember
from app.application.schemas import (
    GroupCreate, GroupJoin, GroupSummary, GroupDetail, LeaderboardEntry,
)
from app.application.services.leaderboard import group_leaderboard

router = APIRouter(prefix="/api/groups", tags=["groups"])

MAX_NAME_LENGTH = 60
MAX_DESCRIPTION_LENGTH = 200
INVITE_ALPHABET = string.ascii_uppercase + string.digits
INVITE_LENGTH = 8
PERIODS = {"all", "week"}


def _new_invite_code(db: Session) -> str:
    while True:
        code = "".join(secrets.choice(INVITE_ALPHABET) for _ in range(INVITE_LENGTH))
        if not db.query(Group.id).filter(Group.invite_code == code).first():
            return code


def _membership(db: Session, group_id, user_id) -> GroupMember | None:
    return db.query(GroupMember).filter(
        GroupMember.group_id == group_id, GroupMember.user_id == user_id
    ).first()


def _get_member_group(db: Session, group_id: UUID, user_id: str) -> Group:
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group or not _membership(db, group.id, user_id):
        raise HTTPException(status_code=404, detail="Group not found")
    return group


def _summary(db: Session, group: Group, user_id: str) -> GroupSummary:
    board = group_leaderboard(db, group.id)
    my_rank = next((rank for rank, user, _ in board if str(user.id) == str(user_id)), 0)
    return GroupSummary(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code,
        is_owner=str(group.owner_id) == str(user_id),
        member_count=len(board),
        my_rank=my_rank,
    )


@router.get("", response_model=list[GroupSummary])
def list_my_groups(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    groups = (
        db.query(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .filter(GroupMember.user_id == user_id)
        .order_by(Group.name)
        .all()
    )
    return [_summary(db, g, user_id) for g in groups]


@router.post("", response_model=GroupSummary)
def create_group(payload: GroupCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    name = payload.name.strip()
    description = (payload.description or "").strip()
    if not name:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(name) > MAX_NAME_LENGTH:
        raise HTTPException(status_code=422, detail=f"Name is too long (max {MAX_NAME_LENGTH} characters)")
    if len(description) > MAX_DESCRIPTION_LENGTH:
        raise HTTPException(
            status_code=422, detail=f"Description is too long (max {MAX_DESCRIPTION_LENGTH} characters)"
        )

    group = Group(
        name=name,
        description=description or None,
        invite_code=_new_invite_code(db),
        owner_id=user_id,
    )
    db.add(group)
    db.flush()
    db.add(GroupMember(group_id=group.id, user_id=user_id))
    db.commit()
    db.refresh(group)
    return _summary(db, group, user_id)


@router.post("/join", response_model=GroupSummary)
def join_group(payload: GroupJoin, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    code = payload.invite_code.strip().upper()
    group = db.query(Group).filter(Group.invite_code == code).first()
    if not group:
        raise HTTPException(status_code=404, detail="Invalid invite code")
    if _membership(db, group.id, user_id):
        raise HTTPException(status_code=409, detail="Already a member of this group")

    db.add(GroupMember(group_id=group.id, user_id=user_id))
    db.commit()
    return _summary(db, group, user_id)


@router.get("/{group_id}", response_model=GroupDetail)
def group_detail(
    group_id: UUID,
    period: str = Query("all"),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if period not in PERIODS:
        raise HTTPException(status_code=422, detail="Period must be 'all' or 'week'")
    group = _get_member_group(db, group_id, user_id)
    board = group_leaderboard(db, group.id, period)
    return GroupDetail(
        id=group.id,
        name=group.name,
        description=group.description,
        invite_code=group.invite_code,
        is_owner=str(group.owner_id) == str(user_id),
        period=period,
        leaderboard=[
            LeaderboardEntry(
                rank=rank, user_id=user.id, name=user.name, points=pts,
                is_me=str(user.id) == str(user_id),
            )
            for rank, user, pts in board
        ],
    )


@router.delete("/{group_id}/members/me")
def leave_group(group_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    group = _get_member_group(db, group_id, user_id)
    db.delete(_membership(db, group.id, user_id))
    db.flush()

    remaining = (
        db.query(GroupMember)
        .filter(GroupMember.group_id == group.id)
        .order_by(GroupMember.joined_at)
        .first()
    )
    if remaining is None:
        db.delete(group)
    elif str(group.owner_id) == str(user_id):
        group.owner_id = remaining.user_id

    db.commit()
    return {"detail": "Left group"}


@router.delete("/{group_id}")
def delete_group(group_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    group = _get_member_group(db, group_id, user_id)
    if str(group.owner_id) != str(user_id):
        raise HTTPException(status_code=403, detail="Only the owner can delete the group")
    db.delete(group)
    db.commit()
    return {"detail": "Group deleted"}
