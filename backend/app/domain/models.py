import uuid
import enum
from datetime import date, datetime
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, Enum, Text, Float, DateTime, UniqueConstraint
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


# ─── Δύση: Pomodoro ─────────────────────────────────────

class PomodoroSession(Base):
    __tablename__ = "pomodoro_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    kind = Column(String, nullable=False)  # "work" | "reading"
    title = Column(String, nullable=True)
    duration_minutes = Column(Integer, nullable=False)
    session_date = Column(Date, nullable=False, default=date.today)
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Κέντρο: Badges ─────────────────────────────────────

class Badge(Base):
    __tablename__ = "badges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(String, unique=True, nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String, nullable=False)
    icon = Column(String, nullable=False)


class UserBadge(Base):
    __tablename__ = "user_badges"
    __table_args__ = (UniqueConstraint("user_id", "badge_id", name="uq_user_badge"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    badge_id = Column(UUID(as_uuid=True), ForeignKey("badges.id"), nullable=False)
    awarded_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Groups & Challenges ────────────────────────────────

class Group(Base):
    __tablename__ = "groups"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    invite_code = Column(String, unique=True, nullable=False, index=True)
    owner_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    __tablename__ = "group_members"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_member"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    joined_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    group = relationship("Group", back_populates="members")


# ─── Steps & Sleep (χειροκίνητη καταγραφή) ───────────────

class StepLog(Base):
    __tablename__ = "step_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_step_log_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, default=date.today)
    steps = Column(Integer, nullable=False)
    points_awarded = Column(Integer, nullable=False, default=0)


class SleepLog(Base):
    __tablename__ = "sleep_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_sleep_log_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, default=date.today)  # day the user woke up
    minutes = Column(Integer, nullable=False)
    quality = Column(Integer, nullable=True)  # 1..5
    points_awarded = Column(Integer, nullable=False, default=0)


# ─── Reminders ──────────────────────────────────────────

class ReminderSetting(Base):
    """Opt-in email reminder preference. No row means reminders are off."""
    __tablename__ = "reminder_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    enabled = Column(Boolean, nullable=False, default=False)
    language = Column(String, nullable=False, default="en")


class ReminderLog(Base):
    """One row per user per day that was mailed, so re-running the job never double-sends."""
    __tablename__ = "reminder_logs"
    __table_args__ = (UniqueConstraint("user_id", "sent_on", name="uq_reminder_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    sent_on = Column(Date, nullable=False)
