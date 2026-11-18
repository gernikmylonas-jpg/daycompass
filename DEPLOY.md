# Using DayCompass without running it on your own computer

The app is three parts: the **site** (static files), the **API** (FastAPI) and the **database** (Postgres, plus Redis and the
worker for e-mails). Nothing in the code ties it to one machine any more: in a production build the site talks to
the API at **its own address** (`/api`), and `CORS_ORIGINS` / `APP_URL` / `VITE_API_URL` are settings, not constants.

## Option A — one small server, everything in containers (recommended)
1. Any VPS (a few euros a month) with Docker. Copy the repository there.
2. Create `.env` next to `docker-compose.yml`:
   ```
   JWT_SECRET=<a long random string>
   SITE_ADDRESS=app.yourdomain.com      # or :80 for plain http on a LAN
   APP_URL=https://app.yourdomain.com
   TZ=Europe/Athens
   SMTP_HOST=...  SMTP_USER=...  SMTP_PASSWORD=...   # only if you want e-mail reminders
   ```
3. Point the domain's DNS at the server and run `docker compose --profile full up -d --build`.
   Caddy gets the https certificate by itself. Open `https://app.yourdomain.com` from any device and, in Chrome/Edge/Safari,
   use *Install app* / *Add to Home Screen* to get an icon.
4. Back up the `pgdata` volume (`docker exec daycompass-db pg_dump -U postgres daycompass > backup.sql`).

## Option B — keep it at home, reach it from anywhere
Leave it running on one computer and add a **Cloudflare Tunnel** or **Tailscale** (no open router ports, free for personal use).
Run the same `docker compose --profile full up -d --build`, then expose port 80 through the tunnel / your tailnet.

## Option C — managed services (no server to look after)
Static site on Netlify/Vercel/Cloudflare Pages, the API on Fly.io/Render, the database on Neon/Supabase.
Build the site with `VITE_API_URL=https://your-api.example.com`, and set `CORS_ORIGINS=https://your-site.example.com` on the API.
(The worker/beat need a second small service if you want e-mails.)

## Database migrations and backups
- The API container runs `python -m app.migrate` at start: a new database gets every table, an existing one is brought up to date
  (`backend/alembic/versions`). After you change `backend/app/domain/models.py`, create the migration with
  `cd backend && alembic revision --autogenerate -m "what changed"` and commit it (a test fails if you forget).
- **Backups** (do this before you rely on it): `scripts/backup-db.sh` on a Linux server (cron it, e.g. `0 3 * * *`) or `scripts/backup-db.ps1` on Windows.
  `scripts/restore-db.*` puts a file back; try it first into a throw-away database (`-Database daycompass_check`). Copy the files off the server.

## Optional: push notifications
Generate keys with `cd backend && venv/Scripts/python ../scripts/make-vapid-keys.py`, put the three `VAPID_*` lines in `.env` and restart. Push needs https
(or localhost). People switch it on themselves in Settings; without keys the option just says it is unavailable.

## Before real users
Set `JWT_SECRET` (the API refuses to start on an https address with the placeholder), do not publish the database port, keep `.env` out of git (it already is), and run
`pytest` and `npm test` (the CI workflow does this on every push). Repeated wrong passwords/PINs are slowed down (429) in the API itself; the web server adds the usual security headers.
