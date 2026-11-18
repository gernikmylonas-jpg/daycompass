from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings

engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def ensure_columns() -> None:
    """Tiny stop-gap until Alembic migrations exist: adds columns introduced after a table was
    first created. Every statement is idempotent."""
    if engine.dialect.name != "postgresql":
        return
    statements = [
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS created_at TIMESTAMP NOT NULL DEFAULT NOW()",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS mood_style VARCHAR NOT NULL DEFAULT 'emoji'",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS depth_3d BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE calendar_events ADD COLUMN IF NOT EXISTS repeat_weekly BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS calendar_prefs TEXT",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS wallpaper VARCHAR",
        "ALTER TABLE profile_photos ADD COLUMN IF NOT EXISTS share_with_groups BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS quests_on BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS wallpapers_on BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS lid_open BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS brightness INTEGER NOT NULL DEFAULT 100",
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS encrypted BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE journal_audio ADD COLUMN IF NOT EXISTS encrypted BOOLEAN NOT NULL DEFAULT FALSE",
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
