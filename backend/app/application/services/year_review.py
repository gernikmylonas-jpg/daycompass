"""The year in review: totals for one calendar year, computed from the user's own records."""
from collections import Counter, defaultdict
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.application.services.points import STEP_GOAL
from app.application.services.streaks import compute_streaks
from app.domain.models import (
    Badge, CheckIn, Habit, JournalEntry, MeditationSession, MoodLog, PomodoroSession, SleepLog, StepLog, UserBadge, WeightLog,
)


def build_year(db: Session, user_id: str, year: int) -> dict:
    start, end = date(year, 1, 1), date(year, 12, 31)

    rows = (
        db.query(CheckIn.check_date, Habit.name)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True), CheckIn.check_date.between(start, end))
        .all()
    )
    days = {d for d, _ in rows}
    by_month = [0] * 12
    habit_counts: Counter = Counter()
    for d, name in rows:
        by_month[d.month - 1] += 1
        habit_counts[name] += 1
    best_streak = compute_streaks(days, end)[1] if days else 0

    steps = [s for (s,) in db.query(StepLog.steps).filter(StepLog.user_id == user_id, StepLog.log_date.between(start, end))]
    sleeps = [m for (m,) in db.query(SleepLog.minutes).filter(SleepLog.user_id == user_id, SleepLog.log_date.between(start, end))]
    moods = [s for (s,) in db.query(MoodLog.score).filter(MoodLog.user_id == user_id, MoodLog.log_date.between(start, end))]
    weights = db.query(WeightLog).filter(WeightLog.user_id == user_id, WeightLog.log_date.between(start, end)).order_by(WeightLog.log_date).all()
    badges = (
        db.query(func.count(UserBadge.id))
        .filter(UserBadge.user_id == user_id, func.extract("year", UserBadge.awarded_at) == year).scalar() or 0
    )
    pomodoro_minutes = db.query(func.coalesce(func.sum(PomodoroSession.duration_minutes), 0)).filter(
        PomodoroSession.user_id == user_id, PomodoroSession.session_date.between(start, end)).scalar() or 0
    meditation_minutes = db.query(func.coalesce(func.sum(MeditationSession.duration_minutes), 0)).filter(
        MeditationSession.user_id == user_id, MeditationSession.session_date.between(start, end)).scalar() or 0

    best_month = max(range(12), key=lambda i: by_month[i]) + 1 if any(by_month) else None
    return {
        "year": year,
        "checkins": len(rows),
        "active_days": len(days),
        "best_streak": best_streak,
        "checkins_by_month": by_month,
        "best_month": best_month,
        "top_habits": [{"name": n, "count": c} for n, c in habit_counts.most_common(3)],
        "steps_total": sum(steps),
        "steps_days": len(steps),
        "steps_avg": round(sum(steps) / len(steps)) if steps else None,
        "step_goal_days": sum(1 for s in steps if s >= STEP_GOAL),
        "sleep_nights": len(sleeps),
        "sleep_avg_minutes": round(sum(sleeps) / len(sleeps)) if sleeps else None,
        "focus_minutes": int(pomodoro_minutes),
        "meditation_minutes": int(meditation_minutes),
        "journal_entries": db.query(func.count(JournalEntry.id)).filter(
            JournalEntry.user_id == user_id, JournalEntry.entry_date.between(start, end)).scalar() or 0,
        "mood_avg": round(sum(moods) / len(moods), 1) if moods else None,
        "mood_logs": len(moods),
        "weight_change_kg": round(weights[-1].kg - weights[0].kg, 1) if len(weights) >= 2 else None,
        "badges_earned": int(badges),
    }
