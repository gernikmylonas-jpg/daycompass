from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import Base, engine, SessionLocal, ensure_columns
from app.domain import models
from app.api.routers import auth, habits, stats, pomodoro, badges, groups, wellness, reminders, settings, events, journal, mood, meditation
from app.application.services.badges import seed_badges

Base.metadata.create_all(bind=engine)
ensure_columns()

with SessionLocal() as _db:
    seed_badges(_db)

app = FastAPI(title="DayCompass API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(habits.router)
app.include_router(stats.router)
app.include_router(pomodoro.router)
app.include_router(badges.router)
app.include_router(groups.router)
app.include_router(wellness.router)
app.include_router(reminders.router)
app.include_router(settings.router)
app.include_router(events.router)
app.include_router(journal.router)
app.include_router(mood.router)
app.include_router(meditation.router)


@app.get("/")
def root():
    return {"status": "DayCompass API running"}
