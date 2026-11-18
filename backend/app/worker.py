from celery import Celery
from celery.schedules import crontab
from app.config import settings
from app.domain import models  # noqa: F401  (registers the tables)
from app.infrastructure.database import SessionLocal
from app.application.services.reminders import send_daily_reminders
from app.application.services.maintenance import nightly_recalculation
from app.application.services.event_mail import send_event_mails

celery_app = Celery("daycompass", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    timezone=settings.timezone,
    enable_utc=True,
    task_acks_late=True,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    beat_schedule={
        "daily-checkin-reminders": {
            "task": "daycompass.send_daily_reminders",
            "schedule": crontab(hour=settings.reminder_hour, minute=settings.reminder_minute),
        },
        "calendar-notes-mail": {
            "task": "daycompass.send_event_mails",
            "schedule": crontab(hour=settings.events_hour, minute=settings.events_minute),
        },
        "nightly-recalculation": {
            "task": "daycompass.nightly_recalculation",
            "schedule": crontab(hour=settings.maintenance_hour, minute=settings.maintenance_minute),
        },
    },
)


@celery_app.task(name="daycompass.send_daily_reminders")
def send_daily_reminders_task() -> dict:
    with SessionLocal() as db:
        return send_daily_reminders(db)


@celery_app.task(name="daycompass.nightly_recalculation")
def nightly_recalculation_task() -> dict:
    with SessionLocal() as db:
        return nightly_recalculation(db)


@celery_app.task(name="daycompass.send_event_mails")
def send_event_mails_task() -> dict:
    with SessionLocal() as db:
        return send_event_mails(db)
