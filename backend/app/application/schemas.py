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
    frequency: Optional[str] = None  # "daily" or "weekly:N"


class HabitResponse(BaseModel):
    id: UUID
    name: str
    frequency: str
    category: str
    checked_in_today: bool = False
    current_streak: int = 0   # days for daily habits, weeks for weekly ones
    best_streak: int = 0
    target_per_week: Optional[int] = None
    week_count: int = 0       # check-ins so far this week (Monday-Sunday)

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


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None


class GroupJoin(BaseModel):
    invite_code: str


class GroupSummary(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    invite_code: str
    is_owner: bool
    member_count: int
    my_rank: int
    new_badges: list[BadgeInfo] = []


class LeaderboardEntry(BaseModel):
    rank: int
    user_id: UUID
    name: str
    points: int
    is_me: bool
    has_photo: bool = False  # a picture its owner chose to share with their groups (or my own)


class GroupDetail(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    invite_code: str
    is_owner: bool
    period: str
    leaderboard: list[LeaderboardEntry]


class StepLogUpsert(BaseModel):
    steps: int
    log_date: Optional[date] = None


class SleepLogUpsert(BaseModel):
    minutes: int
    quality: Optional[int] = None
    log_date: Optional[date] = None


class StepLogResponse(BaseModel):
    log_date: date
    steps: int
    goal_reached: bool
    points_awarded: int
    new_badges: list[BadgeInfo] = []


class SleepLogResponse(BaseModel):
    log_date: date
    minutes: int
    quality: Optional[int] = None
    goal_reached: bool
    points_awarded: int
    new_badges: list[BadgeInfo] = []


class WellnessDay(BaseModel):
    date: date
    steps: Optional[int] = None
    sleep_minutes: Optional[int] = None
    sleep_quality: Optional[int] = None


class WellnessSummary(BaseModel):
    step_goal: int
    sleep_goal_minutes: int
    avg_steps_7d: int
    avg_sleep_minutes_7d: int
    days: list[WellnessDay]  # last 14 days, oldest first


class ReminderSettings(BaseModel):
    enabled: bool
    events_enabled: bool = False
    language: str = "en"


class SettingsPayload(BaseModel):
    theme: str
    mode: str
    needle_cursor: bool
    language: Optional[str] = None
    mood_style: str = "emoji"
    depth_3d: bool = False
    wallpaper: Optional[str] = None  # an unlocked wallpaper id
    wallpapers_on: bool = False
    quests_on: bool = False
    calendar_prefs: Optional[str] = None  # JSON text, opaque to the server (max 2000 characters)
    lid_open: bool = False  # play the compass lid animation on the home screen
    brightness: int = 100  # lighting of the compass face, percent


class SettingsResponse(SettingsPayload):
    saved: bool  # False when the account has never stored settings (client keeps its local ones)


class EventCreate(BaseModel):
    title: str
    event_date: date
    kind: str = "note"
    notes: Optional[str] = None
    repeat_yearly: bool = False
    repeat_weekly: bool = False


class EventResponse(BaseModel):
    id: UUID
    title: str
    kind: str
    notes: Optional[str] = None
    repeat_yearly: bool
    repeat_weekly: bool = False
    date: date           # the day this occurrence falls on
    original_date: date  # the day it was created for (birthdays repeat every year)
    new_badges: list[BadgeInfo] = []


class PointsSource(BaseModel):
    count: int
    points: int


class PointsBreakdown(BaseModel):
    total: int
    check_ins: PointsSource
    pomodoros: PointsSource
    meditations: PointsSource
    steps: PointsSource
    sleep: PointsSource
    other: int  # total minus everything explained above (e.g. points kept from deleted habits)


class JournalEntryResponse(BaseModel):
    id: UUID
    entry_date: date
    content: str
    mood: Optional[str] = None
    created_at: datetime
    has_audio: bool = False
    audio_seconds: int = 0
    audio_mime: Optional[str] = None
    new_badges: list[BadgeInfo] = []


class JournalPage(BaseModel):
    entries: list[JournalEntryResponse]
    total: int


class JournalUpdate(BaseModel):
    entry_date: date
    content: str = ""
    mood: Optional[str] = None


class StreakResponse(BaseModel):
    current: int      # days in a row (up to today or yesterday) with at least one habit check-in
    best: int
    active_today: bool


class ProfileUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[EmailStr] = None
    current_password: Optional[str] = None  # required to change the email


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class MoodUpsert(BaseModel):
    score: int
    log_date: Optional[date] = None
    note: Optional[str] = None


class MoodDay(BaseModel):
    date: date
    score: int
    note: Optional[str] = None


class MoodLogResponse(MoodDay):
    new_badges: list[BadgeInfo] = []


class MoodSummary(BaseModel):
    days: list[MoodDay]          # most recent first
    today: Optional[int] = None
    avg_7d: Optional[float] = None
    avg_30d: Optional[float] = None
    logged_total: int


class MeditationCreate(BaseModel):
    duration_minutes: int
    kind: str = "breathing"


class MeditationItem(BaseModel):
    id: UUID
    kind: str
    duration_minutes: int
    session_date: date
    completed_at: datetime


class MeditationResponse(MeditationItem):
    points_awarded: int = 0
    new_badges: list[BadgeInfo] = []


class MeditationSummary(BaseModel):
    today_minutes: int
    today_sessions: int
    total_minutes: int
    total_sessions: int
    current_streak: int
    recent: list[MeditationItem]


class WellnessHistory(BaseModel):
    days: list[WellnessDay]  # newest first
    total: int               # number of days that have any steps or sleep logged
    steps_logged: int
    avg_steps: int
    best_steps: int
    sleep_logged: int
    avg_sleep_minutes: int


class ChallengeCreate(BaseModel):
    title: str
    metric: str
    target: int
    start_date: date
    end_date: date


class ChallengeMember(BaseModel):
    user_id: UUID
    name: str
    progress: int
    done: bool
    is_me: bool


class ChallengeResponse(BaseModel):
    id: UUID
    title: str
    metric: str
    target: int
    start_date: date
    end_date: date
    status: str          # upcoming | active | finished
    days_left: int
    completed_count: int
    members: list[ChallengeMember]  # most progress first


class Correlation(BaseModel):
    key: str            # sleep | meditation | steps | checkin
    n_with: int
    n_without: int
    avg_with: float     # average mood on days with the habit
    avg_without: float


class ReportResponse(BaseModel):
    period: str
    start: date
    end: date
    axes: dict[str, Optional[float]]   # 0-100 per direction-like area, None = no data
    checkins: int
    active_days: int
    days: int
    points_earned: int
    pomodoro_minutes: int
    meditation_minutes: int
    avg_steps: Optional[int] = None
    avg_sleep_minutes: Optional[int] = None
    avg_mood: Optional[float] = None
    prev_avg_mood: Optional[float] = None
    journal_entries: int
    weekdays: list[int]                # check-ins by weekday, Monday first
    correlations: list[Correlation]
