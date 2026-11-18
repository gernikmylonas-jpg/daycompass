from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.application.services import push as push_service
from app.config import settings
from app.domain.models import PushSubscription
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id

router = APIRouter(prefix="/api/push", tags=["push"])
MAX_PER_USER = 10  # devices


class Keys(BaseModel):
    p256dh: str
    auth: str


class SubscribeIn(BaseModel):
    endpoint: str
    keys: Keys


class UnsubscribeIn(BaseModel):
    endpoint: str


@router.get("/key")
def key(_: str = Depends(get_current_user_id)):
    return {"enabled": push_service.push_enabled(), "public_key": settings.vapid_public_key or None}


@router.post("/subscribe")
def subscribe(payload: SubscribeIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not push_service.push_enabled():
        raise HTTPException(status_code=503, detail="Push notifications are not set up on this server")
    if not payload.endpoint.startswith("https://") or len(payload.endpoint) > 1000:
        raise HTTPException(status_code=422, detail="Invalid subscription")
    sub = db.query(PushSubscription).filter(PushSubscription.endpoint == payload.endpoint).first()
    if sub is None:
        if db.query(PushSubscription).filter(PushSubscription.user_id == user_id).count() >= MAX_PER_USER:
            raise HTTPException(status_code=422, detail="Too many devices")
        sub = PushSubscription(user_id=user_id, endpoint=payload.endpoint, p256dh=payload.keys.p256dh, auth=payload.keys.auth)
        db.add(sub)
    else:  # the same browser signing in as someone else, or refreshed keys
        sub.user_id, sub.p256dh, sub.auth = user_id, payload.keys.p256dh, payload.keys.auth
    db.commit()
    return {"subscribed": True}


@router.post("/unsubscribe")
def unsubscribe(payload: UnsubscribeIn, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.query(PushSubscription).filter(PushSubscription.user_id == user_id, PushSubscription.endpoint == payload.endpoint).delete(synchronize_session=False)
    db.commit()
    return {"subscribed": False}


@router.post("/test")
def test(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if not push_service.push_enabled():
        raise HTTPException(status_code=503, detail="Push notifications are not set up on this server")
    lang = push_service.user_language(db, user_id)
    return {"sent": push_service.send_to_user(db, user_id, {"title": "DayCompass", "body": push_service.TEST[lang], "url": "/"})}
