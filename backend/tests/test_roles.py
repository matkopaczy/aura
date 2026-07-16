from decimal import Decimal

from sqlalchemy import select

from app.models import User, UserRole
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market


def _reception_headers(client, db_session, owner_headers):
    """Właściciel dodaje recepcję; zwraca nagłówki zalogowanej recepcji."""
    r = client.post(
        "/api/account/users",
        json={"email": "recepcja@example.com", "password": "haslo-recepcji-123"},
        headers=owner_headers,
    )
    assert r.status_code == 201
    assert r.json()["role"] == "reception"
    login = client.post(
        "/api/auth/login",
        json={"email": "recepcja@example.com", "password": "haslo-recepcji-123"},
    )
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_registration_makes_owner(client, db_session):
    _register(client)
    user = db_session.scalar(select(User))
    assert user.role == UserRole.OWNER


def test_me_exposes_role(client, db_session):
    headers = _register(client)
    r = client.get("/api/auth/me", headers=headers)
    assert r.json()["role"] == "owner"


def test_reception_shares_tenant_and_sees_recommendations(client, db_session):
    market = _seed_market(db_session)
    owner = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=owner).json()["id"]
    reception = _reception_headers(client, db_session, owner)

    # Recepcja widzi obiekty konta i rekomendacje (ten sam tenant)
    assert len(client.get("/api/properties", headers=reception).json()) == 1
    import datetime

    from tests.test_monitoring import _listing, _obs

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    listing = _listing(db_session, market, "pl/a")
    _obs(db_session, listing, tomorrow, Decimal("400"))
    db_session.commit()
    recs = client.post(
        f"/api/recommendations/{prop_id}/generate?days=3", headers=reception
    )
    assert recs.status_code == 200
    first = recs.json()[0]
    # Recepcja MOŻE akceptować/odrzucać — to jej praca
    r = client.post(
        f"/api/recommendations/decision/{first['id']}",
        json={"decision": "accepted"},
        headers=reception,
    )
    assert r.status_code == 200


def test_reception_blocked_from_owner_actions(client, db_session):
    _seed_market(db_session)
    owner = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=owner).json()["id"]
    reception = _reception_headers(client, db_session, owner)

    # Ustawienia cen (guardrails) — owner-only
    assert client.patch(
        f"/api/properties/{prop_id}", json={"min_price": 100}, headers=reception
    ).status_code == 403
    # Tworzenie obiektu — owner-only
    assert client.post(
        "/api/properties", json=PROPERTY_BODY, headers=reception
    ).status_code == 403
    # Rozliczenia — owner-only
    assert client.get("/api/billing/subscription", headers=reception).status_code == 403
    assert client.post("/api/billing/cancel", headers=reception).status_code == 403
    # Konto (RODO) — owner-only
    assert client.get("/api/account/export", headers=reception).status_code == 403
    assert client.delete("/api/account", headers=reception).status_code == 403
    # Zarządzanie zespołem — owner-only
    assert client.get("/api/account/users", headers=reception).status_code == 403
    assert client.post(
        "/api/account/users",
        json={"email": "x@example.com", "password": "dlugie-haslo-123"},
        headers=reception,
    ).status_code == 403


def test_owner_manages_team(client, db_session):
    _seed_market(db_session)
    owner = _register(client)
    reception = _reception_headers(client, db_session, owner)  # noqa: F841

    users = client.get("/api/account/users", headers=owner).json()
    assert len(users) == 2
    assert {u["role"] for u in users} == {"owner", "reception"}

    reception_id = next(u["id"] for u in users if u["role"] == "reception")
    assert client.delete(f"/api/account/users/{reception_id}", headers=owner).status_code == 204
    assert len(client.get("/api/account/users", headers=owner).json()) == 1


def test_owner_cannot_delete_self(client, db_session):
    owner = _register(client)
    me = client.get("/api/auth/me", headers=owner).json()
    r = client.delete(f"/api/account/users/{me['id']}", headers=owner)
    assert r.status_code == 400


def test_duplicate_email_rejected_for_reception(client, db_session):
    owner = _register(client)  # gospodarz@example.com
    r = client.post(
        "/api/account/users",
        json={"email": "gospodarz@example.com", "password": "dlugie-haslo-123"},
        headers=owner,
    )
    assert r.status_code == 409
