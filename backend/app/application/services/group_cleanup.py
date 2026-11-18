from sqlalchemy.orm import Session
from app.domain.models import Cheer, GroupHabit, GroupHabitCheck


def drop_group_extras(db: Session, group_id) -> None:
    """Shared habits, their check-ins and the cheers of a group that is going away."""
    habit_ids = [h for (h,) in db.query(GroupHabit.id).filter(GroupHabit.group_id == group_id)]
    if habit_ids:
        db.query(GroupHabitCheck).filter(GroupHabitCheck.habit_id.in_(habit_ids)).delete(synchronize_session=False)
    db.query(GroupHabit).filter(GroupHabit.group_id == group_id).delete(synchronize_session=False)
    db.query(Cheer).filter(Cheer.group_id == group_id).delete(synchronize_session=False)
