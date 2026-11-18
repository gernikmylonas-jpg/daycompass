from datetime import date
from uuid import UUID
from cryptography.fernet import Fernet
from fastapi import APIRouter, Depends, File, Form, Header, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import JournalEntry, JournalAudio, JournalLock
from app.application.schemas import JournalEntryResponse, JournalPage, JournalUpdate, BadgeInfo
from app.application.services.badges import award_badges
from app.application.services.journal_crypto import (
    MIN_PIN, MAX_PIN, new_salt, make_cipher, make_check, is_correct,
)

router = APIRouter(prefix="/api/journal", tags=["journal"])

MOODS = {"good", "neutral", "bad"}
MAX_CONTENT = 10_000
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SECONDS = 15 * 60
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac"}


# ── the lock ─────────────────────────────────────────────────────────────

def get_cipher(db: Session, user_id: str, pin: str | None) -> Fernet | None:
    """None when the journal is not locked; otherwise the cipher for the PIN sent in X-Journal-Pin."""
    lock = db.query(JournalLock).filter(JournalLock.user_id == user_id).first()
    if lock is None:
        return None
    if not pin:
        raise HTTPException(status_code=423, detail="Journal is locked")
    cipher = make_cipher(pin, lock.salt)
    if not is_correct(cipher, lock.check_token):
        raise HTTPException(status_code=403, detail="Wrong journal PIN")
    return cipher


def _encrypt_text(cipher: Fernet | None, text: str) -> str:
    return cipher.encrypt(text.encode()).decode() if cipher and text else text


def _decrypt_text(entry: JournalEntry, cipher: Fernet | None) -> str:
    if not entry.encrypted or not entry.content:
        return entry.content or ""
    if cipher is None:
        raise HTTPException(status_code=423, detail="Journal is locked")
    return cipher.decrypt(entry.content.encode()).decode()


def _reencrypt_all(db: Session, user_id: str, old: Fernet | None, new: Fernet | None) -> None:
    """Moves every entry and recording from one key (or plain text) to another."""
    entries = db.query(JournalEntry).filter(JournalEntry.user_id == user_id).all()
    for e in entries:
        plain = _decrypt_text(e, old)
        e.content = _encrypt_text(new, plain)
        e.encrypted = new is not None
    ids = [e.id for e in entries]
    for a in db.query(JournalAudio).filter(JournalAudio.entry_id.in_(ids)) if ids else []:
        data = old.decrypt(a.data) if a.encrypted and old else a.data
        a.data = new.encrypt(data) if new else data
        a.encrypted = new is not None


class PinBody(BaseModel):
    pin: str


class PinChange(BaseModel):
    pin: str
    new_pin: str


def _check_pin(pin: str) -> None:
    if not MIN_PIN <= len(pin) <= MAX_PIN:
        raise HTTPException(status_code=422, detail=f"PIN must be at least {MIN_PIN} characters")


@router.get("/lock")
def lock_status(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    return {"enabled": db.query(JournalLock).filter(JournalLock.user_id == user_id).first() is not None}


@router.post("/lock")
def enable_lock(body: PinBody, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    if db.query(JournalLock).filter(JournalLock.user_id == user_id).first():
        raise HTTPException(status_code=409, detail="Journal lock already enabled")
    _check_pin(body.pin)
    salt = new_salt()
    cipher = make_cipher(body.pin, salt)
    _reencrypt_all(db, user_id, None, cipher)
    db.add(JournalLock(user_id=user_id, salt=salt, check_token=make_check(cipher)))
    db.commit()
    return {"enabled": True}


@router.put("/lock")
def change_pin(body: PinChange, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    old = get_cipher(db, user_id, body.pin)
    if old is None:
        raise HTTPException(status_code=404, detail="Journal lock is not enabled")
    _check_pin(body.new_pin)
    salt = new_salt()
    cipher = make_cipher(body.new_pin, salt)
    _reencrypt_all(db, user_id, old, cipher)
    lock = db.query(JournalLock).filter(JournalLock.user_id == user_id).first()
    lock.salt, lock.check_token = salt, make_check(cipher)
    db.commit()
    return {"enabled": True}


@router.post("/lock/disable")
def disable_lock(body: PinBody, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    old = get_cipher(db, user_id, body.pin)
    if old is None:
        raise HTTPException(status_code=404, detail="Journal lock is not enabled")
    _reencrypt_all(db, user_id, old, None)
    db.delete(db.query(JournalLock).filter(JournalLock.user_id == user_id).first())
    db.commit()
    return {"enabled": False}


# ── entries ──────────────────────────────────────────────────────────────

def _clean(content: str, mood: str | None) -> tuple[str, str | None]:
    content = (content or "").strip()
    if len(content) > MAX_CONTENT:
        raise HTTPException(status_code=422, detail=f"Entry is too long (max {MAX_CONTENT} characters)")
    mood = (mood or "").strip() or None
    if mood is not None and mood not in MOODS:
        raise HTTPException(status_code=422, detail="Invalid mood")
    return content, mood


def _check_date(day: date) -> None:
    if (day - date.today()).days > 1:  # one day of slack for time zones ahead of the server
        raise HTTPException(status_code=422, detail="Date cannot be in the future")


def _response(entry: JournalEntry, audio: JournalAudio | None, cipher: Fernet | None) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id, entry_date=entry.entry_date, content=_decrypt_text(entry, cipher), mood=entry.mood,
        created_at=entry.created_at, has_audio=audio is not None,
        audio_seconds=audio.seconds if audio else 0, audio_mime=audio.mime if audio else None,
    )


def _own(db: Session, entry_id: UUID, user_id: str) -> JournalEntry:
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("/days")
def journal_days(start: date, end: date, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """For a calendar: per day, how many entries and how many voice recordings exist. Counts only, never the content."""
    if end < start or (end - start).days > 366:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    rows = (
        db.query(JournalEntry.entry_date, JournalEntry.id, JournalAudio.entry_id)
        .outerjoin(JournalAudio, JournalAudio.entry_id == JournalEntry.id)
        .filter(JournalEntry.user_id == user_id, JournalEntry.entry_date.between(start, end))
        .all()
    )
    days: dict = {}
    for d, _eid, audio_id in rows:
        item = days.setdefault(d, {"date": d, "entries": 0, "recordings": 0})
        item["entries"] += 1
        item["recordings"] += 1 if audio_id is not None else 0
    return sorted(days.values(), key=lambda x: x["date"])


@router.get("", response_model=JournalPage)
def list_entries(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cipher = get_cipher(db, user_id, x_journal_pin)
    query = db.query(JournalEntry).filter(JournalEntry.user_id == user_id)
    total = query.count()
    entries = (
        query.order_by(JournalEntry.entry_date.desc(), JournalEntry.created_at.desc())
        .offset(offset).limit(limit).all()
    )
    audio = {
        a.entry_id: a
        for a in db.query(JournalAudio.entry_id, JournalAudio.mime, JournalAudio.seconds)
        .filter(JournalAudio.entry_id.in_([e.id for e in entries]))
    } if entries else {}
    return JournalPage(entries=[_response(e, audio.get(e.id), cipher) for e in entries], total=total)


@router.post("", response_model=JournalEntryResponse)
async def create_entry(
    entry_date: date = Form(...),
    content: str = Form(""),
    mood: str | None = Form(None),
    audio_seconds: int = Form(0),
    audio: UploadFile | None = File(None),
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cipher = get_cipher(db, user_id, x_journal_pin)
    content, mood = _clean(content, mood)
    _check_date(entry_date)

    data = mime = None
    if audio is not None and audio.filename:
        mime = (audio.content_type or "").split(";")[0].strip().lower()
        if mime not in AUDIO_TYPES:
            raise HTTPException(status_code=422, detail="Unsupported audio type")
        data = await audio.read(MAX_AUDIO_BYTES + 1)
        if len(data) > MAX_AUDIO_BYTES:
            raise HTTPException(status_code=422, detail="Recording is too large (max 8 MB)")
        if not data:
            data = mime = None

    if not content and data is None:
        raise HTTPException(status_code=422, detail="Write something or record audio")

    entry = JournalEntry(
        user_id=user_id, entry_date=entry_date, content=_encrypt_text(cipher, content), mood=mood,
        encrypted=cipher is not None,
    )
    db.add(entry)
    db.flush()
    attached = None
    if data is not None:
        attached = JournalAudio(
            entry_id=entry.id, mime=mime, data=cipher.encrypt(data) if cipher else data,
            seconds=max(0, min(int(audio_seconds), MAX_AUDIO_SECONDS)), encrypted=cipher is not None,
        )
        db.add(attached)
    new_badges = award_badges(db, user_id)
    db.commit()
    db.refresh(entry)
    result = _response(entry, attached, cipher)
    result.new_badges = [BadgeInfo.model_validate(b) for b in new_badges]
    return result


@router.put("/{entry_id}", response_model=JournalEntryResponse)
def update_entry(
    entry_id: UUID,
    payload: JournalUpdate,
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cipher = get_cipher(db, user_id, x_journal_pin)
    entry = _own(db, entry_id, user_id)
    content, mood = _clean(payload.content, payload.mood)
    _check_date(payload.entry_date)
    audio = db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).first()
    if not content and audio is None:
        raise HTTPException(status_code=422, detail="Write something or record audio")
    entry.content, entry.mood, entry.entry_date = _encrypt_text(cipher, content), mood, payload.entry_date
    entry.encrypted = cipher is not None
    db.commit()
    return _response(entry, audio, cipher)


@router.get("/{entry_id}/audio")
def get_audio(
    entry_id: UUID,
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    cipher = get_cipher(db, user_id, x_journal_pin)
    entry = _own(db, entry_id, user_id)
    audio = db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).first()
    if audio is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    data = cipher.decrypt(audio.data) if audio.encrypted and cipher else audio.data
    return Response(content=data, media_type=audio.mime, headers={"Cache-Control": "private, no-store"})


@router.delete("/{entry_id}/audio")
def delete_audio(
    entry_id: UUID,
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_cipher(db, user_id, x_journal_pin)
    entry = _own(db, entry_id, user_id)
    audio = db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).first()
    if audio is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    if not (entry.content or "").strip():
        raise HTTPException(status_code=422, detail="Write something or record audio")  # would leave it empty
    db.delete(audio)
    db.commit()
    return {"detail": "Recording deleted"}


@router.delete("/{entry_id}")
def delete_entry(
    entry_id: UUID,
    x_journal_pin: str | None = Header(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    get_cipher(db, user_id, x_journal_pin)
    entry = _own(db, entry_id, user_id)
    db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).delete(synchronize_session=False)
    db.delete(entry)
    db.commit()
    return {"detail": "Entry deleted"}
