from datetime import date, timedelta
from typing import Iterable


def compute_streaks(check_dates: Iterable[date], today: date, rest_days: Iterable[date] = ()) -> tuple[int, int]:
    """(current, best) streak in days. A rest day keeps a streak alive without adding to it."""
    checks = set(check_dates)
    if not checks:
        return 0, 0
    rest = set(rest_days) - checks
    days = sorted(checks | rest)

    best = run = 0
    previous = None
    for d in days:
        if previous is not None and d - previous != timedelta(days=1):
            run = 0
        if d in checks:
            run += 1
        best = max(best, run)
        previous = d

    # the streak is alive while the last day (check-in or rest) is today or yesterday
    current = run if (today - days[-1]).days <= 1 else 0
    return current, best


def week_start(d: date) -> date:
    return d - timedelta(days=d.weekday())  # Monday


def compute_weekly_streaks(check_dates: Iterable[date], today: date, target: int) -> tuple[int, int]:
    """(current, best) streak in weeks for a habit with a "target times per week" goal.
    The running week never breaks the streak: it only adds to it once the target is reached."""
    per_week: dict[date, int] = {}
    for d in set(check_dates):
        per_week[week_start(d)] = per_week.get(week_start(d), 0) + 1
    met = {w for w, n in per_week.items() if n >= target}
    if not met:
        return 0, 0

    best = run = 0
    week = min(met)
    this_week = week_start(today)
    while week <= this_week:
        run = run + 1 if week in met else 0
        best = max(best, run)
        week += timedelta(days=7)

    # `run` now ends at the running week; if that week is not done yet, look at the one before
    if this_week in met:
        current = run
    else:
        current, w = 0, this_week - timedelta(days=7)
        while w in met:
            current += 1
            w -= timedelta(days=7)
    return current, best
