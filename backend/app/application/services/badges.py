from collections import Counter, defaultdict
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.domain.models import (
    Badge, UserBadge, User, Habit, CheckIn, PomodoroSession, StepLog, SleepLog, JournalEntry, JournalAudio,
    MoodLog, MeditationSession, CalendarEvent, Group, GroupMember,
)
from app.application.services.streaks import compute_streaks
from app.application.services.leaderboard import group_leaderboard

# (code, name, description, fallback emoji). The app shows translated names/texts and its own
# artwork for every code; the strings here are only the fallback. The first eight keep their
# original (Greek) texts because they are already stored in existing databases.
CATALOG = [
    # ── original badges ──
    {"code": "first_checkin", "name": "Πρώτο βήμα", "description": "Το πρώτο σου check-in", "icon": "🌱"},
    {"code": "checkins_50", "name": "Σταθερός", "description": "50 check-ins συνολικά", "icon": "✅"},
    {"code": "checkins_100", "name": "Εκατοντάρης", "description": "100 check-ins συνολικά", "icon": "💯"},
    {"code": "streak_7", "name": "Εβδομάδα φωτιά", "description": "7 μέρες streak σε ένα habit", "icon": "🔥"},
    {"code": "streak_30", "name": "Μάστορας συνήθειας", "description": "30 μέρες streak σε ένα habit", "icon": "🏆"},
    {"code": "first_pomodoro", "name": "Εστίαση", "description": "Το πρώτο σου Pomodoro", "icon": "🍅"},
    {"code": "pomodoro_10", "name": "Παραγωγικός", "description": "10 Pomodoro συνολικά", "icon": "⏱️"},
    {"code": "points_500", "name": "Εξερευνητής", "description": "500 πόντοι συνολικά", "icon": "🧭"},
]

_NEW = [
    # general: check-ins, points, daily streak
    ("checkins_250", "Quarter Thousand", "250 check-ins in total", "🎯"),
    ("checkins_500", "Five Hundred", "500 check-ins in total", "🏅"),
    ("checkins_1000", "Thousand Club", "1000 check-ins in total", "👑"),
    ("points_100", "First Hundred", "100 points in total", "⭐"),
    ("points_1000", "Thousand Points", "1000 points in total", "🌟"),
    ("points_2500", "Constellation", "2500 points in total", "✨"),
    ("points_5000", "Supernova", "5000 points in total", "💫"),
    ("daily_3", "Warming Up", "3 days in a row with a check-in", "🕯️"),
    ("daily_14", "Fortnight", "14 days in a row with a check-in", "🔥"),
    ("daily_60", "Two Months Strong", "60 days in a row with a check-in", "🌓"),
    ("daily_100", "Century Streak", "100 days in a row with a check-in", "💎"),
    ("daily_365", "Full Orbit", "365 days in a row with a check-in", "🪐"),
    ("perfect_day", "Clean Sweep", "Check in every habit on the same day (with 3 or more habits)", "🧹"),
    ("habit_collector", "Collector", "Have 8 habits", "🗂️"),
    ("all_four", "Four Winds", "Check in at least once in North, East, South and West", "🧭"),
    # north: body and steps
    ("body_25", "Body Builder", "25 check-ins in North (body)", "💪"),
    ("steps_first", "First Steps", "Reach your step goal for the first time", "👟"),
    ("steps_7", "Walker", "Reach your step goal 7 times", "🚶"),
    ("steps_30", "Wanderer", "Reach your step goal 30 times", "🥾"),
    ("steps_20k", "Trailblazer", "Log 20,000 steps in a single day", "🏔️"),
    # north-east: sleep
    ("sleep_first", "Good Night", "Reach your sleep goal for the first time", "😴"),
    ("sleep_7", "Rested", "Reach your sleep goal 7 times", "🛌"),
    ("sleep_30", "Dreamer", "Reach your sleep goal 30 times", "🌙"),
    ("sleep_logged_14", "Night Notes", "Log 14 nights of sleep", "📝"),
    # east: schedule
    ("schedule_25", "Routine Keeper", "25 check-ins in East (schedule)", "📅"),
    # south: mind, mood, meditation, journal
    ("mind_25", "Calm Mind", "25 check-ins in South (mind)", "🧘"),
    ("mood_first", "How Am I?", "Log your mood for the first time", "🙂"),
    ("mood_7", "Mood Mapper", "Log your mood on 7 days", "🗺️"),
    ("mood_30", "Emotional Compass", "Log your mood on 30 days", "🧭"),
    ("meditation_first", "Still Mind", "Complete your first meditation", "🪷"),
    ("meditation_10", "Regular Breath", "Complete 10 meditations", "🌬️"),
    ("meditation_30", "Zen Apprentice", "Complete 30 meditations", "☯️"),
    ("meditation_100min", "Hundred Minutes", "Meditate for 100 minutes in total", "⏳"),
    ("journal_first", "Dear Diary", "Write your first journal entry", "📓"),
    ("journal_10", "Storyteller", "Write 10 journal entries", "📖"),
    ("journal_30", "Chronicler", "Write 30 journal entries", "📚"),
    ("journal_voice", "Voice of the Day", "Record your first voice entry", "🎙️"),
    # south-west: pomodoro
    ("pomodoro_50", "Focus Machine", "Complete 50 Pomodoros", "⚙️"),
    ("pomodoro_100", "Deep Focus", "Complete 100 Pomodoros", "🎯"),
    ("focus_600", "Ten Hours", "Focus for 10 hours in total", "⌛"),
    # west: work
    ("work_25", "Hard Worker", "25 check-ins in West (work & study)", "💼"),
    # north-west: groups
    ("group_join", "Team Player", "Join a group", "🤝"),
    ("group_create", "Founder", "Create a group", "🚩"),
    ("group_champion", "Champion", "Be first on the leaderboard of a group with 2 or more members", "🏆"),
    # south-east: calendar
    ("notes_first", "Planner", "Write your first calendar note", "🗓️"),
    ("notes_10", "Organizer", "Write 10 calendar notes", "📌"),
    ("birthday_first", "Never Forget", "Add a birthday to the calendar", "🎂"),
]
CATALOG += [{"code": c, "name": n, "description": d, "icon": i} for c, n, d, i in _NEW]


def seed_badges(db: Session) -> None:
    existing = {code for (code,) in db.query(Badge.code).all()}
    for item in CATALOG:
        if item["code"] not in existing:
            db.add(Badge(**item))
    db.commit()


def _count(db: Session, column, *filters) -> int:
    return db.query(func.count(column)).filter(*filters).scalar() or 0


def _stats(db: Session, user_id: str) -> dict:
    today = date.today()
    rows = (
        db.query(CheckIn.habit_id, CheckIn.check_date, Habit.category)
        .join(Habit, Habit.id == CheckIn.habit_id)
        .filter(Habit.user_id == user_id, CheckIn.completed.is_(True))
        .all()
    )
    by_habit = defaultdict(list)
    per_day = defaultdict(set)
    categories: Counter = Counter()
    for habit_id, check_date, category in rows:
        by_habit[habit_id].append(check_date)
        per_day[check_date].add(habit_id)
        categories[category.value] += 1

    habits_total = _count(db, Habit.id, Habit.user_id == user_id)
    best_habit_streak = max((compute_streaks(d, today)[1] for d in by_habit.values()), default=0)
    best_daily_streak = compute_streaks(per_day.keys(), today)[1]

    steps_max = db.query(func.max(StepLog.steps)).filter(StepLog.user_id == user_id).scalar() or 0
    user = db.query(User).filter(User.id == user_id).first()

    champion = False
    for (group_id,) in db.query(GroupMember.group_id).filter(GroupMember.user_id == user_id):
        board = group_leaderboard(db, group_id)
        if len(board) >= 2 and any(rank == 1 and str(u.id) == str(user_id) for rank, u, _ in board):
            champion = True
            break

    return {
        "checkins": len(rows),
        "best_streak": best_habit_streak,
        "daily_best": best_daily_streak,
        "cat_body": categories["body"],
        "cat_mind": categories["mind"],
        "cat_work": categories["work"],
        "cat_schedule": categories["schedule"],
        "habits_total": habits_total,
        "perfect_day": habits_total >= 3 and any(len(s) >= habits_total for s in per_day.values()),
        "pomodoros": _count(db, PomodoroSession.id, PomodoroSession.user_id == user_id),
        "focus_minutes": db.query(func.coalesce(func.sum(PomodoroSession.duration_minutes), 0))
        .filter(PomodoroSession.user_id == user_id).scalar() or 0,
        "steps_days": _count(db, StepLog.id, StepLog.user_id == user_id, StepLog.points_awarded > 0),
        "steps_max": steps_max,
        "sleep_days": _count(db, SleepLog.id, SleepLog.user_id == user_id, SleepLog.points_awarded > 0),
        "sleep_logs": _count(db, SleepLog.id, SleepLog.user_id == user_id),
        "journal": _count(db, JournalEntry.id, JournalEntry.user_id == user_id),
        "journal_voice": db.query(func.count(JournalAudio.entry_id))
        .join(JournalEntry, JournalEntry.id == JournalAudio.entry_id)
        .filter(JournalEntry.user_id == user_id).scalar() or 0,
        "mood_logs": _count(db, MoodLog.id, MoodLog.user_id == user_id),
        "meditations": _count(db, MeditationSession.id, MeditationSession.user_id == user_id),
        "meditation_minutes": db.query(func.coalesce(func.sum(MeditationSession.duration_minutes), 0))
        .filter(MeditationSession.user_id == user_id).scalar() or 0,
        "events": _count(db, CalendarEvent.id, CalendarEvent.user_id == user_id),
        "birthdays": _count(db, CalendarEvent.id, CalendarEvent.user_id == user_id, CalendarEvent.kind == "birthday"),
        "groups_joined": _count(db, GroupMember.id, GroupMember.user_id == user_id),
        "groups_owned": _count(db, Group.id, Group.owner_id == user_id),
        "champion": champion,
        "points": user.total_points if user else 0,
    }


def _at_least(key: str, n: int):
    return lambda s: s[key] >= n


RULES = {
    # original
    "first_checkin": _at_least("checkins", 1),
    "checkins_50": _at_least("checkins", 50),
    "checkins_100": _at_least("checkins", 100),
    "streak_7": _at_least("best_streak", 7),
    "streak_30": _at_least("best_streak", 30),
    "first_pomodoro": _at_least("pomodoros", 1),
    "pomodoro_10": _at_least("pomodoros", 10),
    "points_500": _at_least("points", 500),
    # general
    "checkins_250": _at_least("checkins", 250),
    "checkins_500": _at_least("checkins", 500),
    "checkins_1000": _at_least("checkins", 1000),
    "points_100": _at_least("points", 100),
    "points_1000": _at_least("points", 1000),
    "points_2500": _at_least("points", 2500),
    "points_5000": _at_least("points", 5000),
    "daily_3": _at_least("daily_best", 3),
    "daily_14": _at_least("daily_best", 14),
    "daily_60": _at_least("daily_best", 60),
    "daily_100": _at_least("daily_best", 100),
    "daily_365": _at_least("daily_best", 365),
    "perfect_day": lambda s: s["perfect_day"],
    "habit_collector": _at_least("habits_total", 8),
    "all_four": lambda s: min(s["cat_body"], s["cat_mind"], s["cat_work"], s["cat_schedule"]) >= 1,
    # north
    "body_25": _at_least("cat_body", 25),
    "steps_first": _at_least("steps_days", 1),
    "steps_7": _at_least("steps_days", 7),
    "steps_30": _at_least("steps_days", 30),
    "steps_20k": _at_least("steps_max", 20000),
    # north-east
    "sleep_first": _at_least("sleep_days", 1),
    "sleep_7": _at_least("sleep_days", 7),
    "sleep_30": _at_least("sleep_days", 30),
    "sleep_logged_14": _at_least("sleep_logs", 14),
    # east, west
    "schedule_25": _at_least("cat_schedule", 25),
    "work_25": _at_least("cat_work", 25),
    # south
    "mind_25": _at_least("cat_mind", 25),
    "mood_first": _at_least("mood_logs", 1),
    "mood_7": _at_least("mood_logs", 7),
    "mood_30": _at_least("mood_logs", 30),
    "meditation_first": _at_least("meditations", 1),
    "meditation_10": _at_least("meditations", 10),
    "meditation_30": _at_least("meditations", 30),
    "meditation_100min": _at_least("meditation_minutes", 100),
    "journal_first": _at_least("journal", 1),
    "journal_10": _at_least("journal", 10),
    "journal_30": _at_least("journal", 30),
    "journal_voice": _at_least("journal_voice", 1),
    # south-west
    "pomodoro_50": _at_least("pomodoros", 50),
    "pomodoro_100": _at_least("pomodoros", 100),
    "focus_600": _at_least("focus_minutes", 600),
    # north-west
    "group_join": _at_least("groups_joined", 1),
    "group_create": _at_least("groups_owned", 1),
    "group_champion": lambda s: s["champion"],
    # south-east
    "notes_first": _at_least("events", 1),
    "notes_10": _at_least("events", 10),
    "birthday_first": _at_least("birthdays", 1),
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
