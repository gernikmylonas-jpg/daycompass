import calendar as cal
from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.infrastructure.security import get_current_user_id
from app.domain.models import CalendarEvent
from app.application.schemas import EventCreate, EventResponse, BadgeInfo
from app.application.services.badges import award_badges

router = APIRouter(prefix="/api/calendar/events", tags=["calendar"])

KINDS = {"birthday", "reminder", "event", "note"}
MIN_YEAR, MAX_YEAR = 1900, 2100  # the UI browses 2000-2100; earlier years allow birth dates
MAX_RANGE_DAYS = 62
MAX_TITLE = 100
MAX_NOTES = 500
MAX_EVENTS_PER_USER = 2000


def _validate(payload: EventCreate) -> tuple[str, str | None]:
    title = payload.title.strip()
    notes = (payload.notes or "").strip() or None
    if not title:
        raise HTTPException(status_code=422, detail="Name is required")
    if len(title) > MAX_TITLE:
        raise HTTPException(status_code=422, detail=f"Title is too long (max {MAX_TITLE} characters)")
    if notes and len(notes) > MAX_NOTES:
        raise HTTPException(status_code=422, detail=f"Notes are too long (max {MAX_NOTES} characters)")
    if payload.kind not in KINDS:
        raise HTTPException(status_code=422, detail="Invalid kind")
    if not MIN_YEAR <= payload.event_date.year <= MAX_YEAR:
        raise HTTPException(status_code=422, detail=f"Year must be between {MIN_YEAR} and {MAX_YEAR}")
    return title, notes


def _occurrence(event_date: date, year: int) -> date:
    """Yearly repeat: Feb 29 falls on Feb 28 in non-leap years."""
    if event_date.month == 2 and event_date.day == 29 and not cal.isleap(year):
        return date(year, 2, 28)
    return date(year, event_date.month, event_date.day)


def _to_response(e: CalendarEvent, on: date) -> EventResponse:
    return EventResponse(
        id=e.id, title=e.title, kind=e.kind, notes=e.notes,
        repeat_yearly=e.repeat_yearly, date=on, original_date=e.event_date,
    )


@router.get("", response_model=list[EventResponse])
def list_events(
    start: date,
    end: date,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    if end < start:
        raise HTTPException(status_code=422, detail="End date must not be before start date")
    if (end - start).days + 1 > MAX_RANGE_DAYS:
        raise HTTPException(status_code=422, detail=f"Range is limited to {MAX_RANGE_DAYS} days")

    once = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.user_id == user_id,
            CalendarEvent.repeat_yearly.is_(False),
            CalendarEvent.event_date >= start,
            CalendarEvent.event_date <= end,
        )
        .all()
    )
    yearly = (
        db.query(CalendarEvent)
        .filter(CalendarEvent.user_id == user_id, CalendarEvent.repeat_yearly.is_(True))
        .all()
    )

    out = [_to_response(e, e.event_date) for e in once]
    for e in yearly:
        for year in range(start.year, end.year + 1):
            if year < e.event_date.year:
                continue
            occ = _occurrence(e.event_date, year)
            if start <= occ <= end:
                out.append(_to_response(e, occ))
    out.sort(key=lambda r: (r.date, r.title.lower()))
    return out


@router.post("", response_model=EventResponse)
def create_event(payload: EventCreate, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    title, notes = _validate(payload)
    if db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id).count() >= MAX_EVENTS_PER_USER:
        raise HTTPException(status_code=422, detail="Too many events")
    event = CalendarEvent(
        user_id=user_id, event_date=payload.event_date, title=title, kind=payload.kind,
        notes=notes, repeat_yearly=payload.repeat_yearly,
    )
    db.add(event)
    new_badges = award_badges(db, user_id)
    db.commit()
    db.refresh(event)
    result = _to_response(event, event.event_date)
    result.new_badges = [BadgeInfo.model_validate(b) for b in new_badges]
    return result


def _own(db: Session, event_id: UUID, user_id: str) -> CalendarEvent:
    event = db.query(CalendarEvent).filter(CalendarEvent.id == event_id, CalendarEvent.user_id == user_id).first()
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


@router.put("/{event_id}", response_model=EventResponse)
def update_event(
    event_id: UUID,
    payload: EventCreate,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    title, notes = _validate(payload)
    event = _own(db, event_id, user_id)
    event.title = title
    event.notes = notes
    event.kind = payload.kind
    event.event_date = payload.event_date
    event.repeat_yearly = payload.repeat_yearly
    db.commit()
    return _to_response(event, event.event_date)


@router.delete("/{event_id}")
def delete_event(event_id: UUID, user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    db.delete(_own(db, event_id, user_id))
    db.commit()
    return {"detail": "Event deleted"}
