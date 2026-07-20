import datetime
import uuid
from decimal import Decimal

from app.models import Booking, BookingChannel, Property
from app.models.base import utcnow
from app.performance import compute_performance
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market

TODAY = datetime.date(2026, 8, 1)


def _seed_night(db, prop, day, price):
    db.add(Booking(
        account_id=prop.account_id, property_id=prop.id, stay_date=day,
        nightly_price=Decimal(str(price)), currency_code="PLN",
        channel=BookingChannel.BOOKING, imported_at=utcnow(),
    ))


def _make_property(client, db):
    _seed_market(db)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]
    return headers, db.get(Property, uuid.UUID(prop_id))


def test_compute_performance_math(client, db_session):
    _, prop = _make_property(client, db_session)
    # 6 nocy w oknie: 200,200,200,300,300,300 = 1500
    for i, price in enumerate([200, 200, 200, 300, 300, 300]):
        _seed_night(db_session, prop, TODAY - datetime.timedelta(days=i + 1), price)
    # noc poza oknem (35 dni wstecz) i noc przyszła — pominięte
    _seed_night(db_session, prop, TODAY - datetime.timedelta(days=35), 999)
    _seed_night(db_session, prop, TODAY + datetime.timedelta(days=3), 999)
    db_session.commit()

    perf = compute_performance(db_session, prop, window_days=30, today=TODAY)
    assert perf.booked_nights == 6
    assert perf.adr == Decimal("250.00")  # 1500 / 6
    assert perf.occupancy == 6 / 30  # obłożenie kalendarzowe
    assert perf.revpar == Decimal("50.00")  # 1500 / 30


def test_compute_performance_no_bookings(client, db_session):
    _, prop = _make_property(client, db_session)
    perf = compute_performance(db_session, prop, window_days=30, today=TODAY)
    assert perf.booked_nights == 0
    assert perf.adr is None
    assert perf.revpar is None
    assert perf.occupancy == 0.0


def test_performance_endpoint_tenant_isolation(client, db_session):
    _seed_market(db_session)
    headers_a = _register(client, email="a@example.com")
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers_a).json()["id"]
    headers_b = _register(client, email="b@example.com")

    r = client.get(f"/api/monitoring/property/{prop_id}/performance", headers=headers_b)
    assert r.status_code == 404  # cudzy zasób = 404 (§6.2 pkt 1)
