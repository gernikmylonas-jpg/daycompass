from collections import defaultdict
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.domain.models import Badge, UserBadge, User, Habit, CheckIn, PomodoroSession
from app.application.services.streaks import compute_streaks

CATALOG = [
    {"code": "first_checkin", "name": "Πρώτο βήμα", "description": "Το πρώτο σου check-in", "icon": "🌱"},
    {"code": "checkins_50", "name": "Σταθερός", "description": "50 check-ins συνολικά", "icon": "✅"},
    {"code": "checkins_100", "name": "Εκατοντάρης", "description": "100 check-ins συνολικά", "icon": "💯"},
    {"code": "streak_7", "name": "Εβδομάδα φωτιά", "description": "7 μέρες streak σε ένα habit", "icon": "🔥"},
    {"code": "streak_30", "name": "Μάστορας συνήθειας", "description": "30 μέρες streak σε ένα habit", "icon": "🏆"},
    {"code": "first_pomodoro", "name": "Εστίαση", "description": "Το πρώτο σου Pomodoro", "icon": "🍅"},
    {"code": "pomodoro_10", "name": "Παραγωγικός", "description": "10 Pomodoro συνολικά", "icon": "⏱️"},
    {"code": "points_500", "name": "Εξερευνητής", "description": "500 πόντοι συνολικά", "icon": "🧭"},
]


def seed_badges(db: Session) -> None:
    existing = {code for (code,) in db.query(Badge.code).all()}
    for item in CATALOG:
        if item["code"] not in existing:
            db.add(Badge(**item))
    db.commit()


def _stats(db: Session, user_id: str) -> dict:
    rows = (
        db.query(CheckIn.habit_id, CheckIn.check_date)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True))
        .all()
    )
    by_habit = defaultdict(list)
    for habit_id, check_date in rows:
        by_habit[habit_id].append(check_date)

    today = date.today()
    best_streak = max((compute_streaks(d, today)[1] for d in by_habit.values()), default=0)

    pomodoros = db.query(func.count(PomodoroSession.id)).filter(
        PomodoroSession.user_id == user_id
    ).scalar()
    user = db.query(User).filter(User.id == user_id).first()

    return {
        "checkins": len(rows),
        "best_streak": best_streak,
        "pomodoros": pomodoros or 0,
        "points": user.total_points if user else 0,
    }


RULES = {
    "first_checkin": lambda s: s["checkins"] >= 1,
    "checkins_50": lambda s: s["checkins"] >= 50,
    "checkins_100": lambda s: s["checkins"] >= 100,
    "streak_7": lambda s: s["best_streak"] >= 7,
    "streak_30": lambda s: s["best_streak"] >= 30,
    "first_pomodoro": lambda s: s["pomodoros"] >= 1,
    "pomodoro_10": lambda s: s["pomodoros"] >= 10,
    "points_500": lambda s: s["points"] >= 500,
}


def award_badges(db: Session, user_id: str) -> list[Badge]:
    db.flush()
    stats = _stats(db, user_id)

    owned = {
        badge_id
        for (badge_id,) in db.query(UserBadge.badge_id).filter(UserBadge.user_id == user_id)
    }
    awarded: list[Badge] = []
    for badge in db.query(Badge).all():
        rule = RULES.get(badge.code)
        if rule and badge.id not in owned and rule(stats):
            db.add(UserBadge(user_id=user_id, badge_id=badge.id))
            awarded.append(badge)
    return awarded
