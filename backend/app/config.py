from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/daycompass"
    jwt_secret: str = "REPLACE_WITH_A_LONG_RANDOM_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60 * 24

    # Background jobs (Celery + Redis)
    redis_url: str = "redis://localhost:6379/0"
    timezone: str = "Europe/Athens"  # schedule timezone; set TZ to the same value in containers
    reminder_hour: int = 20      # daily reminder time (server local time)
    reminder_minute: int = 0
    maintenance_hour: int = 3    # nightly recalculation time (server local time)
    maintenance_minute: int = 30

    # Email reminders. Without smtp_host the message is only written to the log.
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_use_tls: bool = True
    mail_from: str = "DayCompass <no-reply@daycompass.local>"
    app_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"

settings = Settings()
