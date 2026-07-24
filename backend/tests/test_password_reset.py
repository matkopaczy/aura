import datetime

from sqlalchemy import select

from app.auth.security import verify_password
from app.models import PasswordResetToken, User
from app.models.base import utcnow
from app.password_reset import request_reset, resolve

REGISTER_BODY = {
    "account_name": "Apartamenty Testowe",
    "email": "gospodarz@example.com",
    "password": "bardzo-tajne-haslo",
}


def _register(client, db):
    client.post("/api/auth/register", json=REGISTER_BODY)
    return db.scalar(select(User).where(User.email == REGISTER_BODY["email"]))


def test_request_endpoint_never_reveals_account_existence(client, db_session):
    """§9: ta sama odpowiedź niezależnie od tego, czy konto istnieje."""
    _register(client, db_session)
    existing = client.post(
        "/api/auth/password-reset/request", json={"email": REGISTER_BODY["email"]}
    )
    missing = client.post(
        "/api/auth/password-reset/request", json={"email": "nikt-taki@example.com"}
    )
    assert existing.status_code == missing.status_code == 200
    assert existing.json() == missing.json()


def test_request_creates_token_only_for_existing_user(client, db_session):
    _register(client, db_session)
    client.post("/api/auth/password-reset/request", json={"email": REGISTER_BODY["email"]})
    client.post(
        "/api/auth/password-reset/request", json={"email": "nikt-taki@example.com"}
    )
    assert db_session.scalar(select(PasswordResetToken).limit(1)) is not None
    # dokładnie jeden token — drugie żądanie (nieistniejące konto) nic nie utworzyło
    assert len(db_session.scalars(select(PasswordResetToken)).all()) == 1


def test_confirm_flow_changes_password_and_logs_in(client, db_session):
    user = _register(client, db_session)
    raw = request_reset(db_session, REGISTER_BODY["email"])

    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "new_password": "nowe-bardzo-tajne-haslo"},
    )
    assert r.status_code == 200
    assert r.json()["access_token"]

    db_session.refresh(user)
    assert verify_password("nowe-bardzo-tajne-haslo", user.password_hash)
    assert not verify_password(REGISTER_BODY["password"], user.password_hash)

    # stare hasło już nie działa do logowania
    old_login = client.post(
        "/api/auth/login",
        json={"email": REGISTER_BODY["email"], "password": REGISTER_BODY["password"]},
    )
    assert old_login.status_code == 401


def test_confirm_rejects_token_twice(client, db_session):
    _register(client, db_session)
    raw = request_reset(db_session, REGISTER_BODY["email"])
    first = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "new_password": "nowe-bardzo-tajne-haslo"},
    )
    assert first.status_code == 200
    second = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "new_password": "jeszcze-inne-haslo-123"},
    )
    assert second.status_code == 400
    assert second.json()["detail"] == "used"


def test_confirm_rejects_invalid_token(client):
    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": "nieistniejacy-token", "new_password": "cos-tam-haslo-12"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "invalid"


def test_confirm_rejects_expired_token(client, db_session):
    _register(client, db_session)
    raw = request_reset(db_session, REGISTER_BODY["email"])
    token = db_session.scalar(select(PasswordResetToken))
    token.expires_at = utcnow() - datetime.timedelta(minutes=1)
    db_session.commit()

    r = client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "new_password": "cos-tam-haslo-12"},
    )
    assert r.status_code == 400
    assert r.json()["detail"] == "expired"


def test_new_request_invalidates_previous_token(client, db_session):
    """Nowe żądanie kasuje niewykorzystany token z poprzedniego — działa tylko
    najświeższy link (wzorzec z issue_tokens dla decyzji e-mailowych)."""
    _register(client, db_session)
    first_raw = request_reset(db_session, REGISTER_BODY["email"])
    request_reset(db_session, REGISTER_BODY["email"])

    _, _, error = resolve(db_session, first_raw)
    assert error == "invalid"
