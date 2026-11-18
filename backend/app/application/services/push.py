"""Web push notifications. Only people who switched push on (and allowed it in their browser) have a subscription."""
import json
import logging
from datetime import date

from sqlalchemy.orm import Session

from app.application.services.reminders import _pending_habits
from app.config import settings
from app.domain.models import PushLog, PushSubscription, User, UserSettings

logger = logging.getLogger(__name__)

# title is always "DayCompass"; {n} = how many habits are still open today
MESSAGES = {
    "en": ("You still have {n} habit to check in today. Keep your streak going!", "You still have {n} habits to check in today. Keep your streak going!"),
    "es": ("Aún tienes {n} hábito por registrar hoy. ¡Mantén tu racha!", "Aún tienes {n} hábitos por registrar hoy. ¡Mantén tu racha!"),
    "fr": ("Il te reste {n} habitude à valider aujourd'hui. Garde ta série !", "Il te reste {n} habitudes à valider aujourd'hui. Garde ta série !"),
    "el": ("Έχεις ακόμα {n} συνήθεια για check-in σήμερα. Κράτα το streak σου!", "Έχεις ακόμα {n} συνήθειες για check-in σήμερα. Κράτα το streak σου!"),
}
TEST = {"en": "Push notifications are on.", "es": "Las notificaciones push están activadas.", "fr": "Les notifications push sont activées.", "el": "Οι ειδοποιήσεις push είναι ενεργές."}


def push_enabled() -> bool:
    return bool(settings.vapid_private_key and settings.vapid_public_key)


def send_to_subscription(db: Session, sub: PushSubscription, payload: dict) -> bool:
    """Returns True when the push service accepted it. A subscription the browser has dropped (404/410) is deleted."""
    from pywebpush import WebPushException, webpush
    try:
        webpush(
            subscription_info={"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            data=json.dumps(payload), vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_subject},
        )
        return True
    except WebPushException as e:
        status = getattr(e.response, "status_code", None)
        if status in (404, 410):
            db.delete(sub)
            db.commit()
        else:
            logger.warning("push failed (%s): %s", status, e)
        return False


def send_to_user(db: Session, user_id, payload: dict) -> int:
    sent = 0
    for sub in db.query(PushSubscription).filter(PushSubscription.user_id == user_id).all():
        sent += 1 if send_to_subscription(db, sub, payload) else 0
    return sent


def user_language(db: Session, user_id) -> str:
    lang = db.query(UserSettings.language).filter(UserSettings.user_id == user_id).scalar()
    return lang if lang in MESSAGES else "en"


def send_push_reminders(db: Session, today: date | None = None) -> dict:
    """Pushes the people who turned push on and still have open habits today, at most once a day each."""
    if not push_enabled():
        return {"sent": 0, "skipped": 0, "enabled": False}
    today = today or date.today()
    already = {u for (u,) in db.query(PushLog.user_id).filter(PushLog.sent_on == today)}
    user_ids = {u for (u,) in db.query(PushSubscription.user_id).distinct()}
    sent = skipped = 0
    for uid in user_ids:
        pending = _pending_habits(db, uid, today)
        if uid in already or not pending:
            skipped += 1
            continue
        one, many = MESSAGES[user_language(db, uid)]
        body = (one if len(pending) == 1 else many).format(n=len(pending))
        if send_to_user(db, uid, {"title": "DayCompass", "body": body, "url": "/"}):
            db.add(PushLog(user_id=uid, sent_on=today))
            db.commit()
            sent += 1
    logger.info("push reminders: sent=%s skipped=%s", sent, skipped)
    return {"sent": sent, "skipped": skipped, "enabled": True}
