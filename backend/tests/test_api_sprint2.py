import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import CoverageLevel, Market, User


def _seed_market(db) -> Market:
    market = Market(
        slug="poznan",
        name="Poznań",
        country_code="PL",
        currency_code="PLN",
        timezone="Europe/Warsaw",
        language="pl",
        coverage_level=CoverageLevel.RECOMMENDATIONS,
        center_lat=Decimal("52.4064"),
        center_lng=Decimal("16.9252"),
        radius_km=Decimal("12.0"),
    )
    db.add(market)
    db.commit()
    return market


def _register(client, email="gospodarz@example.com") -> dict:
    r = client.post(
        "/api/auth/register",
        json={"account_name": "Test", "email": email, "password": "bardzo-tajne-haslo"},
    )
    assert r.status_code == 201
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


PROPERTY_BODY = {
    "market_slug": "poznan",
    "name": "Apartament Stary Rynek",
    "property_type": "apartment",
    "lat": 52.408,
    "lng": 16.933,
    "capacity": 4,
    "base_price": 250,
    "min_price": 150,
}


def test_property_create_and_tenant_isolation(client, db_session):
    _seed_market(db_session)
    headers_a = _register(client, "a@example.com")
    headers_b = _register(client, "b@example.com")

    r = client.post("/api/properties", json=PROPERTY_BODY, headers=headers_a)
    assert r.status_code == 201
    prop_id = r.json()["id"]
    assert r.json()["currency_code"] == "PLN"  # waluta z rynku, nie z założenia

    assert len(client.get("/api/properties", headers=headers_a).json()) == 1
    assert client.get("/api/properties", headers=headers_b).json() == []

    # monitoring cudzego obiektu = 404, nie 403 (nie zdradzamy istnienia)
    r = client.get(f"/api/monitoring/property/{prop_id}", headers=headers_b)
    assert r.status_code == 404


def test_curation_requires_curator_flag(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    event_body = {
        "market_slug": "poznan",
        "name": "Testowe targi",
        "category": "targi",
        "start_date": "2026-10-09",
        "end_date": "2026-10-11",
        "impact_strength": 0.7,
        "source": "kurator",
    }
    assert client.post("/api/curation/events", json=event_body, headers=headers).status_code == 403

    user = db_session.scalar(select(User))
    user.is_curator = True
    db_session.commit()

    r = client.post("/api/curation/events", json=event_body, headers=headers)
    assert r.status_code == 201
    assert r.json()["curation_status"] == "draft"


def test_clients_see_only_approved_upcoming_events(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    user = db_session.scalar(select(User))
    user.is_curator = True
    db_session.commit()

    future = (datetime.date.today() + datetime.timedelta(days=30)).isoformat()
    body = {
        "market_slug": "poznan",
        "name": "Majówka testowa",
        "category": "dlugi-weekend",
        "start_date": future,
        "end_date": future,
        "impact_strength": 0.9,
        "source": "kurator",
    }
    r = client.post("/api/curation/events", json=body, headers=headers)
    event_id = r.json()["id"]

    assert client.get("/api/events/poznan", headers=headers).json() == []

    r = client.patch(
        f"/api/curation/events/{event_id}",
        json={"curation_status": "approved"},
        headers=headers,
    )
    assert r.status_code == 200

    events = client.get("/api/events/poznan", headers=headers).json()
    assert len(events) == 1
    assert events[0]["name"] == "Majówka testowa"


def test_property_monitoring_includes_price_position(client, db_session):
    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    from tests.test_monitoring import _listing, _obs

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    listing = _listing(db_session, market, "pl/a")
    _obs(db_session, listing, tomorrow, Decimal("200"))
    db_session.commit()

    r = client.get(f"/api/monitoring/property/{prop_id}?days=1", headers=headers)
    assert r.status_code == 200
    day = r.json()["days"][0]
    assert Decimal(day["median_price"]) == Decimal("200")
    assert day["price_position"] == 0.25  # base 250 vs mediana 200


def test_property_monitoring_comp_set_segment(client, db_session):
    """A2: 'obiekty jak Twój' = mediana konkurentów tego samego typu (apartment)."""
    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    from tests.test_monitoring import _listing, _obs

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    for i, price in enumerate([300, 400, 500, 600, 700]):  # 5 apartamentów
        _obs(db_session, _listing(db_session, market, f"apt{i}", "Apartament"),
             tomorrow, Decimal(str(price)))
    for i, price in enumerate([100, 120]):  # pokoje — inny segment, poza comp setem
        _obs(db_session, _listing(db_session, market, f"room{i}", "Pokój"),
             tomorrow, Decimal(str(price)))
    db_session.commit()

    resp = client.get(f"/api/monitoring/property/{prop_id}?days=1", headers=headers)
    day = resp.json()["days"][0]
    assert Decimal(day["segment_median"]) == Decimal("500")  # mediana apartamentów, bez pokoi
    assert day["segment_sample"] == 5


def test_property_monitoring_comp_set_none_below_min_sample(client, db_session):
    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    from tests.test_monitoring import _listing, _obs

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    for i, price in enumerate([300, 400, 500, 600]):  # 4 < SEGMENT_MIN_SAMPLE
        _obs(db_session, _listing(db_session, market, f"apt{i}", "Apartament"),
             tomorrow, Decimal(str(price)))
    db_session.commit()

    resp = client.get(f"/api/monitoring/property/{prop_id}?days=1", headers=headers)
    day = resp.json()["days"][0]
    assert day["segment_median"] is None  # za mała próbka segmentu
    assert day["segment_sample"] is None


def test_monitoring_response_floor_spread(client, db_session):
    """A7: najtańszy dostępny (floor) + mediana floor w odpowiedzi rynkowej."""
    from app.models import FloorSignal

    market = _seed_market(db_session)
    headers = _register(client)
    db_session.add(
        FloorSignal(
            market_id=market.id,
            source="nocowanie",
            min_price=Decimal("150"),
            median_price=Decimal("240"),
            sample_size=12,
            currency_code="PLN",
            observed_at=datetime.datetime(2026, 7, 16, tzinfo=datetime.UTC),
        )
    )
    db_session.commit()

    body = client.get(f"/api/monitoring/market/{market.slug}?days=1", headers=headers).json()
    assert Decimal(body["floor_min"]) == Decimal("150")
    assert Decimal(body["floor_median"]) == Decimal("240")


def test_monitoring_response_floor_none_without_signal(client, db_session):
    market = _seed_market(db_session)
    headers = _register(client)
    body = client.get(f"/api/monitoring/market/{market.slug}?days=1", headers=headers).json()
    assert body["floor_min"] is None
    assert body["floor_median"] is None


def test_monitoring_response_supply_and_trend(client, db_session):
    """A5: najnowsza podaż + poprzednia migawka (trend) w odpowiedzi rynkowej."""
    from app.models import MarketSupply

    market = _seed_market(db_session)
    headers = _register(client)
    db_session.add_all([
        MarketSupply(market_id=market.id, source="booking", total_listings=500,
                     observed_at=datetime.datetime(2026, 7, 15, tzinfo=datetime.UTC)),
        MarketSupply(market_id=market.id, source="booking", total_listings=560,
                     observed_at=datetime.datetime(2026, 7, 16, tzinfo=datetime.UTC)),
    ])
    db_session.commit()

    body = client.get(f"/api/monitoring/market/{market.slug}?days=1", headers=headers).json()
    assert body["supply_total"] == 560  # najnowsza migawka
    assert body["supply_previous"] == 500  # poprzednia -> trend +12%
