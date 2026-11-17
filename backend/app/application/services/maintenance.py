import logging
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.domain.models import User, Habit, CheckIn, PomodoroSession, StepLog, SleepLog, MeditationSession
from app.application.services.badges import award_badges
from app.application.services.points import (
    POINTS_PER_CHECK_IN, POINTS_PER_POMODORO, POINTS_PER_MEDITATION,
    STEP_GOAL, SLEEP_GOAL_MINUTES, POINTS_PER_STEP_GOAL, POINTS_PER_SLEEP_GOAL,
)

logger = logging.getLogger(__name__)


def backfill_goal_points(db: Session) -> int:
    """Grants goal points for logs that reached the goal but were never rewarded (e.g. a
    crash between the log and the award). Idempotent: only touches rows with points_awarded=0."""
    granted = 0
    for model, goal_ok, points in (
        (StepLog, StepLog.steps >= STEP_GOAL, POINTS_PER_STEP_GOAL),
        (SleepLog, SleepLog.minutes >= SLEEP_GOAL_MINUTES, POINTS_PER_SLEEP_GOAL),
    ):
        for log in db.query(model).filter(goal_ok, model.points_awarded == 0).all():
            log.points_awarded = points
            db.query(User).filter(User.id == log.user_id).update(
                {User.total_points: User.total_points + points}
            )
            granted += points
    db.commit()
    return granted


def award_missing_badges(db: Session) -> int:
    """Re-evaluates the badge rules (streaks, counts, points) for every user. Idempotent."""
    count = 0
    for (user_id,) in db.query(User.id).all():
        count += len(award_badges(db, str(user_id)))
        db.commit()
    return count


def points_drift(db: Session) -> list[dict]:
    """Compares each user's stored total_points with what the activity history would give.
    Report only: points legitimately survive deleted habits, so we never auto-correct."""
    check_ins = dict(
        db.query(Habit.user_id, func.count(CheckIn.id))
        .join(CheckIn, CheckIn.habit_id == Habit.id)
        .filter(CheckIn.completed.is_(True))
        .group_by(Habit.user_id)
        .all()
    )
    pomodoros = dict(
        db.query(PomodoroSession.user_id, func.count(PomodoroSession.id))
        .group_by(PomodoroSession.user_id)
        .all()
    )
    meditations = dict(
        db.query(MeditationSession.user_id, func.count(MeditationSession.id))
        .group_by(MeditationSession.user_id)
        .all()
    )
    steps = dict(db.query(StepLog.user_id, func.sum(StepLog.points_awarded)).group_by(StepLog.user_id).all())
    sleep = dict(db.query(SleepLog.user_id, func.sum(SleepLog.points_awarded)).group_by(SleepLog.user_id).all())

    drift = []
    for user in db.query(User).all():
        expected = (
            check_ins.get(user.id, 0) * POINTS_PER_CHECK_IN
            + pomodoros.get(user.id, 0) * POINTS_PER_POMODORO
            + meditations.get(user.id, 0) * POINTS_PER_MEDITATION
            + int(steps.get(user.id) or 0)
            + int(sleep.get(user.id) or 0)
        )
        if expected != user.total_points:
            drift.append({"user_id": str(user.id), "stored": user.total_points, "expected": expected})
    return drift


def nightly_recalculation(db: Session) -> dict:
    granted = backfill_goal_points(db)
    badges = award_missing_badges(db)
    drift = points_drift(db)
    if drift:
        logger.warning("points drift for %s user(s): %s", len(drift), drift[:10])
    result = {"goal_points_granted": granted, "badges_awarded": badges, "points_drift_users": len(drift)}
    logger.info("nightly recalculation: %s", result)
    return result
