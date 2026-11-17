from datetime import date, timedelta
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.domain.models import User, Habit, CheckIn, PomodoroSession, GroupMember, StepLog, SleepLog
from app.application.services.points import POINTS_PER_CHECK_IN, POINTS_PER_POMODORO

WEEK_DAYS = 7


def _weekly_points(db: Session, user_ids: list) -> dict:
    since = date.today() - timedelta(days=WEEK_DAYS - 1)
    points = {uid: 0 for uid in user_ids}

    check_ins = (
        db.query(Habit.user_id, func.count(CheckIn.id))
        .join(CheckIn, CheckIn.habit_id == Habit.id)
        .filter(Habit.user_id.in_(user_ids), CheckIn.completed.is_(True), CheckIn.check_date >= since)
        .group_by(Habit.user_id)
    )
    for uid, count in check_ins:
        points[uid] += count * POINTS_PER_CHECK_IN

    pomodoros = (
        db.query(PomodoroSession.user_id, func.count(PomodoroSession.id))
        .filter(PomodoroSession.user_id.in_(user_ids), PomodoroSession.session_date >= since)
        .group_by(PomodoroSession.user_id)
    )
    for uid, count in pomodoros:
        points[uid] += count * POINTS_PER_POMODORO

    for model in (StepLog, SleepLog):
        awarded = (
            db.query(model.user_id, func.sum(model.points_awarded))
            .filter(model.user_id.in_(user_ids), model.log_date >= since)
            .group_by(model.user_id)
        )
        for uid, total in awarded:
            points[uid] += int(total or 0)

    return points


def group_leaderboard(db: Session, group_id, period: str = "all") -> list[tuple[int, User, int]]:
    """Returns (rank, user, points) ordered by points desc. Ties share the same rank."""
    users = (
        db.query(User)
        .join(GroupMember, GroupMember.user_id == User.id)
        .filter(GroupMember.group_id == group_id)
        .all()
    )
    if period == "week":
        weekly = _weekly_points(db, [u.id for u in users])
        scored = [(u, weekly[u.id]) for u in users]
    else:
        scored = [(u, u.total_points) for u in users]

    scored.sort(key=lambda item: (-item[1], item[0].name.lower()))

    result = []
    prev_points, rank = None, 0
    for index, (user, pts) in enumerate(scored, start=1):
        if pts != prev_points:
            rank, prev_points = index, pts
        result.append((rank, user, pts))
    return result
