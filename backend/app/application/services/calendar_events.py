import calendar as cal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.domain.models import CalendarEvent


def occurrence_date(event_date: date, year: int) -> date:
    """Yearly repeat: Feb 29 falls on Feb 28 in non-leap years."""
    if event_date.month == 2 and event_date.day == 29 and not cal.isleap(year):
        return date(year, 2, 28)
    return date(year, event_date.month, event_date.day)


def occurrences_between(db: Session, user_id, start: date, end: date) -> list[tuple[CalendarEvent, date]]:
    """Every (event, day) in the range, with yearly events repeated from their first year on."""
    once = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.user_id == user_id, CalendarEvent.repeat_yearly.is_(False), CalendarEvent.repeat_weekly.is_(False),
            CalendarEvent.event_date >= start, CalendarEvent.event_date <= end,
        ).all()
    )
    yearly = db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id, CalendarEvent.repeat_yearly.is_(True)).all()
    weekly = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id, CalendarEvent.repeat_weekly.is_(True), CalendarEvent.event_date <= end
    ).all()
    out = [(e, e.event_date) for e in once]
    for e in weekly:  # the same weekday every week, from its first day on
        first = max(start, e.event_date)
        day = first + timedelta(days=(e.event_date - first).days % 7)
        while day <= end:
            out.append((e, day))
            day += timedelta(days=7)
    for e in yearly:
        for year in range(start.year, end.year + 1):
            if year < e.event_date.year:
                continue
            day = occurrence_date(e.event_date, year)
            if start <= day <= end:
                out.append((e, day))
    out.sort(key=lambda item: (item[1], item[0].title.lower()))
    return out
