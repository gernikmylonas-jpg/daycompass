import logging
from datetime import date
from sqlalchemy.orm import Session
from app.config import settings
from app.domain.models import User, Habit, CheckIn, ReminderSetting, ReminderLog
from app.application.services.emailer import send_email

logger = logging.getLogger(__name__)

LANGUAGES = {"en", "es", "fr", "el"}
DEFAULT_LANGUAGE = "en"

# subject / body per language. {name} = user name, {habits} = bullet list, {url} = app link
TEMPLATES = {
    "en": (
        "DayCompass: you still have habits to check in today",
        "Hi {name},\n\nYou haven't checked in today yet. Still open:\n{habits}\n\nKeep your streak going: {url}\n\n"
        "You can turn these reminders off in the app.",
    ),
    "es": (
        "DayCompass: aún tienes hábitos por registrar hoy",
        "Hola {name},\n\nHoy todavía no has hecho tu registro. Pendientes:\n{habits}\n\nMantén tu racha: {url}\n\n"
        "Puedes desactivar estos recordatorios en la aplicación.",
    ),
    "fr": (
        "DayCompass : il te reste des habitudes à valider aujourd'hui",
        "Bonjour {name},\n\nTu n'as pas encore validé aujourd'hui. Restent à faire :\n{habits}\n\nGarde ta série : {url}\n\n"
        "Tu peux désactiver ces rappels dans l'application.",
    ),
    "el": (
        "DayCompass: έχεις ακόμα habits για check-in σήμερα",
        "Γεια σου {name},\n\nΔεν έχεις κάνει ακόμα check-in σήμερα. Εκκρεμούν:\n{habits}\n\nΚράτα το streak σου: {url}\n\n"
        "Μπορείς να απενεργοποιήσεις αυτές τις υπενθυμίσεις μέσα στην εφαρμογή.",
    ),
}


def _pending_habits(db: Session, user_id, today: date) -> list[str]:
    done = {
        hid for (hid,) in db.query(CheckIn.habit_id).filter(
            CheckIn.check_date == today, CheckIn.completed.is_(True)
        )
    }
    habits = db.query(Habit).filter(Habit.user_id == user_id).order_by(Habit.name).all()
    return [h.name for h in habits if h.id not in done]


def send_daily_reminders(db: Session, today: date | None = None) -> dict:
    """Emails opted-in users who still have un-checked habits today. Safe to re-run: each
    user is mailed at most once per day (ReminderLog)."""
    today = today or date.today()
    rows = (
        db.query(User, ReminderSetting)
        .join(ReminderSetting, ReminderSetting.user_id == User.id)
        .filter(ReminderSetting.enabled.is_(True))
        .all()
    )
    already = {uid for (uid,) in db.query(ReminderLog.user_id).filter(ReminderLog.sent_on == today)}

    sent = skipped = failed = 0
    for user, setting in rows:
        if user.id in already:
            skipped += 1
            continue
        pending = _pending_habits(db, user.id, today)
        if not pending:
            skipped += 1
            continue

        language = setting.language if setting.language in LANGUAGES else DEFAULT_LANGUAGE
        subject, body = TEMPLATES[language]
        body = body.format(
            name=user.name,
            habits="\n".join(f"  - {name}" for name in pending),
            url=settings.app_url,
        )
        if send_email(user.email, subject, body):
            db.add(ReminderLog(user_id=user.id, sent_on=today))
            db.commit()
            sent += 1
        else:
            failed += 1

    logger.info("daily reminders: sent=%s skipped=%s failed=%s", sent, skipped, failed)
    return {"sent": sent, "skipped": skipped, "failed": failed}
