"""Profile photo. Private by default: only its owner can fetch it. If the owner switches on "show to my groups",
people who share a group with them can fetch it too (and see it in that group's leaderboard); nobody else ever can."""
from datetime import datetime

from uuid import UUID
from pydantic import BaseModel
from fastapi import APIRouter, Depends, File, HTTPException, Response, UploadFile
from sqlalchemy.orm import Session

from app.domain.models import GroupMember, ProfilePhoto
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/profile-photo", tags=["profile"])

MAX_BYTES = 400 * 1024  # the app shrinks pictures to about 256 px before uploading
TYPES = {"image/jpeg": b"\xff\xd8\xff", "image/png": b"\x89PNG", "image/webp": b"RIFF"}


class SharingIn(BaseModel):
    share: bool


def shares_a_group(db: Session, a, b) -> bool:
    mine = [g for (g,) in db.query(GroupMember.group_id).filter(GroupMember.user_id == a)]
    return db.query(GroupMember.id).filter(GroupMember.user_id == b, GroupMember.group_id.in_(mine)).first() is not None


@router.get("/status")
def status(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first()
    return {"has_photo": p is not None, "share_with_groups": bool(p and p.share_with_groups)}


@router.put("/sharing")
def set_sharing(payload: SharingIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="No profile photo")
    p.share_with_groups = payload.share
    db.commit()
    return {"has_photo": True, "share_with_groups": p.share_with_groups}


@router.get("/user/{other_id}")
def get_member_photo(other_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """Someone else's picture: only if they chose to share it, and only for people who are in a group with them."""
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == other_id).first()
    if not p or (str(other_id) != str(user_id) and not (p.share_with_groups and shares_a_group(db, user_id, other_id))):
        raise HTTPException(status_code=404, detail="No profile photo")
    return Response(content=p.data, media_type=p.mime, headers={"Cache-Control": "private, no-store"})


@router.get("")
def get_photo(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="No profile photo")
    return Response(content=p.data, media_type=p.mime, headers={"Cache-Control": "private, no-store"})


@router.put("")
async def put_photo(file: UploadFile = File(...), user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    mime = (file.content_type or "").lower()
    if mime not in TYPES:
        raise HTTPException(status_code=422, detail="Unsupported image type")
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=422, detail="Picture is too large (max 400 KB)")
    if not data.startswith(TYPES[mime]):  # the bytes must really look like the type that was claimed
        raise HTTPException(status_code=422, detail="Unsupported image type")
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first()
    if p is None:
        p = ProfilePhoto(user_id=user_id)
        db.add(p)
    p.mime, p.data, p.updated_at = mime, data, datetime.utcnow()
    db.commit()
    return {"detail": "Saved"}


@router.delete("")
def delete_photo(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    p = db.query(ProfilePhoto).filter(ProfilePhoto.user_id == user_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="No profile photo")
    db.delete(p)
    db.commit()
    return {"detail": "Removed"}
