from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.infrastructure.database import Base, engine
from app.domain import models
from app.api.routers import auth, habits

Base.metadata.create_all(bind=engine)

app = FastAPI(title="DayCompass API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(habits.router)

@app.get("/")
def root():
    return {"status": "DayCompass API running"}