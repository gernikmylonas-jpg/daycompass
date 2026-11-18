import logging
from datetime import date
from sqlalchemy.orm import Session
from app.config import settings
from app.domain.models import User, ReminderSetting, EventMailLog
from app.application.services.calendar_events import occurrences_between
from app.application.services.emailer import send_email
from app.application.services.reminders import LANGUAGES, DEFAULT_LANGUAGE

logger = logging.getLogger(__name__)

KIND_ICON = {"birthday": "🎂", "reminder": "⏰", "event": "📌", "note": "📝"}

# subject, intro, birthday suffix ("{years}" = age), footer
TEMPLATES = {
    "en": ("DayCompass: on your calendar today", "Hi {name},\n\nHere is what you wrote on your calendar for today:\n{items}\n\nOpen DayCompass: {url}\n\nYou can turn these e-mails off in the app."),
    "es": ("DayCompass: en tu calendario hoy", "Hola {name},\n\nEsto es lo que escribiste en tu calendario para hoy:\n{items}\n\nAbre DayCompass: {url}\n\nPuedes desactivar estos correos en la aplicación."),
    "fr": ("DayCompass : dans ton calendrier aujourd'hui", "Bonjour {name},\n\nVoici ce que tu as noté dans ton calendrier pour aujourd'hui :\n{items}\n\nOuvre DayCompass : {url}\n\nTu peux désactiver ces e-mails dans l'application."),
    "el": ("DayCompass: στο ημερολόγιό σου σήμερα", "Γεια σου {name},\n\nΑυτά έγραψες στο ημερολόγιό σου για σήμερα:\n{items}\n\nΆνοιξε το DayCompass: {url}\n\nΜπορείς να απενεργοποιήσεις αυτά τα email μέσα στην εφαρμογή."),
}


def send_event_mails(db: Session, today: date | None = None) -> dict:
    """E-mails the users who turned the calendar-notes e-mail on a list of today's calendar notes (birthdays
    included). Safe to re-run: each user gets at most one such e-mail per day."""
    today = today or date.today()
    rows = (
        db.query(User, ReminderSetting)
        .join(ReminderSetting, ReminderSetting.user_id == User.id)
        .filter(ReminderSetting.events_enabled.is_(True))
        .all()
    )
    already = {uid for (uid,) in db.query(EventMailLog.user_id).filter(EventMailLog.sent_on == today)}
    sent = skipped = failed = 0
    for user, setting in rows:
        if user.id in already:
            skipped += 1
            continue
        todays = occurrences_between(db, user.id, today, today)
        if not todays:
            skipped += 1
            continue
        lines = []
        for event, day in todays:
            age = f" ({day.year - event.event_date.year})" if event.kind == "birthday" and event.repeat_yearly else ""
            note = f" — {event.notes}" if event.notes else ""
            lines.append(f"  {KIND_ICON.get(event.kind, '•')} {event.title}{age}{note}")
        language = setting.language if setting.language in LANGUAGES else DEFAULT_LANGUAGE
        subject, body = TEMPLATES[language]
        if send_email(user.email, subject, body.format(name=user.name, items="\n".join(lines), url=settings.app_url)):
            db.add(EventMailLog(user_id=user.id, sent_on=today))
            db.commit()
            sent += 1
        else:
            failed += 1
    logger.info("event e-mails: sent=%s skipped=%s failed=%s", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}
