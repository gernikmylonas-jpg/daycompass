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

## Compass styles

The **Settings** menu (top right) switches between 7 compass styles and toggles the needle cursor. Choices are stored in the browser. To add a style: add a `html[data-theme="…"]` block in `frontend/src/style.css`, an entry in `THEMES` (`frontend/src/stores/settings.ts`) and its name under `settings.themes` in all four locale files.

## The compass home screen

The home page is a big compass with eight directions. N, E, S and W hold habits (steps & sleep sit inside N), SW is the Pomodoro timer, SE the calendar (2000–2100, with notes, birthdays and reminders), NW the groups, and NE is still reserved. Pressing a letter opens that direction's panel; the ring around each letter shows today's progress. The symbol in the middle (different for every compass style, and it turns to face the pointer) opens points and badges. Clicking the "DayCompass" title opens a short guide.

To give a reserved direction a feature, change its entry in `directions` in `frontend/src/views/HomeView.vue` (`kind: 'soon'` becomes `'habits'`, `'pomodoro'`, `'groups'`, `'calendar'` or a new kind) and add its panel next to the others.

## What is inside each direction

| Direction | Contents |
|---|---|
| N | Body habits · **Steps** (log any date since 2000; complete history, no retention limit) |
| E | Schedule habits · **Calendars: Moon & eclipses** (moon phases for every day 2000–2100, solar and lunar eclipses, equinoxes/solstices, meteor showers) |
| S | Mind habits · **Journal** (write and/or record your voice; private to your account) · **Daily mood** (1–10 as emoji, colours or words) · **Meditation** (timer with a breathing guide, +5 points) |
| W | Work & study habits |
| NW | Groups with a live leaderboard |
| SE | Calendar 2000–2100 with notes, birthdays and reminders (right-click a day to add one) |
| SW | Pomodoro timer |
| NE | **Sleep** (hours, quality; complete history, no retention limit) |

Dates are always shown day / month / year. The astronomy is computed in the browser (`frontend/src/astronomy.ts`, Meeus' *Astronomical Algorithms*); results agree with published data to about a minute. Journal recordings are stored in the database (`journal_audio`), limited to 8 MB / 10 minutes each, and are served only to their owner. `ensure_columns()` in `backend/app/infrastructure/database.py` adds columns introduced after a table was created, until Alembic migrations are set up.

## Profile, streak and badges

Click your name (top right on the compass) for your profile: name, email, password change and a summary. Passwords are stored hashed, so they can only be changed, never shown (minimum 8 characters). The flame next to your name is your **daily streak**: days in a row with at least one habit check-in. The symbol in the middle opens points and the **55 badges**, which have their own artwork (`frontend/src/badgeArt.ts`) and are awarded by the rules in `backend/app/application/services/badges.py`. To add a badge: add it to the catalog and `RULES` there, give it art in `badgeArt.ts` and add its name/description to the four locale files.

## Your settings follow your account

Compass style, light/dark mode, the needle cursor and the language are stored on the server (`/api/settings`), so they appear on any device once you sign in. This device's copy is only used until you are signed in. Calendar notes live in `calendar_events`.

## Weekly habits, rest days, challenges, report

- **Weekly habits** ("3 times a week", ISO weeks Monday–Sunday): their streak counts weeks that reached the target; the running week never breaks it.
- **Rest days** (calendar → pick a day → *Rest day*; from a week back to three days ahead, at most 2 in any 7) bridge the gap for daily streaks.
- **Group challenges**: the group owner sets a goal (check-ins, steps, meditation, …) for a date range; progress is measured from each member's own activity.
- **Compass report** (`/report`): balance radar for the last 7/30 days plus patterns found in your own data (e.g. mood after good sleep).
- **Journal lock**: optional PIN; entries are encrypted at rest with a key derived from it (scrypt + Fernet). The PIN is only kept in memory and sent as `X-Journal-Pin`; a forgotten PIN cannot be recovered.
- **Your data**: Profile → download everything as JSON, or delete the account and all its data.
- **Calendar notes by email**: a daily job (08:00, `EVENTS_HOUR`/`EVENTS_MINUTE`) mails the notes of the day, at most once per day.
- **Sun times** for your place (Moon tab → *Use my location*; stays in the browser) and lunar-eclipse visibility.
- **Installable / offline shell** (PWA, production build only). API data is never cached.

## Extra calendars

In the calendar, switch on any of: **public holidays** of a country (computed by the `holidays` package, any country), **Orthodox name days** (`frontend/src/calendars/nameDays.ts`, movable feasts from Orthodox Easter), **national days** of ~190 countries and **history & fun facts** (`history.ts`: add rows to `ROWS` in English and Greek). The choice follows the account. Notes can repeat yearly or weekly (a weekly timetable).

## Steps and weight (North)

- **Steps**: a progress ring for the chosen day (goal 8,000; a second lap after the goal), quick-add buttons (+500 … +5,000), a goal streak and a bar chart for 7 days / 30 days / 12 months (`/api/wellness/steps/series`).
- **Weight**: one reading a day, a 7-day trend line (single readings are noisy), optional goal, height and BMI (off by default), kg or lb. It awards no points for a result, only badges for logging; a gentle note appears if the trend falls faster than ~1.5% of body weight a week.

## Gold nuggets and wallpapers

Every 10 points earned = 1 gold nugget (`POINTS_PER_NUGGET`). Nuggets buy wallpapers on the points page; points are never reduced, and every purchase is stored (`wallpaper_unlocks`) so the history is always there. Wallpapers are drawn in code (`frontend/src/wallpapers/art.ts`) and are optional: *Settings → Wallpapers* switches them on/off and picks one you own. To add one: catalog entry in `backend/app/application/services/wallpapers.py`, a function in `art.ts`, texts in the four locale files (a test checks all three).

## Running it from anywhere, desktop icon

See `DEPLOY.md` (one small server with `docker compose --profile full up -d --build`, a home server plus a tunnel, or managed services). `scripts/create-desktop-shortcut.ps1` puts a DayCompass icon on your Desktop that starts everything locally and opens the app. In a production build the app is installable (browser menu: *Install*). Offline mode is opt-in in Settings.

**Nothing happens unless you choose it:** reminders and e-mails, lid, 3D, wallpapers, extra calendars, BMI, goals, offline mode and location are all off until you switch them on.

## More trackers (all opt-in, all yours alone)

North: water (glasses), workouts. South: gratitude. West: focus sounds (generated in the browser). Calendar: import/export `.ics`, a *Journal days* layer that marks days that have entries or voice recordings (counts only). Profile: a picture shown only on the profile page and never served to anyone else. *Settings → Daily quest* shows one small challenge a day worth an extra nugget.

## Planets, groups, small extras

*Moon & eclipses → Sky events* also lists planetary oppositions, greatest elongations, conjunctions with the Sun and between planets, and the Earth's perihelion/aphelion (`frontend/src/planets.ts`, from JPL's approximate Keplerian elements; about a day of accuracy up to 2050), plus which planets are in the evening or morning sky today. Groups have shared habits with a group streak (everyone must do it), one-emoji cheers, and optional profile pictures (a member's picture is shown to their groups only if they switch it on in their profile). Focus time is totalled per session title, and the breathing exercises have more patterns.

## Tests and CI

`cd backend && pip install -r requirements-dev.txt && pytest` (needs the Postgres from docker compose; uses its own `daycompass_test` database). `cd frontend && npm test`. GitHub Actions (`.github/workflows/ci.yml`) runs both, plus `vue-tsc` and the build.

## Adding UI text

Add every new string to all four files in `frontend/src/i18n/locales/`. `es`, `fr` and `el` are typed from `en.ts`, so a missing key fails `vue-tsc`.
