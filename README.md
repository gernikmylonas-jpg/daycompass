# DayCompass

Habit tracking + wellness app (Vue 3 + TypeScript frontend, FastAPI backend, PostgreSQL, Celery + Redis).
UI languages: English, Español, Français, Ελληνικά.

## Local development

```bash
# 1. Infrastructure (Postgres + Redis)
docker compose up -d

# 2. Backend (from backend/, with the venv activated)
pip install -r requirements.txt
uvicorn app.main:app --reload            # http://localhost:8000  (docs at /docs)

# 3. Background worker + scheduler (optional; needed for email reminders / nightly job)
celery -A app.worker.celery_app worker --pool=solo --loglevel=info   # --pool=solo is for Windows
celery -A app.worker.celery_app beat --loglevel=info

# 4. Frontend (from frontend/)
npm install
npm run dev                              # http://localhost:5173
```

## Everything in containers

```bash
docker compose --profile full up -d --build   # api :8000, worker, beat, Postgres, Redis
```

## Configuration

Read from environment variables or `backend/.env` (never commit it).

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | local Postgres | database connection |
| `JWT_SECRET` | placeholder | **set a long random value outside local dev** |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker / result backend |
| `TIMEZONE` | `Europe/Athens` | timezone of the schedule (also set `TZ` in containers) |
| `REMINDER_HOUR` / `REMINDER_MINUTE` | `20` / `0` | daily reminder time |
| `MAINTENANCE_HOUR` / `MAINTENANCE_MINUTE` | `3` / `30` | nightly recalculation time |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `MAIL_FROM` | empty | email delivery; **without `SMTP_HOST` reminders are only written to the worker log** |
| `APP_URL` | `http://localhost:5173` | link included in reminder emails |

## Background jobs

- **Daily reminder** — emails users who opted in (checkbox on the home page) and still have unchecked habits today. At most one email per user per day.
- **Nightly recalculation** — grants goal points that were never awarded, re-evaluates badges, and logs any mismatch between stored points and activity history (report only; it never changes totals).

## Adding UI text

Add every new string to all four files in `frontend/src/i18n/locales/`. `es`, `fr` and `el` are typed from `en.ts`, so a missing key fails `vue-tsc`.
