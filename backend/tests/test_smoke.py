def test_api_is_up(client):
    assert client.get("/").json()["status"] == "DayCompass API running"


def test_register_login_and_me(client, user):
    login = client.post("/api/auth/login", json={"email": user.email, "password": user.password})
    assert login.status_code == 200
    assert user.get("/api/auth/me").json()["email"] == user.email
    assert client.post("/api/auth/login", json={"email": user.email, "password": "nope"}).status_code == 401
