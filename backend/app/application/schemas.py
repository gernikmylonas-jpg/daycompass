from datetime import date
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


class HabitResponse(BaseModel):
    id: UUID
    name: str
    frequency: str
    category: str
    checked_in_today: bool = False

    class Config:
        from_attributes = True


class CheckInResponse(BaseModel):
    id: UUID
    habit_id: UUID
    check_date: date
    completed: bool

    class Config:
        from_attributes = True
        