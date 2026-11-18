from datetime import date, timedelta

from app.application.services.streaks import compute_streaks, compute_weekly_streaks

TODAY = date(2026, 11, 18)  # a Wednesday


def d(offset):
    return TODAY + timedelta(days=offset)


def test_daily_streak_basics():
    assert compute_streaks([], TODAY) == (0, 0)
    assert compute_streaks([d(0)], TODAY) == (1, 1)
    assert compute_streaks([d(-1), d(-2), d(-3)], TODAY) == (3, 3)  # still alive: last check was yesterday
    assert compute_streaks([d(-2), d(-3)], TODAY) == (0, 2)         # a whole day missed


def test_rest_day_bridges_a_gap_without_adding_to_the_streak():
    assert compute_streaks([d(-3), d(-2), d(0)], TODAY) == (1, 2)          # gap on d(-1) breaks it
    assert compute_streaks([d(-3), d(-2), d(0)], TODAY, [d(-1)]) == (3, 3)  # rest day on d(-1) keeps it
    assert compute_streaks([d(-2), d(-1)], TODAY, [d(0)]) == (2, 2)         # resting today: alive, not counted
    assert compute_streaks([d(-5), d(-4)], TODAY, [d(-3), d(-2)]) == (0, 2)  # rest days cannot stretch forever


def test_weekly_streak_counts_weeks_that_met_the_target():
    monday = TODAY - timedelta(days=TODAY.weekday())
    two_weeks_ago = [monday - timedelta(days=14) + timedelta(days=i) for i in range(3)]
    last_week = [monday - timedelta(days=7) + timedelta(days=i) for i in range(3)]
    assert compute_weekly_streaks(two_weeks_ago + last_week, TODAY, 3) == (2, 2)
    this_week = [monday, monday + timedelta(days=1), monday + timedelta(days=2)]
    assert compute_weekly_streaks(last_week + this_week, TODAY, 3) == (2, 2)
    assert compute_weekly_streaks(last_week + this_week[:1], TODAY, 3) == (1, 1)  # running week never breaks it
    assert compute_weekly_streaks(two_weeks_ago, TODAY, 3) == (0, 1)               # last week missed


def test_weekly_habit_api(user):
    r = user.post("/api/habits", json={"name": "Gym", "frequency": "weekly:3", "category": "body"})
    assert r.status_code == 200 and r.json()["target_per_week"] == 3
    assert user.post("/api/habits", json={"name": "x", "frequency": "weekly:9", "category": "body"}).status_code == 422
    assert user.post("/api/habits", json={"name": "x", "frequency": "monthly", "category": "body"}).status_code == 422
    user.post(f"/api/habits/{r.json()['id']}/check-in")
    habit = user.get("/api/habits").json()[0]
    assert habit["week_count"] == 1 and habit["checked_in_today"] is True
    changed = user.put(f"/api/habits/{r.json()['id']}", json={"frequency": "daily"}).json()
    assert changed["target_per_week"] is None


def test_rest_days_keep_the_overall_streak_and_have_limits(user):
    h = user.post("/api/habits", json={"name": "Run", "frequency": "daily", "category": "body"}).json()
    user.post(f"/api/habits/{h['id']}/check-in")
    today = date.today()
    assert user.get("/api/stats/streak").json()["current"] == 1

    assert user.put(f"/api/rest-days/{today}").status_code == 200
    assert user.put(f"/api/rest-days/{today}").status_code == 200  # idempotent
    assert user.put(f"/api/rest-days/{today - timedelta(days=1)}").status_code == 200
    third = user.put(f"/api/rest-days/{today - timedelta(days=2)}")
    assert third.status_code == 422 and "Too many rest days" in third.json()["detail"]
    assert user.put(f"/api/rest-days/{today - timedelta(days=30)}").status_code == 422

    days = user.get(f"/api/rest-days?start={today - timedelta(days=7)}&end={today}").json()
    assert days == [str(today - timedelta(days=1)), str(today)]
    assert user.delete(f"/api/rest-days/{today}").status_code == 200
    assert user.delete(f"/api/rest-days/{today}").status_code == 404
