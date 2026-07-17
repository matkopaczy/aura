import datetime
from decimal import Decimal

from app.monitoring import occupancy_by_ring, occupancy_map
from tests.test_monitoring import _listing, _market, _obs

TOMORROW = datetime.date.today() + datetime.timedelta(days=1)


def _ring_listing(db, market, sid, distance_km):
    listing = _listing(db, market, sid)
    listing.distance_center_km = Decimal(str(distance_km))
    return listing


def test_occupancy_by_ring_groups_by_distance(db_session):
    market = _market(db_session)
    # 0-1 km: 2 obiekty, 1 zajęty; 1-3 km: 2 obiekty, 2 zajęte; 6+: 1 wolny
    _obs(db_session, _ring_listing(db_session, market, "c1", 0.4), TOMORROW, Decimal("300"))
    _obs(db_session, _ring_listing(db_session, market, "c2", 0.8), TOMORROW, None, available=False)
    _obs(db_session, _ring_listing(db_session, market, "m1", 1.5), TOMORROW, None, available=False)
    _obs(db_session, _ring_listing(db_session, market, "m2", 2.9), TOMORROW, None, available=False)
    _obs(db_session, _ring_listing(db_session, market, "far", 8.0), TOMORROW, Decimal("200"))
    db_session.commit()

    rings = {r.ring: r for r in occupancy_by_ring(db_session, market)}
    assert rings["0-1"].occupancy == 0.5
    assert rings["0-1"].listings == 2
    assert rings["1-3"].occupancy == 1.0
    # 0 niedostępnych = może skan niewyczerpujący -> None, nie "0%"
    assert rings["6+"].occupancy is None
    assert rings["6+"].listings == 1
    assert rings["3-6"].listings == 0


def test_occupancy_by_ring_skips_listings_without_distance(db_session):
    market = _market(db_session)
    _obs(db_session, _listing(db_session, market, "nodist"), TOMORROW, None, available=False)
    db_session.commit()
    assert all(r.listings == 0 for r in occupancy_by_ring(db_session, market))


def test_occupancy_map_averages_market(db_session):
    market = _market(db_session)
    day2 = TOMORROW + datetime.timedelta(days=1)
    # dzień 1: 1/2 zajęte (0.5); dzień 2: 1/1 zajęte (1.0) -> średnia 0.75
    a = _listing(db_session, market, "a")
    b = _listing(db_session, market, "b")
    _obs(db_session, a, TOMORROW, Decimal("300"))
    _obs(db_session, b, TOMORROW, None, available=False)
    _obs(db_session, a, day2, None, available=False)
    db_session.commit()

    points = occupancy_map(db_session)
    assert len(points) == 1
    point = points[0]
    assert point.slug == "poznan"
    assert point.center_lat == 52.4064
    assert point.occupancy == 0.75


def test_public_occupancy_endpoint(client, db_session):
    _market(db_session)
    r = client.get("/api/public/occupancy")
    assert r.status_code == 200
    body = r.json()
    assert body[0]["slug"] == "poznan"
    assert body[0]["occupancy"] is None  # brak obserwacji = brak danych


def test_property_rings_endpoint(client, db_session):
    from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market

    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]
    _obs(db_session, _ring_listing(db_session, market, "r1", 0.5), TOMORROW, None, available=False)
    db_session.commit()

    r = client.get(f"/api/monitoring/property/{prop_id}/rings", headers=headers)
    assert r.status_code == 200
    rings = {row["ring"]: row for row in r.json()}
    assert rings["0-1"]["occupancy"] == 1.0
    assert rings["0-1"]["listings"] == 1
