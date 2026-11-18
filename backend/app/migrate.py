"""Brings the database up to date. The API container runs this before it starts.

- A new, empty database: applies every migration (creates all tables).
- A database that already has tables but no Alembic history (everything made before migrations existed):
  adopts the current state as the baseline, without touching any data.
- Otherwise: applies whatever migrations are still pending.
"""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import inspect

from app.infrastructure.database import engine


def main() -> None:
    cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
    tables = set(inspect(engine).get_table_names())
    if "alembic_version" not in tables and "users" in tables:
        print("Existing database without migration history: adopting it as the baseline.")
        from app.infrastructure.database import ensure_columns
        ensure_columns()  # make sure the old stop-gap columns exist, so the schema equals the baseline
        command.stamp(cfg, "head")
    else:
        command.upgrade(cfg, "head")
    print("Database is up to date.")


if __name__ == "__main__":
    main()
