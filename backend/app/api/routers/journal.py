from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import JournalEntry, JournalAudio
from app.application.schemas import JournalEntryResponse, JournalPage, JournalUpdate

router = APIRouter(prefix="/api/journal", tags=["journal"])

MOODS = {"good", "neutral", "bad"}
MAX_CONTENT = 10_000
MAX_AUDIO_BYTES = 8 * 1024 * 1024
MAX_AUDIO_SECONDS = 15 * 60
AUDIO_TYPES = {"audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/x-wav", "audio/aac"}


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


def _response(entry: JournalEntry, audio: JournalAudio | None) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id, entry_date=entry.entry_date, content=entry.content or "", mood=entry.mood,
        created_at=entry.created_at, has_audio=audio is not None,
        audio_seconds=audio.seconds if audio else 0, audio_mime=audio.mime if audio else None,
    )


def _own(db: Session, entry_id: UUID, user_id: str) -> JournalEntry:
    entry = db.query(JournalEntry).filter(JournalEntry.id == entry_id, JournalEntry.user_id == user_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    return entry


@router.get("", response_model=JournalPage)
def list_entries(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
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
    return JournalPage(entries=[_response(e, audio.get(e.id)) for e in entries], total=total)


@router.post("", response_model=JournalEntryResponse)
async def create_entry(
    entry_date: date = Form(...),
    content: str = Form(""),
    mood: str | None = Form(None),
    audio_seconds: int = Form(0),
    audio: UploadFile | None = File(None),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
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

    entry = JournalEntry(user_id=user_id, entry_date=entry_date, content=content, mood=mood)
    db.add(entry)
    db.flush()
    attached = None
    if data is not None:
        attached = JournalAudio(
            entry_id=entry.id, mime=mime, data=data,
            seconds=max(0, min(int(audio_seconds), MAX_AUDIO_SECONDS)),
        )
        db.add(attached)
    db.commit()
    db.refresh(entry)
    return _response(entry, attached)


@router.put("/{entry_id}", response_model=JournalEntryResponse)
def update_entry(
    entry_id: UUID,
    payload: JournalUpdate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    entry = _own(db, entry_id, user_id)
    content, mood = _clean(payload.content, payload.mood)
    _check_date(payload.entry_date)
    audio = db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).first()
    if not content and audio is None:
        raise HTTPException(status_code=422, detail="Write something or record audio")
    entry.content, entry.mood, entry.entry_date = content, mood, payload.entry_date
    db.commit()
    return _response(entry, audio)


@router.get("/{entry_id}/audio")
def get_audio(entry_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    entry = _own(db, entry_id, user_id)
    audio = db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).first()
    if audio is None:
        raise HTTPException(status_code=404, detail="Recording not found")
    return Response(content=audio.data, media_type=audio.mime, headers={"Cache-Control": "private, max-age=3600"})


@router.delete("/{entry_id}/audio")
def delete_audio(entry_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
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
def delete_entry(entry_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    entry = _own(db, entry_id, user_id)
    db.query(JournalAudio).filter(JournalAudio.entry_id == entry.id).delete(synchronize_session=False)
    db.delete(entry)
    db.commit()
    return {"detail": "Entry deleted"}
