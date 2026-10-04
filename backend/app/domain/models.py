import uuid
import enum
from datetime import date
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, Enum, Text, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base


class HabitCategory(str, enum.Enum):
    BODY = "body"          # Βορράς — άσκηση, φυσική δραστηριότητα
    MIND = "mind"          # Νότος — mental health, διαλογισμός
    WORK = "work"          # Δύση — δουλειά, διάβασμα
    SCHEDULE = "schedule"  # Ανατολή — πρόγραμμα, υπενθυμίσεις


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    total_points = Column(Integer, default=0, nullable=False)

    habits = relationship("Habit", back_populates="user")


class Habit(Base):
    __tablename__ = "habits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    frequency = Column(String, nullable=False)
    category = Column(Enum(HabitCategory), nullable=False, default=HabitCategory.BODY)

    user = relationship("User", back_populates="habits")
    check_ins = relationship("CheckIn", back_populates="habit", cascade="all, delete-orphan")

class CheckIn(Base):
    __tablename__ = "check_ins"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    habit_id = Column(UUID(as_uuid=True), ForeignKey("habits.id"), nullable=False)
    check_date = Column(Date, nullable=False, default=date.today)
    completed = Column(Boolean, default=True, nullable=False)

    habit = relationship("Habit", back_populates="check_ins")


# ─── Βορράς: Σώμα ───────────────────────────────────────

class NutritionLog(Base):
    __tablename__ = "nutrition_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    log_date = Column(Date, nullable=False, default=date.today)
    meal_description = Column(String, nullable=False)
    calories = Column(Integer, nullable=True)


# ─── Νότος: Mental Health ───────────────────────────────

class JournalEntry(Base):
    __tablename__ = "journal_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    entry_date = Column(Date, nullable=False, default=date.today)
    content = Column(Text, nullable=False)
    mood = Column(String, nullable=True)  # π.χ. "good" | "neutral" | "bad"