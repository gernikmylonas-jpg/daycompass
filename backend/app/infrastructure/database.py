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
    ]
    with engine.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
