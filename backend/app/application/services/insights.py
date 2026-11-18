from collections import defaultdict
from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.domain.models import (
    Habit, CheckIn, StepLog, SleepLog, PomodoroSession, MeditationSession, MoodLog, JournalEntry,
)
from app.application.services.points import (
    STEP_GOAL, SLEEP_GOAL_MINUTES, POINTS_PER_CHECK_IN, POINTS_PER_POMODORO, POINTS_PER_MEDITATION,
    POINTS_PER_STEP_GOAL, POINTS_PER_SLEEP_GOAL,
)
from app.application.schemas import ReportResponse, Correlation

PERIOD_DAYS = {"week": 7, "month": 30}
CORRELATION_DAYS = 90      # a longer window gives the comparisons enough data
MIN_SAMPLES = 3            # per side of a comparison
MEDITATION_TARGET = 10     # minutes a day that counts as a full score
FOCUS_TARGET = 60          # pomodoro minutes a day that counts as a full score


def _avg(values) -> float | None:
    values = list(values)
    return round(sum(values) / len(values), 2) if values else None


def _pct(value: float) -> float:
    return round(max(0.0, min(100.0, value)), 1)


def build_report(db: Session, user_id: str, period: str) -> ReportResponse:
    days = PERIOD_DAYS[period]
    end = date.today()
    start = end - timedelta(days=days - 1)
    prev_start, prev_end = start - timedelta(days=days), start - timedelta(days=1)
    long_start = end - timedelta(days=CORRELATION_DAYS - 1)

    habits = db.query(Habit).filter(Habit.user_id == user_id).all()
    checks = (
        db.query(CheckIn.check_date, Habit.category)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True), CheckIn.check_date >= long_start)
        .all()
    )
    steps = {l.log_date: l.steps for l in db.query(StepLog).filter(StepLog.user_id == user_id, StepLog.log_date >= long_start)}
    sleeps = {l.log_date: l.minutes for l in db.query(SleepLog).filter(SleepLog.user_id == user_id, SleepLog.log_date >= long_start)}
    pomodoro = defaultdict(int)
    for s in db.query(PomodoroSession).filter(PomodoroSession.user_id == user_id, PomodoroSession.session_date >= long_start):
        pomodoro[s.session_date] += s.duration_minutes
    meditation = defaultdict(int)
    for s in db.query(MeditationSession).filter(MeditationSession.user_id == user_id, MeditationSession.session_date >= long_start):
        meditation[s.session_date] += s.duration_minutes
    moods = {m.log_date: m.score for m in db.query(MoodLog).filter(MoodLog.user_id == user_id, MoodLog.log_date >= long_start - timedelta(days=days))}
    journal_days = {j.entry_date for j in db.query(JournalEntry).filter(JournalEntry.user_id == user_id, JournalEntry.entry_date >= long_start)}

    def in_period(d: date) -> bool:
        return start <= d <= end

    # ── habit completion per category (0-100) ──
    per_category = defaultdict(int)
    for d, category in checks:
        if in_period(d):
            per_category[category.value] += 1
    expected = defaultdict(float)
    for h in habits:
        weekly = h.frequency.partition(":")
        per_day = int(weekly[2]) / 7 if weekly[0] == "weekly" and weekly[2].isdigit() else 1.0
        expected[h.category.value] += per_day * days
    habit_axis = {c: (_pct(per_category[c] / expected[c] * 100) if expected[c] else None)
                  for c in ("body", "mind", "schedule", "work")}

    p_steps = [v for d, v in steps.items() if in_period(d)]
    p_sleep = [v for d, v in sleeps.items() if in_period(d)]
    p_mood = [v for d, v in moods.items() if in_period(d)]
    prev_mood = [v for d, v in moods.items() if prev_start <= d <= prev_end]
    focus_minutes = sum(v for d, v in pomodoro.items() if in_period(d))
    calm_minutes = sum(v for d, v in meditation.items() if in_period(d))

    axes = {
        **habit_axis,
        "movement": _pct(sum(p_steps) / len(p_steps) / STEP_GOAL * 100) if p_steps else None,
        "sleep": _pct(sum(p_sleep) / len(p_sleep) / SLEEP_GOAL_MINUTES * 100) if p_sleep else None,
        "focus": _pct(focus_minutes / (days * FOCUS_TARGET) * 100) if focus_minutes else None,
        "calm": _pct(calm_minutes / (days * MEDITATION_TARGET) * 100) if calm_minutes else None,
    }

    check_days = {d for d, _ in checks if in_period(d)}
    active = (
        check_days | {d for d in steps if in_period(d)} | {d for d in sleeps if in_period(d)}
        | {d for d in pomodoro if in_period(d)} | {d for d in meditation if in_period(d)}
        | {d for d in moods if in_period(d)} | {d for d in journal_days if in_period(d)}
    )
    points = (
        sum(1 for d, _ in checks if in_period(d)) * POINTS_PER_CHECK_IN
        + sum(1 for d in pomodoro if in_period(d)) * 0
        + db.query(PomodoroSession).filter(PomodoroSession.user_id == user_id, PomodoroSession.session_date.between(start, end)).count() * POINTS_PER_POMODORO
        + db.query(MeditationSession).filter(MeditationSession.user_id == user_id, MeditationSession.session_date.between(start, end)).count() * POINTS_PER_MEDITATION
        + sum(1 for d, v in steps.items() if in_period(d) and v >= STEP_GOAL) * POINTS_PER_STEP_GOAL
        + sum(1 for d, v in sleeps.items() if in_period(d) and v >= SLEEP_GOAL_MINUTES) * POINTS_PER_SLEEP_GOAL
    )
    weekdays = [0] * 7
    for d, _ in checks:
        if in_period(d):
            weekdays[d.weekday()] += 1

    # ── does your mood differ on days with / without something? (last 90 days) ──
    def compare(key: str, with_days: set, candidates: set | None = None) -> Correlation | None:
        logged = {d: v for d, v in moods.items() if long_start <= d <= end and (candidates is None or d in candidates)}
        yes = [v for d, v in logged.items() if d in with_days]
        no = [v for d, v in logged.items() if d not in with_days]
        if len(yes) < MIN_SAMPLES or len(no) < MIN_SAMPLES:
            return None
        return Correlation(key=key, n_with=len(yes), n_without=len(no), avg_with=_avg(yes), avg_without=_avg(no))

    found = [
        compare("sleep", {d for d, v in sleeps.items() if v >= SLEEP_GOAL_MINUTES}, set(sleeps)),
        compare("steps", {d for d, v in steps.items() if v >= STEP_GOAL}, set(steps)),
        compare("meditation", set(meditation)),
        compare("checkin", {d for d, _ in checks}),
    ]
    return ReportResponse(
        period=period, start=start, end=end, axes=axes,
        checkins=sum(1 for d, _ in checks if in_period(d)), active_days=len(active), days=days,
        points_earned=points, pomodoro_minutes=focus_minutes, meditation_minutes=calm_minutes,
        avg_steps=round(sum(p_steps) / len(p_steps)) if p_steps else None,
        avg_sleep_minutes=round(sum(p_sleep) / len(p_sleep)) if p_sleep else None,
        avg_mood=_avg(p_mood), prev_avg_mood=_avg(prev_mood),
        journal_entries=sum(1 for d in journal_days if in_period(d)),
        weekdays=weekdays, correlations=[c for c in found if c],
    )
