import calendar as cal
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.domain.models import CalendarEvent


def occurrence_date(event_date: date, year: int) -> date:
    """Yearly repeat: Feb 29 falls on Feb 28 in non-leap years."""
    if event_date.month == 2 and event_date.day == 29 and not cal.isleap(year):
        return date(year, 2, 28)
    return date(year, event_date.month, event_date.day)


def _days(first: date, last: date, start: date, end: date):
    """The days of first..last that fall inside start..end."""
    day, stop = max(first, start), min(last, end)
    while day <= stop:
        yield day
        day += timedelta(days=1)


def occurrences_between(db: Session, user_id, start: date, end: date) -> list[tuple[CalendarEvent, date]]:
    """Every (event, day) in the range. Yearly events repeat from their first year on, weekly ones every week, and a
    note that lasts several days appears on each of its days."""
    plain = CalendarEvent.repeat_yearly.is_(False) & CalendarEvent.repeat_weekly.is_(False)
    once = (
        db.query(CalendarEvent)
        .filter(
            CalendarEvent.user_id == user_id, plain, CalendarEvent.event_date <= end,
            (CalendarEvent.event_date >= start) | (CalendarEvent.end_date >= start),
        ).all()
    )
    yearly = db.query(CalendarEvent).filter(CalendarEvent.user_id == user_id, CalendarEvent.repeat_yearly.is_(True)).all()
    weekly = db.query(CalendarEvent).filter(
        CalendarEvent.user_id == user_id, CalendarEvent.repeat_weekly.is_(True), CalendarEvent.event_date <= end
    ).all()
    out: list[tuple[CalendarEvent, date]] = []
    for e in once:
        out += [(e, d) for d in _days(e.event_date, e.end_date or e.event_date, start, end)]
    for e in weekly:  # the same weekday every week, from its first day on
        first = max(start, e.event_date)
        day = first + timedelta(days=(e.event_date - first).days % 7)
        while day <= end:
            out.append((e, day))
            day += timedelta(days=7)
    for e in yearly:
        span = (e.end_date - e.event_date).days if e.end_date else 0
        for year in range(start.year - 1, end.year + 1):  # the year before too: a range can run over New Year
            if year < e.event_date.year:
                continue
            first = occurrence_date(e.event_date, year)
            out += [(e, d) for d in _days(first, first + timedelta(days=span), start, end)]
    out.sort(key=lambda item: (item[1], item[0].title.lower()))
    return out
