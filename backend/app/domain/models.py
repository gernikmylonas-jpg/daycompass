import uuid
import enum
from datetime import date, datetime
from sqlalchemy import Column, String, Integer, Date, Boolean, ForeignKey, Enum, Text, Float, DateTime, UniqueConstraint, LargeBinary
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
    content = Column(Text, nullable=False, default="")
    mood = Column(String, nullable=True)  # "good" | "neutral" | "bad"
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    encrypted = Column(Boolean, nullable=False, default=False)  # content is a Fernet token


class JournalAudio(Base):
    """A voice recording attached to a journal entry (stored in the database, owner-only)."""
    __tablename__ = "journal_audio"

    entry_id = Column(UUID(as_uuid=True), ForeignKey("journal_entries.id"), primary_key=True)
    mime = Column(String, nullable=False)
    seconds = Column(Integer, nullable=False, default=0)
    data = Column(LargeBinary, nullable=False)
    encrypted = Column(Boolean, nullable=False, default=False)


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
    challenges = relationship("Challenge", cascade="all, delete-orphan")


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


# ─── User preferences (follow the account across devices) ───

class UserSettings(Base):
    __tablename__ = "user_settings"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    theme = Column(String, nullable=False, default="classic")
    mode = Column(String, nullable=False, default="system")  # light | dark | system
    needle_cursor = Column(Boolean, nullable=False, default=True)
    language = Column(String, nullable=True)
    mood_style = Column(String, nullable=False, default="emoji")  # emoji | colors | words
    depth_3d = Column(Boolean, nullable=False, default=False)
    brightness = Column(Integer, nullable=False, default=100)
    lid_open = Column(Boolean, nullable=False, default=False)
    wallpaper = Column(String, nullable=True)  # id of the chosen wallpaper (must be unlocked)
    wallpapers_on = Column(Boolean, nullable=False, default=False)
    quests_on = Column(Boolean, nullable=False, default=False)
    calendar_prefs = Column(Text, nullable=True)  # JSON: which calendar layers are shown
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Calendar notes: birthdays, reminders, free notes ───────

class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    event_date = Column(Date, nullable=False, index=True)
    title = Column(String, nullable=False)
    kind = Column(String, nullable=False, default="note")  # birthday | reminder | event | note
    notes = Column(Text, nullable=True)
    repeat_yearly = Column(Boolean, nullable=False, default=False)
    repeat_weekly = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Mood (1-10 a day) and meditation ───────────────────

class MoodLog(Base):
    __tablename__ = "mood_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_mood_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, default=date.today)
    score = Column(Integer, nullable=False)  # 1..10
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class MeditationSession(Base):
    __tablename__ = "meditation_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    kind = Column(String, nullable=False, default="breathing")  # breathing | silent
    duration_minutes = Column(Integer, nullable=False)
    session_date = Column(Date, nullable=False, default=date.today)
    completed_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Rest days (keep a streak alive without a check-in) ───

class RestDay(Base):
    __tablename__ = "rest_days"
    __table_args__ = (UniqueConstraint("user_id", "rest_date", name="uq_rest_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    rest_date = Column(Date, nullable=False)


# ─── Group challenges ───────────────────────────────────

class Challenge(Base):
    __tablename__ = "challenges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    created_by = Column(UUID(as_uuid=True), nullable=True)
    title = Column(String, nullable=False)
    metric = Column(String, nullable=False)  # see services/challenges.METRICS
    target = Column(Integer, nullable=False)  # each member's goal for the period
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Journal lock (PIN) and event e-mails ───────────────

class JournalLock(Base):
    """Present when the user locked their journal with a PIN. Only a salt and an encrypted
    check value are stored, never the PIN; the key is derived from the PIN on every request."""
    __tablename__ = "journal_locks"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    salt = Column(LargeBinary, nullable=False)
    check_token = Column(LargeBinary, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class EventMailLog(Base):
    """One row per user per day that received their calendar-notes e-mail."""
    __tablename__ = "event_mail_logs"
    __table_args__ = (UniqueConstraint("user_id", "sent_on", name="uq_event_mail_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    sent_on = Column(Date, nullable=False)


# ─── Weight ─────────────────────────────────────────────

class WeightLog(Base):
    __tablename__ = "weight_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_weight_log_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, default=date.today)
    kg = Column(Float, nullable=False)


class WeightProfile(Base):
    __tablename__ = "weight_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    height_cm = Column(Integer, nullable=True)
    goal_kg = Column(Float, nullable=True)
    unit = Column(String, nullable=False, default="kg")  # kg | lb
    show_bmi = Column(Boolean, nullable=False, default=False)


# ─── Nuggets: what has been spent on wallpapers ──────────

class WallpaperUnlock(Base):
    __tablename__ = "wallpaper_unlocks"
    __table_args__ = (UniqueConstraint("user_id", "wallpaper_id", name="uq_wallpaper_unlock"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    wallpaper_id = Column(String, nullable=False)
    cost = Column(Integer, nullable=False)  # nuggets paid, kept even if the price changes later
    unlocked_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Personal goals with a deadline ─────────────────────

class Goal(Base):
    __tablename__ = "goals"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, nullable=False)
    metric = Column(String, nullable=False)  # same metrics as group challenges
    target = Column(Integer, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Water, workouts, gratitude, daily quests ───────────

class WaterLog(Base):
    __tablename__ = "water_logs"
    __table_args__ = (UniqueConstraint("user_id", "log_date", name="uq_water_log_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    log_date = Column(Date, nullable=False, default=date.today)
    glasses = Column(Integer, nullable=False)


class Workout(Base):
    __tablename__ = "workouts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    workout_date = Column(Date, nullable=False, default=date.today, index=True)
    kind = Column(String, nullable=False)
    minutes = Column(Integer, nullable=False)
    note = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GratitudeEntry(Base):
    __tablename__ = "gratitude_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    entry_date = Column(Date, nullable=False, default=date.today, index=True)
    text = Column(String, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class QuestReward(Base):
    """One row per day a quest was completed and its nugget claimed."""
    __tablename__ = "quest_rewards"
    __table_args__ = (UniqueConstraint("user_id", "reward_date", name="uq_quest_reward_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    reward_date = Column(Date, nullable=False)
    quest_id = Column(String, nullable=False)


class ProfilePhoto(Base):
    __tablename__ = "profile_photos"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    mime = Column(String, nullable=False)
    data = Column(LargeBinary, nullable=False)
    share_with_groups = Column(Boolean, nullable=False, default=False)  # opt-in: people in my groups may see it
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# ─── Group shared habits and cheers ─────────────────────

class GroupHabit(Base):
    __tablename__ = "group_habits"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class GroupHabitCheck(Base):
    __tablename__ = "group_habit_checks"
    __table_args__ = (UniqueConstraint("habit_id", "user_id", "check_date", name="uq_group_habit_check"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    habit_id = Column(UUID(as_uuid=True), ForeignKey("group_habits.id"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)
    check_date = Column(Date, nullable=False)


class Cheer(Base):
    __tablename__ = "cheers"
    __table_args__ = (UniqueConstraint("group_id", "from_user", "to_user", "cheer_date", name="uq_cheer_pair_day"),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    group_id = Column(UUID(as_uuid=True), ForeignKey("groups.id"), nullable=False, index=True)
    from_user = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    to_user = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    emoji = Column(String, nullable=False)
    cheer_date = Column(Date, nullable=False)
