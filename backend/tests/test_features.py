"""Challenges, the compass report, account export/delete, the journal lock and e-mails."""
from datetime import date, timedelta

from app.application.services import event_mail
from app.domain.models import JournalAudio, JournalEntry, User

TODAY = date.today()


def _habit(user, name, category="body"):
    return user.post("/api/habits", json={"name": name, "frequency": "daily", "category": category}).json()


# ── challenges ───────────────────────────────────────────────────────────

def test_group_challenge_progress_and_permissions(user, other, client):
    from tests.conftest import Account
    outsider = Account(client, "Outsider")
    g = user.post("/api/groups", json={"name": "Squad"}).json()
    other.post("/api/groups/join", json={"invite_code": g["invite_code"]})

    body = {"title": "Two check-ins", "metric": "checkins", "target": 2, "start_date": str(TODAY), "end_date": str(TODAY + timedelta(days=6))}
    assert other.post(f"/api/groups/{g['id']}/challenges", json=body).status_code == 403   # members cannot create
    assert outsider.get(f"/api/groups/{g['id']}/challenges").status_code == 404
    assert user.post(f"/api/groups/{g['id']}/challenges", json={**body, "metric": "bogus"}).status_code == 422
    assert user.post(f"/api/groups/{g['id']}/challenges", json={**body, "end_date": str(TODAY - timedelta(days=1))}).status_code == 422
    assert user.post(f"/api/groups/{g['id']}/challenges", json={**body, "target": 0}).status_code == 422
    created = user.post(f"/api/groups/{g['id']}/challenges", json=body)
    assert created.status_code == 200 and created.json()["status"] == "active"

    for name in ("A", "B"):
        other.post(f"/api/habits/{_habit(other, name)['id']}/check-in")
    listed = other.get(f"/api/groups/{g['id']}/challenges").json()[0]
    assert listed["completed_count"] == 1
    assert [(m["name"], m["progress"], m["done"]) for m in listed["members"]] == [("Other", 2, True), ("Tester", 0, False)]
    assert "challenge_first" in [b["code"] for b in other.get("/api/badges").json() if b["earned"]]

    assert other.delete(f"/api/groups/{g['id']}/challenges/{listed['id']}").status_code == 403
    assert user.delete(f"/api/groups/{g['id']}/challenges/{listed['id']}").status_code == 200
    assert user.get(f"/api/groups/{g['id']}/challenges").json() == []


def test_challenge_metrics_count_the_right_things(user):
    g = user.post("/api/groups", json={"name": "Solo"}).json()
    window = {"start_date": str(TODAY - timedelta(days=2)), "end_date": str(TODAY)}
    user.put("/api/wellness/steps", json={"steps": 4000})
    user.put("/api/wellness/steps", json={"steps": 6000, "log_date": str(TODAY - timedelta(days=1))})
    user.put("/api/wellness/steps", json={"steps": 99999, "log_date": str(TODAY - timedelta(days=30))})  # outside the window
    user.post("/api/meditation", json={"duration_minutes": 12})
    for metric, target, expected in (("steps", 20000, 10000), ("meditation_minutes", 10, 12), ("sleep_nights", 1, 0)):
        c = user.post(f"/api/groups/{g['id']}/challenges", json={"title": metric, "metric": metric, "target": target, **window}).json()
        assert c["members"][0]["progress"] == expected, metric


# ── compass report ───────────────────────────────────────────────────────

def test_report_axes_and_mood_correlations(user):
    h = _habit(user, "Run", "body")
    user.post(f"/api/habits/{h['id']}/check-in")
    for i in range(12):
        day = str(TODAY - timedelta(days=i))
        well_rested = i < 6
        user.put("/api/wellness/sleep", json={"minutes": 480 if well_rested else 300, "log_date": day})
        user.put("/api/mood", json={"score": 9 if well_rested else 4, "log_date": day})
    report = user.get("/api/insights/report?period=week").json()
    assert report["days"] == 7 and report["checkins"] == 1
    assert report["axes"]["body"] is not None and report["axes"]["mind"] is None  # no mind habits: no data
    assert report["axes"]["sleep"] is not None
    sleep = next(c for c in report["correlations"] if c["key"] == "sleep")
    assert (sleep["avg_with"], sleep["avg_without"]) == (9.0, 4.0)
    assert sleep["n_with"] == 6 and sleep["n_without"] == 6
    assert user.get("/api/insights/report?period=month").json()["days"] == 30
    assert user.get("/api/insights/report?period=year").status_code == 422


def test_report_without_data_is_empty_not_an_error(user):
    report = user.get("/api/insights/report").json()
    assert report["checkins"] == 0 and report["correlations"] == [] and report["avg_mood"] is None
    assert all(v is None for v in report["axes"].values())


# ── account ──────────────────────────────────────────────────────────────

def test_export_contains_the_users_data(user):
    h = _habit(user, "Read", "work")
    user.post(f"/api/habits/{h['id']}/check-in")
    user.put("/api/mood", json={"score": 8})
    user.post("/api/journal", data={"entry_date": str(TODAY), "content": "Dear diary"})
    r = user.get("/api/account/export")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    data = r.json()
    assert data["profile"]["email"] == user.email
    assert data["habits"][0]["check_ins"] == [str(TODAY)]
    assert data["mood"][0]["score"] == 8 and data["journal"][0]["content"] == "Dear diary"


def test_deleting_an_account_removes_everything_and_hands_over_groups(client, user, other):
    g = user.post("/api/groups", json={"name": "Keep me"}).json()
    other.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    solo = user.post("/api/groups", json={"name": "Only me"}).json()
    user.post(f"/api/habits/{_habit(user, 'Run')['id']}/check-in")
    user.post("/api/journal", data={"entry_date": str(TODAY), "audio_seconds": "3"},
              files={"audio": ("a.webm", b"x" * 50, "audio/webm")})

    assert user.delete("/api/account", json={"password": "wrong"}).status_code == 403
    assert user.delete("/api/account", json={"password": user.password}).status_code == 200
    assert client.post("/api/auth/login", json={"email": user.email, "password": user.password}).status_code == 401
    assert user.get("/api/auth/me").status_code == 404  # the old token no longer matches anyone

    groups = other.get("/api/groups").json()
    assert [(x["name"], x["is_owner"]) for x in groups] == [("Keep me", True)]
    assert other.get(f"/api/groups/{solo['id']}").status_code == 404  # deleted with its only member


def test_deleting_leaves_no_orphans(db, user):
    user.post("/api/journal", data={"entry_date": str(TODAY), "audio_seconds": "1"},
              files={"audio": ("a.webm", b"x" * 20, "audio/webm")})
    user.delete("/api/account", json={"password": user.password})
    assert db.query(User).filter(User.email == user.email).count() == 0
    assert db.query(JournalEntry).filter(JournalEntry.user_id == user.id).count() == 0
    assert db.query(JournalAudio).count() == db.query(JournalAudio).join(JournalEntry, JournalEntry.id == JournalAudio.entry_id).count()


# ── journal lock ─────────────────────────────────────────────────────────

def test_journal_lock_encrypts_at_rest_and_needs_the_pin(db, user, other):
    audio = b"\x1aE\xdf\xa3" + b"secret-voice" * 20
    user.post("/api/journal", data={"entry_date": str(TODAY), "content": "before the lock"})
    assert user.get("/api/journal/lock").json() == {"enabled": False}
    assert user.post("/api/journal/lock", json={"pin": "12"}).status_code == 422
    assert user.post("/api/journal/lock", json={"pin": "4821"}).status_code == 200
    assert user.post("/api/journal/lock", json={"pin": "4821"}).status_code == 409

    pin = {"X-Journal-Pin": "4821"}
    # at rest: the stored text is ciphertext, not the words
    stored = db.query(JournalEntry).filter(JournalEntry.user_id == user.id).first()
    assert "before the lock" not in stored.content and stored.encrypted is True

    assert user.get("/api/journal").status_code == 423                                   # locked
    assert user.get("/api/journal", headers={"X-Journal-Pin": "0000"}).status_code == 403  # wrong PIN
    assert user.get("/api/journal", headers=pin).json()["entries"][0]["content"] == "before the lock"

    voice = user.post("/api/journal", headers=pin, data={"entry_date": str(TODAY), "content": "new secret", "audio_seconds": "5"},
                      files={"audio": ("a.webm", audio, "audio/webm")}).json()
    db.expire_all()
    assert db.query(JournalAudio).filter(JournalAudio.entry_id == voice["id"]).first().data != audio  # recording is encrypted too
    assert user.get(f"/api/journal/{voice['id']}/audio", headers=pin).content == audio
    assert user.get(f"/api/journal/{voice['id']}/audio").status_code == 423
    assert user.delete(f"/api/journal/{voice['id']}").status_code == 423
    assert other.get("/api/journal").status_code == 200  # nobody else is affected
    assert user.get("/api/account/export").json()["journal"] == {"locked": True, "note": "Send the journal PIN (X-Journal-Pin) to include the journal."}
    assert len(user.get("/api/account/export", headers=pin).json()["journal"]) == 2

    # change the PIN, then remove the lock: everything is readable again, nothing lost
    assert user.put("/api/journal/lock", json={"pin": "0000", "new_pin": "9999"}).status_code == 403
    assert user.put("/api/journal/lock", json={"pin": "4821", "new_pin": "9999"}).status_code == 200
    assert user.get("/api/journal", headers=pin).status_code == 403
    assert user.post("/api/journal/lock/disable", json={"pin": "9999"}).status_code == 200
    entries = user.get("/api/journal").json()["entries"]
    assert sorted(e["content"] for e in entries) == ["before the lock", "new secret"]
    assert user.get(f"/api/journal/{voice['id']}/audio").content == audio
    db.expire_all()
    assert db.query(JournalEntry).filter(JournalEntry.user_id == user.id).first().encrypted is False


# ── e-mails ──────────────────────────────────────────────────────────────

def test_calendar_notes_email_is_sent_once_a_day_to_opted_in_users(db, user, other, monkeypatch):
    sent = []
    monkeypatch.setattr(event_mail, "send_email", lambda to, subject, body: sent.append((to, subject, body)) or True)
    user.put("/api/reminders", json={"enabled": False, "events_enabled": True, "language": "fr"})
    user.post("/api/calendar/events", json={"title": "Anniversaire de Léa", "event_date": f"{TODAY.year - 30}-{TODAY.month:02d}-{TODAY.day:02d}",
                                            "kind": "birthday", "repeat_yearly": True})
    other.post("/api/calendar/events", json={"title": "Not opted in", "event_date": str(TODAY)})  # reminders are off for them

    first = event_mail.send_event_mails(db, TODAY)
    mine = [m for m in sent if m[0] == user.email]
    assert len(mine) == 1 and "Anniversaire de Léa (30)" in mine[0][2] and "aujourd'hui" in mine[0][1]
    assert not [m for m in sent if m[0] == other.email]
    assert first["sent"] >= 1
    event_mail.send_event_mails(db, TODAY)  # running again sends nothing new
    assert len([m for m in sent if m[0] == user.email]) == 1


def test_weekly_repeat_events(user):
    e = user.post("/api/calendar/events", json={"title": "Gym", "event_date": "2026-03-02", "repeat_weekly": True}).json()
    assert e["repeat_weekly"] is True
    both = user.post("/api/calendar/events", json={"title": "x", "event_date": "2026-03-02", "repeat_weekly": True, "repeat_yearly": True})
    assert both.status_code == 422
    days = [x["date"] for x in user.get("/api/calendar/events", params={"start": "2026-03-01", "end": "2026-03-31"}).json()]
    assert days == ["2026-03-02", "2026-03-09", "2026-03-16", "2026-03-23", "2026-03-30"]
    before = user.get("/api/calendar/events", params={"start": "2026-02-01", "end": "2026-02-28"}).json()
    assert before == []  # not before its first day
    mid = [x["date"] for x in user.get("/api/calendar/events", params={"start": "2026-03-10", "end": "2026-03-17"}).json()]
    assert mid == ["2026-03-16"]


def test_public_holidays_and_calendar_prefs(user):
    assert "GR" in user.get("/api/calendars/countries").json()
    gr = user.get("/api/calendars/holidays", params={"country": "gr", "year": 2026, "lang": "en"}).json()
    dates = {h["date"] for h in gr}
    assert "2026-03-25" in dates and "2026-10-28" in dates and "2026-04-10" in dates and "2026-04-13" in dates  # Orthodox Good Friday and Easter Monday 2026
    assert user.get("/api/calendars/holidays", params={"country": "ZZ", "year": 2026}).status_code == 422
    assert user.get("/api/calendars/holidays", params={"country": "GR", "year": 1800}).status_code == 422
    base = {"theme": "classic", "mode": "light", "needle_cursor": True, "language": "en"}
    prefs = '{"nameDays":true}'
    assert user.put("/api/settings", json={**base, "calendar_prefs": prefs}).json()["calendar_prefs"] == prefs
    assert user.get("/api/settings").json()["calendar_prefs"] == prefs
    assert user.put("/api/settings", json={**base, "calendar_prefs": "x" * 2001}).status_code == 422


def test_steps_series_and_goal_streak(user):
    from datetime import date, timedelta
    today = date.today()
    for i, steps in enumerate([9000, 8500, 3000]):  # today=9000, yesterday=8500, two days ago=3000
        user.put("/api/wellness/steps", json={"steps": steps, "log_date": str(today - timedelta(days=i))})
    week = user.get("/api/wellness/steps/series", params={"period": "week"}).json()
    assert len(week["buckets"]) == 7 and week["buckets"][-1]["steps"] == 9000 and week["today"] == 9000
    assert week["goal_streak"] == 2 and week["goal"] == 8000
    assert len(user.get("/api/wellness/steps/series", params={"period": "month"}).json()["buckets"]) == 30
    year = user.get("/api/wellness/steps/series", params={"period": "year"}).json()
    assert len(year["buckets"]) == 12 and year["buckets"][-1]["days_logged"] >= 1
    assert user.get("/api/wellness/steps/series", params={"period": "decade"}).status_code == 422


def test_weight_trend_goal_and_privacy(user, other):
    from datetime import date, timedelta
    today = date.today()
    assert user.put(f"/api/weight/{today}", json={"kg": 5}).status_code == 422
    assert user.put(f"/api/weight/{today + timedelta(days=3)}", json={"kg": 70}).status_code == 422
    for i, kg in enumerate([80.0, 79.6, 79.2, 79.0, 78.6, 78.4, 78.0, 77.5, 77.0, 76.0]):  # one a day, oldest first
        user.put(f"/api/weight/{today - timedelta(days=9 - i)}", json={"kg": kg})
    user.put("/api/weight/profile", json={"height_cm": 180, "goal_kg": 72.5, "unit": "lb", "show_bmi": True})
    data = user.get("/api/weight").json()
    s = data["stats"]
    assert s["latest"]["kg"] == 76.0 and len(data["entries"]) == 10
    assert s["trend"] == round((78.4 + 78.0 + 77.5 + 77.0 + 76.0 + 78.6 + 79.0) / 7, 2)  # mean of the last 7 readings
    assert s["to_goal"] == round(s["trend"] - 72.5, 2) and s["bmi"] == round(s["trend"] / 1.8 ** 2, 1)
    assert data["profile"]["unit"] == "lb"
    assert user.put("/api/weight/profile", json={"unit": "stone"}).status_code == 422
    assert user.put("/api/weight/profile", json={"height_cm": 20}).status_code == 422
    assert other.get("/api/weight").json()["entries"] == []  # private
    assert user.delete(f"/api/weight/{today}").status_code == 200
    assert user.delete(f"/api/weight/{today}").status_code == 404
    export = user.get("/api/account/export").json()
    assert len(export["weight"]["entries"]) == 9 and export["weight"]["profile"]["goal_kg"] == 72.5


def test_steps_streak_and_weight_badges(user):
    from datetime import date, timedelta
    today = date.today()
    for i in range(7):
        user.put("/api/wellness/steps", json={"steps": 9000, "log_date": str(today - timedelta(days=i))})
    first = user.put(f"/api/weight/{today}", json={"kg": 70}).json()
    got = {b["code"] for b in user.get("/api/badges").json() if b.get("earned")}
    assert {"steps_streak_7", "weight_first"} <= got and "weight_30" not in got
    assert [b["code"] for b in first["new_badges"]] == ["weight_first"]


def test_nuggets_economy_and_wallpapers(user):
    from app.infrastructure.database import SessionLocal
    from app.domain.models import User
    n = user.get("/api/nuggets").json()
    assert n["balance"] == 0 and n["points_per_nugget"] == 10 and n["next_in"] == 10 and len(n["catalog"]) >= 10
    assert user.post("/api/nuggets/wallpapers/topo/unlock").status_code == 422  # not enough nuggets
    assert user.post("/api/nuggets/wallpapers/nope/unlock").status_code == 404

    me = user.get("/api/auth/me").json()
    db = SessionLocal()
    db.query(User).filter(User.id == me["id"]).update({User.total_points: 127})  # 12 nuggets, 7 points towards the next
    db.commit()
    db.close()
    n = user.get("/api/nuggets").json()
    assert (n["earned"], n["balance"], n["next_in"]) == (12, 12, 3)

    after = user.post("/api/nuggets/wallpapers/topo/unlock").json()  # costs 5
    assert (after["spent"], after["balance"]) == (5, 7) and [u["id"] for u in after["unlocked"]] == ["topo"]
    assert user.post("/api/nuggets/wallpapers/topo/unlock").status_code == 409
    assert user.post("/api/nuggets/wallpapers/aurora/unlock").status_code == 422  # costs 25, 7 left
    assert user.get("/api/auth/me").json()["total_points"] == 127  # spending never touches points

    base = {"theme": "classic", "mode": "light", "needle_cursor": True, "language": "en"}
    assert user.put("/api/settings", json={**base, "wallpaper": "forest", "wallpapers_on": True}).json()["wallpaper"] is None  # locked: ignored, not an error
    assert user.put("/api/settings", json={**base, "wallpaper": "", "wallpapers_on": True}).status_code == 200
    ok = user.put("/api/settings", json={**base, "wallpaper": "topo", "wallpapers_on": True}).json()
    assert ok["wallpaper"] == "topo" and ok["wallpapers_on"] is True
    assert user.get("/api/account/export").json()["wallpapers_unlocked"][0]["id"] == "topo"


def test_goals_with_deadline_progress_and_privacy(user, other):
    from datetime import date, timedelta
    today = date.today()
    body = {"title": "Walk 20k", "metric": "steps", "target": 20000, "start_date": str(today - timedelta(days=2)), "end_date": str(today + timedelta(days=3))}
    assert user.post("/api/goals", json={**body, "metric": "nope"}).status_code == 422
    assert user.post("/api/goals", json={**body, "target": 0}).status_code == 422
    assert user.post("/api/goals", json={**body, "end_date": str(today - timedelta(days=5))}).status_code == 422
    g = user.post("/api/goals", json=body).json()
    assert g["status"] == "active" and g["progress"] == 0 and g["days_left"] == 4 and g["needed_per_day"] == 5000
    user.put("/api/wellness/steps", json={"steps": 12000, "log_date": str(today)})
    g = user.get("/api/goals").json()[0]
    assert g["progress"] == 12000 and g["percent"] == 60 and g["needed_per_day"] == 2000
    user.put("/api/wellness/steps", json={"steps": 20000, "log_date": str(today - timedelta(days=1))})
    assert user.get("/api/goals").json()[0]["status"] == "done"
    assert other.get("/api/goals").json() == []
    assert other.delete(f"/api/goals/{g['id']}").status_code == 404
    assert user.delete(f"/api/goals/{g['id']}").status_code == 200


def test_year_review_totals(user):
    from datetime import date
    today = date.today()
    h = user.post("/api/habits", json={"name": "Read", "frequency": "daily", "category": "mind"}).json()
    user.post(f"/api/habits/{h['id']}/check-in")
    user.put("/api/wellness/steps", json={"steps": 9000, "log_date": str(today)})
    user.put("/api/mood", json={"score": 8})
    r = user.get("/api/insights/year", params={"year": today.year}).json()
    assert r["checkins"] == 1 and r["active_days"] == 1 and r["best_streak"] == 1
    assert r["checkins_by_month"][today.month - 1] == 1 and r["best_month"] == today.month
    assert r["top_habits"] == [{"name": "Read", "count": 1}] and r["steps_total"] == 9000 and r["step_goal_days"] == 1
    assert r["mood_avg"] == 8.0 and r["badges_earned"] >= 1
    assert user.get("/api/insights/year", params={"year": 1899}).status_code == 422
    assert user.get("/api/insights/year", params={"year": today.year + 1}).status_code == 422


def test_water_workouts_gratitude(user, other):
    from datetime import date
    today = str(date.today())
    assert user.put(f"/api/water/{today}", json={"glasses": 99}).status_code == 422
    user.put(f"/api/water/{today}", json={"glasses": 8})
    w = user.get("/api/water").json()
    assert w["today"] == 8 and w["goal_streak"] == 1 and w["goal"] == 8 and len(w["days"]) == 14
    assert user.post("/api/workouts", json={"kind": "flying", "minutes": 20}).status_code == 422
    assert user.post("/api/workouts", json={"kind": "run", "minutes": 0}).status_code == 422
    user.post("/api/workouts", json={"kind": "run", "minutes": 30, "note": "park"})
    user.post("/api/workouts", json={"kind": "yoga", "minutes": 20})
    wk = user.get("/api/workouts").json()
    assert wk["total_minutes"] == 50 and wk["by_kind"] == {"run": 30, "yoga": 20} and len(wk["items"]) == 2
    assert other.get("/api/workouts").json()["items"] == []
    assert user.delete(f"/api/workouts/{wk['items'][0]['id']}").status_code == 200
    for i in range(5):
        assert user.post("/api/gratitude", json={"text": f"thing {i}"}).status_code == 200
    assert user.post("/api/gratitude", json={"text": "sixth"}).status_code == 422  # five a day
    assert user.post("/api/gratitude", json={"text": "  "}).status_code == 422
    g = user.get("/api/gratitude").json()
    assert g["total"] == 5 and other.get("/api/gratitude").json()["items"] == []
    export = user.get("/api/account/export").json()
    assert len(export["gratitude"]) == 5 and len(export["workouts"]) == 1 and export["water"][0]["glasses"] == 8


import pytest
from app.api.routers import quests as quests_module


@pytest.mark.parametrize("quest", quests_module.QUESTS, ids=[q[0] for q in quests_module.QUESTS])
def test_daily_quest_claim_gives_one_nugget(user, monkeypatch, quest):
    from datetime import date
    monkeypatch.setattr(quests_module, "quest_for", lambda user_id, day: quest)  # try every kind of quest
    q = user.get("/api/quests/today").json()
    assert not q["done"] and not q["claimed"] and q["reward_nuggets"] == 1
    assert user.post("/api/quests/today/claim").status_code == 422  # not finished
    # finish whatever today's quest is
    today = str(date.today())
    metric, target = q["metric"], q["target"]
    if metric == "checkins":
        for i in range(target):
            h = user.post("/api/habits", json={"name": f"h{i}", "frequency": "daily", "category": "mind"}).json()
            user.post(f"/api/habits/{h['id']}/check-in")
    elif metric == "steps":
        user.put("/api/wellness/steps", json={"steps": target})
    elif metric == "meditation_minutes":
        user.post("/api/meditation", json={"duration_minutes": target})
    elif metric == "pomodoros":
        for _ in range(target):
            user.post("/api/pomodoro", json={"duration_minutes": 25, "kind": "work"})
    elif metric == "journal_entries":
        user.post("/api/journal", data={"content": "x", "entry_date": today})
    elif metric == "mood_logs":
        user.put("/api/mood", json={"score": 7})
    elif metric == "water":
        user.put(f"/api/water/{today}", json={"glasses": target})
    elif metric == "workout_minutes":
        user.post("/api/workouts", json={"kind": "walk", "minutes": target})
    done = user.get("/api/quests/today").json()
    assert done["done"], done
    before = user.get("/api/nuggets").json()["balance"]  # points from the activity itself may already have given some
    claimed = user.post("/api/quests/today/claim").json()
    assert claimed["claimed"] and claimed["completed_total"] == 1
    assert user.post("/api/quests/today/claim").status_code == 409
    assert user.get("/api/nuggets").json()["balance"] == before + 1


def test_journal_recording_is_filed_under_its_day_and_counted(user):
    from datetime import date, timedelta
    past = date.today() - timedelta(days=3)
    r = user.post("/api/journal", data={"entry_date": str(past), "audio_seconds": "5"}, files={"audio": ("a.webm", b"\x1aE\xdf\xa3fake", "audio/webm")})
    assert r.status_code == 200 and r.json()["entry_date"] == str(past) and r.json()["has_audio"] is True
    user.post("/api/journal", data={"entry_date": str(past), "content": "text too"})
    user.post("/api/journal", data={"entry_date": str(date.today()), "content": "today"})
    days = user.get("/api/journal/days", params={"start": str(past - timedelta(days=1)), "end": str(date.today())}).json()
    assert days == [{"date": str(past), "entries": 2, "recordings": 1}, {"date": str(date.today()), "entries": 1, "recordings": 0}]
    assert user.get("/api/journal/days", params={"start": "2026-02-01", "end": "2026-01-01"}).status_code == 422


def test_profile_photo_is_private_and_validated(user, other):
    png = b"\x89PNG\r\n\x1a\n" + b"0" * 200
    assert user.get("/api/profile-photo").status_code == 404
    bad = user.put("/api/profile-photo", files={"file": ("x.png", b"not a png at all", "image/png")})
    assert bad.status_code == 422
    assert user.put("/api/profile-photo", files={"file": ("x.gif", png, "image/gif")}).status_code == 422
    assert user.put("/api/profile-photo", files={"file": ("x.png", b"\x89PNG" + b"0" * 500_000, "image/png")}).status_code == 422
    assert user.put("/api/profile-photo", files={"file": ("x.png", png, "image/png")}).status_code == 200
    got = user.get("/api/profile-photo")
    assert got.status_code == 200 and got.content == png and got.headers["content-type"] == "image/png"
    assert other.get("/api/profile-photo").status_code == 404  # nobody else can see it
    assert user.get("/api/account/export").json()["has_profile_photo"] is True
    assert user.delete("/api/profile-photo").status_code == 200 and user.get("/api/profile-photo").status_code == 404


def test_focus_time_per_project(user, other):
    for title, minutes in [("Thesis", 25), ("thesis ", 25), ("Reading", 15), (None, 25)]:
        user.post("/api/pomodoro", json={"kind": "work", "duration_minutes": minutes, "title": title})
    rows = user.get("/api/pomodoro/projects").json()
    assert [(r["title"].lower(), r["minutes"], r["sessions"]) for r in rows] == [("thesis", 50, 2), ("reading", 15, 1)]
    assert other.get("/api/pomodoro/projects").json() == []


def test_group_members_see_my_photo_only_if_i_share_it(user, other):
    png = b"\x89PNG\r\n\x1a\n" + b"1" * 100
    me = user.get("/api/auth/me").json()["id"]
    user.put("/api/profile-photo", files={"file": ("x.png", png, "image/png")})
    assert user.get("/api/profile-photo/status").json() == {"has_photo": True, "share_with_groups": False}
    g = user.post("/api/groups", json={"name": "Crew"}).json()
    other.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    board = lambda who: {e["user_id"]: e["has_photo"] for e in who.get(f"/api/groups/{g['id']}").json()["leaderboard"]}
    assert board(user)[me] is True  # my own is always shown to me
    assert board(other)[me] is False and other.get(f"/api/profile-photo/user/{me}").status_code == 404  # not shared yet
    assert user.put("/api/profile-photo/sharing", json={"share": True}).json()["share_with_groups"] is True
    assert board(other)[me] is True
    got = other.get(f"/api/profile-photo/user/{me}")
    assert got.status_code == 200 and got.content == png
    stranger = other  # someone who shares no group with the owner gets nothing
    user.delete(f"/api/groups/{g['id']}/members/me")
    assert stranger.get(f"/api/profile-photo/user/{me}").status_code == 404


def test_group_shared_habit_streak_and_cheers(user, other):
    g = user.post("/api/groups", json={"name": "Crew"}).json()
    other.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    base = f"/api/groups/{g['id']}"
    assert user.post(f"{base}/habits", json={"name": " "}).status_code == 422
    h = other.post(f"{base}/habits", json={"name": "Walk 20 min"}).json()  # any member may add one
    assert h["members_total"] == 2 and h["group_streak"] == 0 and not h["all_done_today"]
    mine = user.post(f"{base}/habits/{h['id']}/check").json()
    assert mine["me_done"] and mine["done_today"] == 1 and not mine["all_done_today"] and mine["group_streak"] == 0
    assert user.post(f"{base}/habits/{h['id']}/check").status_code == 409
    both = other.post(f"{base}/habits/{h['id']}/check").json()
    assert both["all_done_today"] and both["group_streak"] == 1  # everyone did it today
    assert user.get(f"{base}/habits").json()[0]["members"][0]["done"] is True

    stranger_id = other.get("/api/auth/me").json()["id"]
    me_id = user.get("/api/auth/me").json()["id"]
    assert user.post(f"{base}/cheers", json={"to_user_id": me_id, "emoji": "👏"}).status_code == 422  # not yourself
    assert user.post(f"{base}/cheers", json={"to_user_id": stranger_id, "emoji": "😈"}).status_code == 422
    assert user.post(f"{base}/cheers", json={"to_user_id": stranger_id, "emoji": "💪"}).status_code == 200
    assert user.post(f"{base}/cheers", json={"to_user_id": stranger_id, "emoji": "👏"}).status_code == 409  # one a day
    got = other.get(f"{base}/cheers").json()
    assert got["received"] == [{"from": user.get("/api/auth/me").json()["name"], "emoji": "💪"}]
    assert user.get(f"{base}/cheers").json()["sent_to"] == [stranger_id]

    assert other.delete(f"{base}/habits/{h['id']}").status_code == 200
    assert user.get(f"{base}/habits").json() == []


def test_review_fixes(user, other):
    from datetime import date, timedelta
    # the last member leaving a group with shared habits and cheers works (no foreign-key error)
    g = user.post("/api/groups", json={"name": "Solo"}).json()
    user.post(f"/api/groups/{g['id']}/habits", json={"name": "Stretch"})
    assert user.delete(f"/api/groups/{g['id']}/members/me").status_code == 200
    # a day ahead (a time zone ahead of the server) is accepted, three days ahead is not
    tomorrow = date.today() + timedelta(days=1)
    assert user.put(f"/api/water/{tomorrow}", json={"glasses": 2}).status_code == 200
    assert user.put(f"/api/water/{date.today() + timedelta(days=3)}", json={"glasses": 2}).status_code == 422
    # a locked journal also hides its day counts
    user.post("/api/journal", data={"entry_date": str(date.today()), "content": "x"})
    user.post("/api/journal/lock", json={"pin": "1234"})
    r = user.get("/api/journal/days", params={"start": str(date.today()), "end": str(date.today())})
    assert r.status_code == 423
    ok = user.get("/api/journal/days", params={"start": str(date.today()), "end": str(date.today())}, headers={"X-Journal-Pin": "1234"})
    assert ok.status_code == 200 and ok.json()[0]["entries"] == 1


def test_ics_export_is_valid(user):
    long = "Ελληνικό κείμενο " * 12
    user.post("/api/calendar/events", json={"title": "Line\r\nbreak", "event_date": "2026-03-02", "notes": long})
    body = user.get("/api/calendar/events/ics").text
    lines = body.split("\r\n")
    assert all(len(l.encode("utf-8")) <= 75 for l in lines)  # folded
    assert "SUMMARY:Line\\nbreak" in body  # the carriage return became an escaped newline, not a raw break
    unfolded = body.replace("\r\n ", "")
    assert long.strip() in unfolded.replace("\\,", ",")


def test_repeated_wrong_passwords_and_pins_are_slowed_down(user):
    from app.application.services import ratelimit
    email = f"limit_{__import__('uuid').uuid4().hex[:8]}@t.io"
    user.client.post("/api/auth/register", json={"name": "L", "email": email, "password": "password123"})
    for _ in range(8):
        assert user.client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 401
    assert user.client.post("/api/auth/login", json={"email": email, "password": "wrong-password"}).status_code == 429
    assert user.client.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 429  # even the right one waits
    ratelimit.logins.reset(email)
    assert user.client.post("/api/auth/login", json={"email": email, "password": "password123"}).status_code == 200

    user.post("/api/journal/lock", json={"pin": "1234"})
    for _ in range(8):
        assert user.get("/api/journal", headers={"X-Journal-Pin": "0000"}).status_code == 403
    assert user.get("/api/journal", headers={"X-Journal-Pin": "1234"}).status_code == 429


def test_migrations_build_the_same_schema_as_the_models():
    """A new database made with `alembic upgrade head` must equal what the models describe (no forgotten migration)."""
    import psycopg2
    from alembic import command
    from alembic.config import Config
    from pathlib import Path
    from sqlalchemy.engine import make_url
    from app.config import settings
    url = make_url(settings.database_url)
    admin = psycopg2.connect(dbname="postgres", user=url.username, password=url.password, host=url.host, port=url.port or 5432)
    admin.autocommit = True
    cur = admin.cursor()
    cur.execute("DROP DATABASE IF EXISTS daycompass_migtest")
    cur.execute("CREATE DATABASE daycompass_migtest")
    original = settings.database_url
    try:
        settings.database_url = url.set(database="daycompass_migtest").render_as_string(hide_password=False)
        cfg = Config(str(Path(__file__).resolve().parent.parent / "alembic.ini"))
        command.upgrade(cfg, "head")
        command.check(cfg)  # raises if the models have changes no migration covers
    finally:
        settings.database_url = original
        cur.execute("DROP DATABASE IF EXISTS daycompass_migtest")
        admin.close()


def test_new_badges_are_earned_by_the_new_features(user, other):
    from datetime import date, timedelta
    today = date.today()
    earned = lambda: {b["code"] for b in user.get("/api/badges").json() if b.get("earned")}
    w = user.put(f"/api/water/{today}", json={"glasses": 8}).json()
    assert [b["code"] for b in w["new_badges"]] == ["water_first"]
    assert [b["code"] for b in user.post("/api/workouts", json={"kind": "run", "minutes": 30}).json()["new_badges"]] == ["workout_first"]
    assert [b["code"] for b in user.post("/api/gratitude", json={"text": "tea"}).json()["new_badges"]] == ["gratitude_first"]
    # a goal reached: the badge appears the next time goals are listed
    user.post("/api/goals", json={"title": "Move", "metric": "steps", "target": 100, "start_date": str(today), "end_date": str(today + timedelta(days=2))})
    user.put("/api/wellness/steps", json={"steps": 500})
    user.get("/api/goals")
    assert "goal_first" in earned()
    # group things
    g = user.post("/api/groups", json={"name": "Crew"}).json()
    other.post("/api/groups/join", json={"invite_code": g["invite_code"]})
    h = user.post(f"/api/groups/{g['id']}/habits", json={"name": "Walk"}).json()
    user.post(f"/api/groups/{g['id']}/habits/{h['id']}/check")
    other_id = other.get("/api/auth/me").json()["id"]
    sent = user.post(f"/api/groups/{g['id']}/cheers", json={"to_user_id": other_id, "emoji": "👏"}).json()
    assert [b["code"] for b in sent["new_badges"]] == ["cheer_first"]
    # wallpapers
    from app.infrastructure.database import SessionLocal
    from app.domain.models import User
    me = user.get("/api/auth/me").json()["id"]
    db = SessionLocal(); db.query(User).filter(User.id == me).update({User.total_points: 500}); db.commit(); db.close()
    un = user.post("/api/nuggets/wallpapers/topo/unlock").json()
    assert "wallpaper_first" in [b["code"] for b in un["new_badges"]]
    assert {"water_first", "workout_first", "gratitude_first", "goal_first", "cheer_first", "wallpaper_first"} <= earned()


def test_push_subscriptions_and_reminder_job(user, other, monkeypatch):
    from datetime import date
    from app.application.services import push as push_service
    from app.application.services.push import send_push_reminders
    from app.infrastructure.database import SessionLocal
    from app.config import settings

    assert user.get("/api/push/key").json() == {"enabled": False, "public_key": None}  # not set up: everything stays off
    sub = {"endpoint": "https://push.example.test/abc", "keys": {"p256dh": "k", "auth": "a"}}
    assert user.post("/api/push/subscribe", json=sub).status_code == 503

    monkeypatch.setattr(settings, "vapid_public_key", "PUB")
    monkeypatch.setattr(settings, "vapid_private_key", "PRIV")
    assert user.get("/api/push/key").json() == {"enabled": True, "public_key": "PUB"}
    assert user.post("/api/push/subscribe", json={**sub, "endpoint": "http://insecure"}).status_code == 422
    assert user.post("/api/push/subscribe", json=sub).json() == {"subscribed": True}
    assert user.post("/api/push/subscribe", json=sub).status_code == 200  # the same device again is fine

    sent = []
    monkeypatch.setattr(push_service, "send_to_subscription", lambda db, s, payload: sent.append(payload) or True)
    user.post("/api/habits", json={"name": "Read", "frequency": "daily", "category": "mind"})
    db = SessionLocal()
    result = send_push_reminders(db, date.today())
    assert result["sent"] >= 1 and result["enabled"] is True
    first = len(sent)
    assert "habit" in sent[-1]["body"]
    send_push_reminders(db, date.today())  # at most once a day
    assert len(sent) == first
    db.close()

    assert user.post("/api/push/test").json()["sent"] == 1
    assert other.post("/api/push/unsubscribe", json={"endpoint": sub["endpoint"]}).status_code == 200  # not theirs: nothing happens
    assert user.post("/api/push/test").json()["sent"] == 1
    assert user.post("/api/push/unsubscribe", json={"endpoint": sub["endpoint"]}).json() == {"subscribed": False}
    assert user.post("/api/push/test").json()["sent"] == 0


def test_calendar_notes_mail_needs_its_own_switch(user, monkeypatch):
    from app.application.services import event_mail
    from app.infrastructure.database import SessionLocal
    sent = []
    monkeypatch.setattr(event_mail, "send_email", lambda to, subject, body: sent.append(to) or True)
    user.post("/api/calendar/events", json={"title": "Dentist", "event_date": str(TODAY)})
    user.put("/api/reminders", json={"enabled": True, "language": "en"})  # habit reminders on, notes mail NOT chosen
    db = SessionLocal()
    assert event_mail.send_event_mails(db, TODAY)["sent"] == 0 and sent == []
    user.put("/api/reminders", json={"enabled": True, "events_enabled": True, "language": "en"})
    assert user.get("/api/reminders").json()["events_enabled"] is True
    assert event_mail.send_event_mails(db, TODAY)["sent"] == 1
    db.close()


def test_two_recordings_on_the_same_day(user):
    from datetime import date
    day = str(date.today())
    ids = []
    for n in (1, 2):
        r = user.post("/api/journal", data={"entry_date": day, "audio_seconds": str(n * 5)}, files={"audio": ("a.webm", b"\x1aE\xdf\xa3" + bytes([n]) * 20, "audio/webm")})
        assert r.status_code == 200 and r.json()["has_audio"] is True
        ids.append(r.json()["id"])
    assert ids[0] != ids[1]
    listing = user.get("/api/journal").json()["entries"]
    assert [e["audio_seconds"] for e in listing if e["entry_date"] == day] == [10, 5]  # newest first, both kept
    assert user.get(f"/api/journal/{ids[0]}/audio").content != user.get(f"/api/journal/{ids[1]}/audio").content
    days = user.get("/api/journal/days", params={"start": day, "end": day}).json()
    assert days == [{"date": day, "entries": 2, "recordings": 2}]


def test_events_that_last_several_days(user):
    e = user.post("/api/calendar/events", json={"title": "Crete", "event_date": "2026-08-03", "end_date": "2026-08-06", "kind": "event"}).json()
    assert e["end_date"] == "2026-08-06"
    assert user.post("/api/calendar/events", json={"title": "x", "event_date": "2026-08-03", "end_date": "2026-08-01"}).status_code == 422
    assert user.post("/api/calendar/events", json={"title": "x", "event_date": "2026-08-03", "end_date": "2026-08-05", "repeat_weekly": True}).status_code == 422
    days = lambda a, b: [x["date"] for x in user.get("/api/calendar/events", params={"start": a, "end": b}).json()]
    assert days("2026-08-01", "2026-08-31") == ["2026-08-03", "2026-08-04", "2026-08-05", "2026-08-06"]
    assert days("2026-08-05", "2026-08-05") == ["2026-08-05"]          # a day in the middle of the range
    assert days("2026-07-01", "2026-08-02") == [] and days("2026-08-07", "2026-08-20") == []
    # yearly + range, running over New Year
    user.post("/api/calendar/events", json={"title": "Ski week", "event_date": "2026-12-29", "end_date": "2027-01-02", "repeat_yearly": True})
    assert days("2027-12-30", "2028-01-03") == ["2027-12-30", "2027-12-31", "2028-01-01", "2028-01-02"]
    assert days("2028-01-01", "2028-01-01") == ["2028-01-01"]
    ics = user.get("/api/calendar/events/ics").text
    assert "DTEND;VALUE=DATE:20260807" in ics  # all-day ends are exclusive in .ics
    assert user.put(f"/api/calendar/events/{e['id']}", json={"title": "Crete", "event_date": "2026-08-03", "end_date": None}).json()["end_date"] is None


def test_budget_month_limits_and_privacy(user, other):
    from datetime import date
    today = date.today()
    assert user.get("/api/money/profile").json()["currency"] == "EUR"
    assert user.put("/api/money/profile", json={"currency": "euro"}).status_code == 422
    user.put("/api/money/profile", json={"currency": "usd", "monthly_budget": 1000})
    assert user.post("/api/money/entries", json={"kind": "expense", "amount": 0, "category": "food"}).status_code == 422
    assert user.post("/api/money/entries", json={"kind": "expense", "amount": 5, "category": "salary"}).status_code == 422
    user.post("/api/money/entries", json={"kind": "income", "amount": 2000.50, "category": "salary"})
    user.post("/api/money/entries", json={"kind": "expense", "amount": 12.34, "category": "food", "note": "lunch"})
    user.post("/api/money/entries", json={"kind": "expense", "amount": 100, "category": "fun"})
    user.put("/api/money/limits", json={"category": "food", "monthly": 10})
    m = user.get("/api/money/month").json()
    assert m["currency"] == "USD" and m["income_cents"] == 200050 and m["spent_cents"] == 11234 and m["balance_cents"] == 200050 - 11234
    assert m["budget_cents"] == 100000 and m["left_cents"] == 100000 - 11234
    food = next(c for c in m["categories"] if c["category"] == "food")
    assert food == {"category": "food", "spent_cents": 1234, "limit_cents": 1000}  # over its limit: the app can show it
    assert len(m["entries"]) == 3 and other.get("/api/money/month").json()["entries"] == []
    assert user.delete(f"/api/money/entries/{m['entries'][0]['id']}").status_code == 200
    assert other.delete(f"/api/money/entries/{m['entries'][1]['id']}").status_code == 404


def test_savings_goals_projection_and_withdrawals(user):
    from datetime import date, timedelta
    g = user.post("/api/money/savings", json={"name": "Laptop", "target": 1000, "deadline": str(date.today() + timedelta(days=305))}).json()
    assert g["saved_cents"] == 0 and g["monthly_needed_cents"] is not None and 9000 <= g["monthly_needed_cents"] <= 11000
    assert user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": 0}).status_code == 422
    assert user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": -5}).status_code == 422  # nothing saved yet
    d = user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": 250}).json()
    assert d["saved_cents"] == 25000 and d["percent"] == 25 and d["projected"] is not None
    w = user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": -50}).json()
    assert w["saved_cents"] == 20000
    done = user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": 800}).json()
    assert done["done"] is True and done["remaining_cents"] == 0
    assert user.delete(f"/api/money/savings/{g['id']}").status_code == 200 and user.get("/api/money/savings").json()["goals"] == []


def test_trip_budget_daily_allowance_and_separate_from_the_month(user, other):
    from datetime import date, timedelta
    today = date.today()
    t = user.post("/api/money/trips", json={"name": "Lisbon", "start_date": str(today), "end_date": str(today + timedelta(days=4)), "budget": 500, "currency": "eur"}).json()
    assert t["total_days"] == 5 and t["daily_allowance_cents"] == 10000 and t["currency"] == "EUR"
    assert user.post("/api/money/trips", json={"name": "x", "start_date": str(today), "end_date": str(today - timedelta(days=1)), "budget": 5}).status_code == 422
    assert user.post("/api/money/entries", json={"kind": "income", "amount": 5, "category": "other", "trip_id": t["id"]}).status_code == 422  # trips only have expenses
    assert user.post("/api/money/entries", json={"kind": "expense", "amount": 5, "category": "home", "trip_id": t["id"]}).status_code == 422  # not a trip category
    user.post("/api/money/entries", json={"kind": "expense", "amount": 120, "category": "lodging", "trip_id": t["id"]})
    user.post("/api/money/entries", json={"kind": "expense", "amount": 30, "category": "food", "trip_id": t["id"]})
    got = user.get("/api/money/trips").json()[0]
    assert got["spent_cents"] == 15000 and got["left_cents"] == 35000 and got["percent"] == 30
    assert got["by_category"][0] == {"category": "lodging", "spent_cents": 12000}
    assert got["left_per_day_cents"] is not None and got["avg_per_day_cents"] == 15000  # first day: everything spent so far
    assert user.get("/api/money/month").json()["spent_cents"] == 0  # trip money is not everyday spending
    assert other.post("/api/money/entries", json={"kind": "expense", "amount": 5, "category": "food", "trip_id": t["id"]}).status_code == 404
    assert user.get("/api/account/export").json()["money"]["trips"][0]["name"] == "Lisbon"
    assert user.delete(f"/api/money/trips/{t['id']}").status_code == 200 and user.get("/api/money/trips").json() == []


def test_changing_a_savings_goal_and_a_trip_budget(user, other):
    from datetime import date, timedelta
    g = user.post("/api/money/savings", json={"name": "Laptop", "target": 800}).json()
    user.post(f"/api/money/savings/{g['id']}/deposit", json={"amount": 200})
    up = user.put(f"/api/money/savings/{g['id']}", json={"name": "Better laptop", "target": 1000, "deadline": str(date.today() + timedelta(days=100)), "kind": "general"}).json()
    assert up["name"] == "Better laptop" and up["target_cents"] == 100000 and up["saved_cents"] == 20000 and up["percent"] == 20 and up["monthly_needed_cents"]
    low = user.put(f"/api/money/savings/{g['id']}", json={"name": "Better laptop", "target": 150, "kind": "general"}).json()  # a target below what is saved: reached
    assert low["done"] is True and low["deadline"] is None
    assert user.put(f"/api/money/savings/{g['id']}", json={"name": "x", "target": 0}).status_code == 422
    assert other.put(f"/api/money/savings/{g['id']}", json={"name": "x", "target": 5}).status_code == 404
    t = user.post("/api/money/trips", json={"name": "Rome", "start_date": str(date.today()), "end_date": str(date.today() + timedelta(days=3)), "budget": 400}).json()
    new = user.put(f"/api/money/trips/{t['id']}", json={"name": "Rome", "start_date": t["start_date"], "end_date": t["end_date"], "budget": 600}).json()
    assert new["budget_cents"] == 60000 and new["daily_allowance_cents"] == 15000


def test_period_tracking_cycles_predictions_and_privacy(user, other):
    from datetime import date, timedelta
    today = date.today()
    first = today - timedelta(days=60)
    assert user.get("/api/cycle").json()["predictions"] == []  # nothing is assumed without data
    assert user.put(f"/api/cycle/day/{today}", json={"flow": "huge"}).status_code == 422
    assert user.post("/api/cycle/range", json={"start": str(first), "end": str(first - timedelta(days=1))}).status_code == 422
    assert user.post("/api/cycle/range", json={"start": str(first), "end": str(first + timedelta(days=20))}).status_code == 422
    for k in range(3):  # three periods of 5 days, 28 days apart: the last one started 4 days ago
        s = today - timedelta(days=4 + 28 * (2 - k))
        assert user.post("/api/cycle/range", json={"start": str(s), "end": str(s + timedelta(days=4)), "flow": "medium"}).json()["added"] == 5
    data = user.get("/api/cycle").json()
    assert [p["length"] for p in data["periods"]] == [5, 5, 5]
    assert data["stats"]["average_cycle"] == 28 and data["stats"]["average_period"] == 5 and data["stats"]["regular"] is None  # regularity needs 3+ cycles
    assert data["cycle_lengths"] == [28, 28]
    last_start = today - timedelta(days=4)
    assert data["predictions"][0]["start"] == str(last_start + timedelta(days=28))
    assert data["next_in_days"] == 24 and data["stats"]["current_cycle_day"] == 5
    user.put(f"/api/cycle/day/{today}", json={"flow": "light", "note": "cramps"})
    assert any(d["date"] == str(today) and d["note"] == "cramps" for d in user.get("/api/cycle").json()["days"])
    assert other.get("/api/cycle").json()["days"] == [] and other.delete(f"/api/cycle/day/{today}").status_code == 404
    assert user.delete(f"/api/cycle/day/{today}").status_code == 200
    export = user.get("/api/account/export").json()
    assert len(export["period_days"]) >= 14


def test_the_tour_is_remembered_by_the_account(user):
    base = {"theme": "classic", "mode": "light", "needle_cursor": True, "language": "en"}
    assert user.get("/api/settings").json()["tutorial_seen"] is False and user.get("/api/settings").json()["saved"] is False  # a new account: show the tour
    assert user.put("/api/settings", json={**base, "tutorial_seen": True}).json()["tutorial_seen"] is True
    assert user.get("/api/settings").json()["tutorial_seen"] is True
    assert user.put("/api/settings", json={**base, "tutorial_seen": False}).json()["tutorial_seen"] is False  # replaying it from the guide is up to the app
