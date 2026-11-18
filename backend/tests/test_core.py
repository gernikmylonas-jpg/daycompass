"""Behaviour that existed before the latest features: points, badges, groups, wellness, calendar, ..."""
from datetime import date, timedelta

TODAY = date.today()


def _habit(user, name="Run", category="body", frequency="daily"):
    return user.post("/api/habits", json={"name": name, "frequency": frequency, "category": category}).json()


def test_check_in_gives_points_once_a_day_and_a_badge(user):
    h = _habit(user)
    first = user.post(f"/api/habits/{h['id']}/check-in")
    assert first.status_code == 200
    assert [b["code"] for b in first.json()["new_badges"]] == ["first_checkin"]
    assert user.points() == 10
    assert user.post(f"/api/habits/{h['id']}/check-in").status_code == 409
    assert user.points() == 10


def test_habits_are_private(user, other):
    h = _habit(user)
    assert other.post(f"/api/habits/{h['id']}/check-in").status_code == 404
    assert other.delete(f"/api/habits/{h['id']}").status_code == 404
    assert other.get("/api/habits").json() == []


def test_profile_and_password(client, user):
    assert user.put("/api/auth/profile", json={"name": "  New  "}).json()["name"] == "New"
    assert user.put("/api/auth/profile", json={"name": " "}).status_code == 422
    assert user.put("/api/auth/profile", json={"email": "x" + user.email}).status_code == 403  # needs the password
    changed = user.put("/api/auth/profile", json={"email": "x" + user.email, "current_password": user.password})
    assert changed.json()["email"] == "x" + user.email
    assert user.put("/api/auth/password", json={"current_password": "bad", "new_password": "longenough"}).status_code == 403
    assert user.put("/api/auth/password", json={"current_password": user.password, "new_password": "short"}).status_code == 422
    assert user.put("/api/auth/password", json={"current_password": user.password, "new_password": "NewPass99"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "x" + user.email, "password": "NewPass99"}).status_code == 200
    assert client.post("/api/auth/login", json={"email": "x" + user.email, "password": user.password}).status_code == 401


def test_registration_requires_a_decent_password_and_a_unique_email(client, user):
    assert client.post("/api/auth/register", json={"name": "A", "email": "new@test.io", "password": "short"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "A", "email": user.email, "password": "longenough"}).status_code == 409


def test_steps_and_sleep_reward_goals_once_and_have_no_history_limit(user):
    long_ago = "2003-11-20"
    first = user.put("/api/wellness/steps", json={"steps": 9000, "log_date": long_ago}).json()
    assert first["points_awarded"] == 10 and "steps_first" in [b["code"] for b in first["new_badges"]]
    assert user.put("/api/wellness/steps", json={"steps": 12000, "log_date": long_ago}).json()["points_awarded"] == 0
    assert user.put("/api/wellness/sleep", json={"minutes": 450, "quality": 4, "log_date": long_ago}).json()["goal_reached"] is True
    assert user.put("/api/wellness/steps", json={"steps": 1, "log_date": "1999-12-31"}).status_code == 422
    assert user.put("/api/wellness/steps", json={"steps": 1, "log_date": str(TODAY + timedelta(days=1))}).status_code == 422
    for i in range(35):
        user.put("/api/wellness/steps", json={"steps": 1000 + i, "log_date": str(TODAY - timedelta(days=3 * i + 1))})
    page1 = user.get("/api/wellness/history?limit=20").json()
    assert page1["total"] == 36 and len(page1["days"]) == 20
    assert user.get("/api/wellness/history?limit=20&offset=20").json()["days"][-1]["date"] == long_ago
    sleep_days = user.get("/api/wellness/history?kind=sleep").json()
    assert sleep_days["total"] == 1 and sleep_days["days"][0]["sleep_minutes"] == 450  # only days that have sleep logged
    assert user.delete(f"/api/wellness/steps/{long_ago}").status_code == 200
    assert user.delete(f"/api/wellness/steps/{long_ago}").status_code == 404


def test_mood_scale_and_style_setting(user):
    assert user.put("/api/mood", json={"score": 0}).status_code == 422
    assert user.put("/api/mood", json={"score": 11}).status_code == 422
    assert user.put("/api/mood", json={"score": 7}).json()["date"] == str(TODAY)
    assert user.put("/api/mood", json={"score": 9, "note": "better"}).json()["score"] == 9  # same day: replaced
    summary = user.get("/api/mood").json()
    assert summary["today"] == 9 and summary["logged_total"] == 1
    base = {"theme": "classic", "mode": "light", "needle_cursor": True, "language": "en"}
    assert user.put("/api/settings", json={**base, "mood_style": "words"}).json()["mood_style"] == "words"
    assert user.put("/api/settings", json={**base, "mood_style": "pirate"}).status_code == 422
    assert user.get("/api/settings").json() == {
        **base, "mood_style": "words", "depth_3d": False, "lid_open": False, "brightness": 100, "calendar_prefs": None, "saved": True,
    }


def test_compass_look_settings(user):
    base = {"theme": "retro", "mode": "dark", "needle_cursor": True, "language": "en"}
    saved = user.put("/api/settings", json={**base, "depth_3d": True, "lid_open": True, "brightness": 130}).json()
    assert saved["depth_3d"] is True and saved["lid_open"] is True and saved["brightness"] == 130
    again = user.get("/api/settings").json()
    assert (again["depth_3d"], again["lid_open"], again["brightness"]) == (True, True, 130)
    assert user.put("/api/settings", json={**base, "brightness": 20}).status_code == 422
    assert user.put("/api/settings", json={**base, "brightness": 200}).status_code == 422


def test_meditation_gives_points_and_counts_in_the_breakdown(user):
    assert user.post("/api/meditation", json={"duration_minutes": 0}).status_code == 422
    r = user.post("/api/meditation", json={"duration_minutes": 10}).json()
    assert r["points_awarded"] == 5 and [b["code"] for b in r["new_badges"]] == ["meditation_first"]
    summary = user.get("/api/meditation/summary").json()
    assert summary["total_minutes"] == 10 and summary["current_streak"] == 1
    breakdown = user.get("/api/stats/points").json()
    assert breakdown["meditations"] == {"count": 1, "points": 5} and breakdown["other"] == 0


def test_calendar_events_repeat_yearly_and_are_private(user, other):
    e = user.post("/api/calendar/events", json={"title": "Mum", "event_date": "1990-03-14", "kind": "birthday", "repeat_yearly": True}).json()
    leap = user.post("/api/calendar/events", json={"title": "Leap", "event_date": "2000-02-29", "kind": "birthday", "repeat_yearly": True}).json()
    in_march_2085 = user.get("/api/calendar/events?start=2085-03-01&end=2085-03-31").json()
    assert [(x["title"], x["date"]) for x in in_march_2085] == [("Mum", "2085-03-14")]
    assert [x["date"] for x in user.get("/api/calendar/events?start=2026-02-01&end=2026-02-28").json()] == ["2026-02-28"]
    assert user.get("/api/calendar/events?start=1985-03-01&end=1985-03-31").json() == []  # before the birth year
    assert other.get("/api/calendar/events?start=2026-03-01&end=2026-03-31").json() == []
    assert other.delete(f"/api/calendar/events/{e['id']}").status_code == 404
    assert user.post("/api/calendar/events", json={"title": "x", "event_date": "1899-01-01"}).status_code == 422
    assert leap["id"]


def test_groups_leaderboard_and_ownership(user, other):
    g = user.post("/api/groups", json={"name": "Team"}).json()
    assert "group_create" in [b["code"] for b in g["new_badges"]]
    assert other.get(f"/api/groups/{g['id']}").status_code == 404  # not a member
    joined = other.post("/api/groups/join", json={"invite_code": g["invite_code"].lower()})
    assert joined.status_code == 200 and "group_join" in [b["code"] for b in joined.json()["new_badges"]]
    assert other.post("/api/groups/join", json={"invite_code": g["invite_code"]}).status_code == 409
    h = _habit(other)
    other.post(f"/api/habits/{h['id']}/check-in")
    board = user.get(f"/api/groups/{g['id']}").json()["leaderboard"]
    assert [(r["rank"], r["points"]) for r in board] == [(1, 10), (2, 0)]
    assert other.delete(f"/api/groups/{g['id']}").status_code == 403  # only the owner may delete
    assert user.delete(f"/api/groups/{g['id']}/members/me").status_code == 200
    assert other.get("/api/groups").json()[0]["is_owner"] is True  # ownership passed on


def test_journal_text_and_voice_are_private(user, other):
    audio = b"\x1aE\xdf\xa3" + b"opus" * 100
    text = user.post("/api/journal", data={"entry_date": str(TODAY), "content": "Good day", "mood": "good"})
    assert text.status_code == 200 and text.json()["has_audio"] is False
    voice = user.post("/api/journal", data={"entry_date": str(TODAY), "audio_seconds": "7"},
                      files={"audio": ("a.webm", audio, "audio/webm;codecs=opus")})
    assert voice.json()["has_audio"] is True and voice.json()["audio_seconds"] == 7
    assert user.get(f"/api/journal/{voice.json()['id']}/audio").content == audio
    assert other.get(f"/api/journal/{voice.json()['id']}/audio").status_code == 404
    assert other.get("/api/journal").json()["total"] == 0
    assert user.post("/api/journal", data={"entry_date": str(TODAY), "content": " "}).status_code == 422
    assert user.post("/api/journal", data={"entry_date": str(TODAY), "content": "x"},
                     files={"audio": ("a.exe", b"MZ", "application/x-msdownload")}).status_code == 422
