REGISTER_BODY = {
    "account_name": "Apartamenty Testowe",
    "email": "gospodarz@example.com",
    "password": "bardzo-tajne-haslo",
}


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_register_login_me_flow(client):
    r = client.post("/api/auth/register", json=REGISTER_BODY)
    assert r.status_code == 201
    token = r.json()["access_token"]

    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    body = r.json()
    assert body["email"] == "gospodarz@example.com"
    assert body["locale"] == "pl"
    assert body["account_id"]

    r = client.post(
        "/api/auth/login",
        json={"email": "gospodarz@example.com", "password": "bardzo-tajne-haslo"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_register_duplicate_email_conflict(client):
    assert client.post("/api/auth/register", json=REGISTER_BODY).status_code == 201
    assert client.post("/api/auth/register", json=REGISTER_BODY).status_code == 409


def test_login_wrong_password_rejected(client):
    client.post("/api/auth/register", json=REGISTER_BODY)
    r = client.post(
        "/api/auth/login",
        json={"email": "gospodarz@example.com", "password": "zle-haslo-zupelnie"},
    )
    assert r.status_code == 401


def test_me_without_token_rejected(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_garbage_token_rejected(client):
    r = client.get("/api/auth/me", headers={"Authorization": "Bearer nonsens"})
    assert r.status_code == 401
