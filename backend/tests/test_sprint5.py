import datetime

from sqlalchemy import func, select

from app.billing import start_trial, view
from app.models import (
    Account,
    Subscription,
    SubscriptionStatus,
    User,
    WaitlistEntry,
)
from app.models.base import utcnow
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market


def test_registration_creates_trial(client, db_session):
    _register(client)
    sub = db_session.scalar(select(Subscription))
    assert sub is not None
    assert sub.status == SubscriptionStatus.TRIALING
    assert sub.trial_ends_at is not None
    v = view(sub)
    assert v.trial_days_left is not None and 28 <= v.trial_days_left <= 30
    assert v.is_expired is False


def test_trial_expiry_detected(db_session):
    account = Account(name="Test")
    db_session.add(account)
    db_session.flush()
    sub = start_trial(db_session, account)
    db_session.commit()
    sub.trial_ends_at = utcnow() - datetime.timedelta(days=1)
    db_session.commit()
    v = view(sub)
    assert v.is_expired is True
    assert v.trial_days_left is None


def test_start_trial_idempotent(db_session):
    account = Account(name="Test")
    db_session.add(account)
    db_session.flush()
    start_trial(db_session, account)
    db_session.commit()
    start_trial(db_session, account)
    db_session.commit()
    count = db_session.scalar(
        select(func.count()).select_from(Subscription).where(
            Subscription.account_id == account.id
        )
    )
    assert count == 1


def test_billing_endpoint_and_cancel(client, db_session):
    headers = _register(client)
    r = client.get("/api/billing/subscription", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "trialing"
    assert r.json()["currency_code"] == "PLN"

    r = client.post("/api/billing/cancel", headers=headers)
    assert r.status_code == 200
    assert r.json()["status"] == "canceled"


def test_public_market_preview_no_auth(client, db_session):
    _seed_market(db_session)
    r = client.get("/api/public/preview/poznan")
    assert r.status_code == 200
    body = r.json()
    assert body["market_slug"] == "poznan"
    assert body["currency_code"] == "PLN"
    assert len(body["days"]) == 30


def test_public_markets_list(client, db_session):
    _seed_market(db_session)
    r = client.get("/api/public/markets")
    assert r.status_code == 200
    assert any(m["slug"] == "poznan" for m in r.json())


def test_waitlist_signup_and_dedup(client, db_session):
    _seed_market(db_session)
    body = {"email": "Gosc@Example.com", "market_slug": "poznan"}
    assert client.post("/api/public/waitlist", json=body).status_code == 201
    assert client.post("/api/public/waitlist", json=body).status_code == 201  # dedup
    entries = db_session.scalars(select(WaitlistEntry)).all()
    assert len(entries) == 1
    assert entries[0].email == "gosc@example.com"  # znormalizowany


def test_waitlist_unknown_market(client, db_session):
    r = client.post("/api/public/waitlist", json={"email": "a@b.pl", "market_slug": "nieznane"})
    assert r.status_code == 404


def test_account_export(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    client.post("/api/properties", json=PROPERTY_BODY, headers=headers)
    r = client.get("/api/account/export", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["account"]["name"] == "Test"
    assert len(body["properties"]) == 1
    assert body["subscription"]["status"] == "trialing"


def test_account_delete_removes_all_tenant_data(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    client.post("/api/properties", json=PROPERTY_BODY, headers=headers)

    r = client.delete("/api/account", headers=headers)
    assert r.status_code == 204
    assert db_session.scalar(select(func.count()).select_from(User)) == 0
    assert db_session.scalar(select(func.count()).select_from(Account)) == 0
    assert db_session.scalar(select(func.count()).select_from(Subscription)) == 0
    # token nie działa po usunięciu konta
    assert client.get("/api/auth/me", headers=headers).status_code == 401


def test_security_headers_present(client, db_session):
    r = client.get("/api/health")
    assert r.headers["X-Content-Type-Options"] == "nosniff"
    assert r.headers["X-Frame-Options"] == "DENY"


def test_auth_rate_limit(client, db_session):
    body = {"email": "nikt@example.com", "password": "zle-haslo-123"}
    statuses = [client.post("/api/auth/login", json=body).status_code for _ in range(12)]
    assert 429 in statuses  # po przekroczeniu limitu
    assert statuses[:10] == [401] * 10  # pierwsze 10 przechodzi do logiki (401)
