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
    user.put("/api/reminders", json={"enabled": True, "language": "fr"})
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
    assert user.put(f"/api/weight/{today + timedelta(days=1)}", json={"kg": 70}).status_code == 422
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
