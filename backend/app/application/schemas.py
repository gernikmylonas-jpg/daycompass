from datetime import date, datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    total_points: int

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    token: str
    user: UserResponse


class HabitCreate(BaseModel):
    name: str
    frequency: str
    category: str


class HabitUpdate(BaseModel):
    name: Optional[str] = None
    category: Optional[str] = None


class HabitResponse(BaseModel):
    id: UUID
    name: str
    frequency: str
    category: str
    checked_in_today: bool = False
    current_streak: int = 0
    best_streak: int = 0

    class Config:
        from_attributes = True


class BadgeInfo(BaseModel):
    code: str
    name: str
    description: str
    icon: str

    class Config:
        from_attributes = True


class BadgeStatus(BadgeInfo):
    earned: bool = False
    awarded_at: Optional[datetime] = None


class CheckInResponse(BaseModel):
    id: UUID
    habit_id: UUID
    check_date: date
    completed: bool
    new_badges: list[BadgeInfo] = []

    class Config:
        from_attributes = True


class HeatmapDay(BaseModel):
    date: date
    count: int


class CalendarEntry(BaseModel):
    date: date
    habit_id: UUID
    habit_name: str
    category: str


class PomodoroCreate(BaseModel):
    kind: str
    duration_minutes: int
    title: Optional[str] = None


class PomodoroResponse(BaseModel):
    id: UUID
    kind: str
    title: Optional[str] = None
    duration_minutes: int
    session_date: date
    completed_at: datetime
    new_badges: list[BadgeInfo] = []

    class Config:
        from_attributes = True


class PomodoroSummary(BaseModel):
    today_minutes: int
    today_sessions: int
    total_minutes: int
    total_sessions: int
    recent: list[PomodoroResponse]
