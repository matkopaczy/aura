import datetime
import uuid
from decimal import Decimal

from sqlalchemy import select

from app.models import CalendarDay, Property, Recommendation, RecommendationStatus
from app.models.base import utcnow
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market
from tests.test_monitoring import _listing, _obs


def _book(db, prop_id, day):
    prop = db.get(Property, uuid.UUID(prop_id))
    db.add(CalendarDay(
        account_id=prop.account_id, property_id=prop.id, stay_date=day, synced_at=utcnow(),
    ))
    db.commit()


def test_ical_booked_nights_skipped_and_orphan_discounted(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    base = datetime.date.today() + datetime.timedelta(days=10)
    # Kotwica na środę: sierota (base+1 = czwartek) i zwykła noc (base+5 =
    # poniedziałek) są oba zwykłymi dniami roboczymi — bez zanieczyszczenia
    # czynnikiem weekendu/niedzieli, inaczej test zależy od dnia uruchomienia.
    base += datetime.timedelta(days=(2 - base.weekday()) % 7)
    # rezerwacje: base i base+2 zajęte -> base+1 to noc-sierota
    _book(db_session, prop_id, base)
    _book(db_session, prop_id, base + datetime.timedelta(days=2))

    recs = client.post(
        f"/api/recommendations/{prop_id}/generate?days=25", headers=headers
    ).json()
    by_date = {r["stay_date"]: r for r in recs}

    # zarezerwowane noce pominięte
    assert base.isoformat() not in by_date
    assert (base + datetime.timedelta(days=2)).isoformat() not in by_date
    # sierota obecna, z czynnikiem orphan_night
    orphan = by_date[(base + datetime.timedelta(days=1)).isoformat()]
    keys = [f["key"] for f in orphan["explanation_params"]["factors"]]
    assert "orphan_night" in keys
    # rabat: sierota tańsza niż zwykła wolna noc (te same pozostałe czynniki)
    regular = by_date[(base + datetime.timedelta(days=5)).isoformat()]
    assert Decimal(orphan["recommended_price"]) < Decimal(regular["recommended_price"])


def test_booked_night_expires_existing_pending(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]
    target = datetime.date.today() + datetime.timedelta(days=5)

    client.post(f"/api/recommendations/{prop_id}/generate?days=10", headers=headers)
    # noc się sprzedała po pierwszym przebiegu
    _book(db_session, prop_id, target)
    client.post(f"/api/recommendations/{prop_id}/generate?days=10", headers=headers)

    rec = db_session.scalar(
        select(Recommendation).where(Recommendation.stay_date == target)
    )
    assert rec.status == RecommendationStatus.EXPIRED


def _setup(client, db_session):
    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    listing = _listing(db_session, market, "pl/a")
    _obs(db_session, listing, tomorrow, Decimal("400"))
    db_session.commit()
    return headers, prop_id, tomorrow


def test_generate_list_accept_flow(client, db_session):
    headers, prop_id, tomorrow = _setup(client, db_session)

    r = client.post(f"/api/recommendations/{prop_id}/generate?days=7", headers=headers)
    assert r.status_code == 200
    recs = r.json()
    assert len(recs) == 7
    first = next(rec for rec in recs if rec["stay_date"] == tomorrow.isoformat())
    # baza 250 vs mediana 400 -> podbicie w górę (+15% max korekty pozycji)
    assert Decimal(first["recommended_price"]) > Decimal("250")
    assert first["status"] == "pending"
    assert first["explanation_template_key"] == "v1"
    factor_keys = [f["key"] for f in first["explanation_params"]["factors"]]
    assert "below_median" in factor_keys

    r = client.post(
        f"/api/recommendations/decision/{first['id']}",
        json={"decision": "accepted"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"
    assert r.json()["decided_at"] is not None

    # ponowna decyzja = 409
    r = client.post(
        f"/api/recommendations/decision/{first['id']}",
        json={"decision": "rejected"},
        headers=headers,
    )
    assert r.status_code == 409


def test_regenerate_updates_pending_but_preserves_decided(client, db_session):
    headers, prop_id, tomorrow = _setup(client, db_session)
    recs = client.post(
        f"/api/recommendations/{prop_id}/generate?days=7", headers=headers
    ).json()
    first = next(rec for rec in recs if rec["stay_date"] == tomorrow.isoformat())
    accepted_price = first["recommended_price"]
    client.post(
        f"/api/recommendations/decision/{first['id']}",
        json={"decision": "accepted"},
        headers=headers,
    )

    r = client.post(f"/api/recommendations/{prop_id}/generate?days=7", headers=headers)
    assert r.status_code == 200
    assert len(r.json()) == 6  # zaakceptowany dzień pominięty

    all_recs = client.get(f"/api/recommendations/{prop_id}", headers=headers).json()
    assert len(all_recs) == 7  # bez duplikatów
    decided = next(rec for rec in all_recs if rec["stay_date"] == tomorrow.isoformat())
    assert decided["status"] == "accepted"
    assert Decimal(decided["recommended_price"]) == Decimal(accepted_price)


def test_recommendations_tenant_isolation(client, db_session):
    headers, prop_id, _ = _setup(client, db_session)
    client.post(f"/api/recommendations/{prop_id}/generate?days=3", headers=headers)

    headers_b = _register(client, "obcy@example.com")
    assert (
        client.post(
            f"/api/recommendations/{prop_id}/generate?days=3", headers=headers_b
        ).status_code
        == 404
    )
    assert client.get(f"/api/recommendations/{prop_id}", headers=headers_b).status_code == 404


def test_generate_requires_base_price(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    body = {**PROPERTY_BODY}
    del body["base_price"]
    prop_id = client.post("/api/properties", json=body, headers=headers).json()["id"]
    r = client.post(f"/api/recommendations/{prop_id}/generate", headers=headers)
    assert r.status_code == 422
    assert r.json()["detail"] == "base_price_required"
