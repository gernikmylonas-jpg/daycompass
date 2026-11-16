from datetime import date, timedelta
from typing import Iterable


def compute_streaks(check_dates: Iterable[date], today: date) -> tuple[int, int]:
    days = sorted(set(check_dates))
    if not days:
        return 0, 0

    best = 1
    run = 1
    for prev, cur in zip(days, days[1:]):
        run = run + 1 if cur - prev == timedelta(days=1) else 1
        best = max(best, run)

    last = days[-1]
    if (today - last).days > 1:
        return 0, best

    current = 1
    for i in range(len(days) - 1, 0, -1):
        if days[i] - days[i - 1] == timedelta(days=1):
            current += 1
        else:
            break
    return current, best
