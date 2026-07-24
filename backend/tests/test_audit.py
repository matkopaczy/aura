from sqlalchemy import select

from app.models import AuditLog, User
from tests.test_api_sprint2 import _register

REGISTER_EMAIL = "gospodarz@example.com"
REGISTER_PASSWORD = "bardzo-tajne-haslo"


def test_login_creates_audit_entry(client, db_session):
    _register(client)
    client.post(
        "/api/auth/login", json={"email": REGISTER_EMAIL, "password": REGISTER_PASSWORD}
    )
    entries = db_session.scalars(select(AuditLog).where(AuditLog.action == "login")).all()
    assert len(entries) == 1
    user = db_session.scalar(select(User).where(User.email == REGISTER_EMAIL))
    assert entries[0].user_id == user.id
    assert entries[0].account_id == user.account_id


def test_password_reset_creates_two_audit_entries(client, db_session):
    from app.password_reset import request_reset

    _register(client)
    client.post("/api/auth/password-reset/request", json={"email": REGISTER_EMAIL})
    raw = request_reset(db_session, REGISTER_EMAIL)
    client.post(
        "/api/auth/password-reset/confirm",
        json={"token": raw, "new_password": "nowe-bardzo-tajne-haslo"},
    )
    actions = sorted(
        a.action for a in db_session.scalars(
            select(AuditLog).where(AuditLog.action.like("password_reset%"))
        ).all()
    )
    assert actions == ["password_reset_confirmed", "password_reset_requested"]


def test_password_reset_request_for_missing_account_creates_no_entry(client, db_session):
    _register(client)
    client.post(
        "/api/auth/password-reset/request", json={"email": "nikt-taki@example.com"}
    )
    assert db_session.scalars(select(AuditLog)).all() == []


def test_reception_lifecycle_creates_audit_entries(client, db_session):
    headers = _register(client)
    client.post(
        "/api/account/users",
        json={"email": "recepcja@example.com", "password": "haslo-recepcji-123"},
        headers=headers,
    )
    user_id = db_session.scalar(
        select(User.id).where(User.email == "recepcja@example.com")
    )
    client.delete(f"/api/account/users/{user_id}", headers=headers)

    actions = sorted(
        a.action for a in db_session.scalars(
            select(AuditLog).where(AuditLog.action.like("reception%"))
        ).all()
    )
    assert actions == ["reception_created", "reception_deleted"]


def test_export_creates_audit_entry(client, db_session):
    headers = _register(client)
    client.get("/api/account/export", headers=headers)
    entries = db_session.scalars(
        select(AuditLog).where(AuditLog.action == "account_exported")
    ).all()
    assert len(entries) == 1


def test_account_delete_removes_audit_log_without_fk_error(client, db_session):
    """AuditLog musi być na liście czyszczenia delete_account — inaczej ten
    sam bug FK co Booking/ActionToken (naprawiony wcześniej w tej sesji)."""
    headers = _register(client)
    client.post(
        "/api/auth/login", json={"email": REGISTER_EMAIL, "password": REGISTER_PASSWORD}
    )
    assert db_session.scalars(select(AuditLog)).all() != []  # jest co czyścić

    r = client.delete("/api/account", headers=headers)
    assert r.status_code == 204
    assert db_session.scalars(select(AuditLog)).all() == []
