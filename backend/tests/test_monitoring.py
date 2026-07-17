import datetime
from decimal import Decimal

from app.models import (
    CompetitorListing,
    CoverageLevel,
    Market,
    PriceObservation,
    PropertyType,
)
from app.monitoring import market_series, price_position, segment_medians, unit_category


def _market(db) -> Market:
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


def _listing(db, market, sid, unit_type=None) -> CompetitorListing:
    listing = CompetitorListing(
        market_id=market.id, source="booking", source_listing_id=sid, unit_type=unit_type
    )
    db.add(listing)
    db.flush()
    return listing


def test_unit_category_mapping():
    assert unit_category("Apartament typu Classic") == PropertyType.APARTMENT
    assert unit_category("Studio z aneksem") == PropertyType.APARTMENT
    assert unit_category("Pokój Dwuosobowy Superior") == PropertyType.ROOM
    assert unit_category("Domek letniskowy") == PropertyType.GUESTHOUSE
    assert unit_category(None) is None
    assert unit_category("Coś nietypowego") is None


def test_segment_medians_filters_by_type(db_session):
    market = _market(db_session)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    # 3 apartamenty (200/300/400) + 2 pokoje (100/120)
    for i, price in enumerate([200, 300, 400]):
        _obs(db_session, _listing(db_session, market, f"apt{i}", "Apartament typu X"),
             tomorrow, Decimal(str(price)))
    for i, price in enumerate([100, 120]):
        _obs(db_session, _listing(db_session, market, f"room{i}", "Pokój Dwuosobowy"),
             tomorrow, Decimal(str(price)))
    db_session.commit()

    seg = segment_medians(db_session, market, PropertyType.APARTMENT, days=1)
    median, sample = seg[tomorrow]
    assert median == Decimal("300")  # mediana z 200/300/400, bez pokoi
    assert sample == 3


def _obs(db, listing, stay_date, price, available=True, hours=0):
    db.add(
        PriceObservation(
            listing_id=listing.id,
            stay_date=stay_date,
            price=price,
            currency_code="PLN",
            available=available,
            observed_at=datetime.datetime(2026, 7, 16, hours, 0, tzinfo=datetime.UTC),
            source="booking",
        )
    )


def _obs_run(db, listing, stay_date, available, run_date):
    """Obserwacja w konkretnym przebiegu scrapera (run_date) — pod booking pace."""
    db.add(
        PriceObservation(
            listing_id=listing.id,
            stay_date=stay_date,
            price=Decimal("300") if available else None,
            currency_code="PLN",
            available=available,
            observed_at=datetime.datetime.combine(
                run_date, datetime.time(2, 0), tzinfo=datetime.UTC
            ),
            source="booking",
        )
    )


def test_booking_pace_from_two_runs(db_session):
    market = _market(db_session)
    stay = datetime.date.today() + datetime.timedelta(days=20)
    listings = [_listing(db_session, market, f"pl/{i}") for i in range(6)]
    run1 = datetime.date(2026, 7, 10)
    run2 = datetime.date(2026, 7, 15)
    # przebieg 1: 1/6 zajęte (~17%); przebieg 2: 4/6 zajęte (~67%) -> pace ~ +0.50
    for i, listing in enumerate(listings):
        _obs_run(db_session, listing, stay, available=(i >= 1), run_date=run1)
        _obs_run(db_session, listing, stay, available=(i >= 4), run_date=run2)
    db_session.commit()

    day = next(d for d in market_series(db_session, market, days=30) if d.stay_date == stay)
    assert day.booking_pace is not None
    assert round(day.booking_pace, 2) == 0.50


def test_booking_pace_none_with_single_run(db_session):
    market = _market(db_session)
    stay = datetime.date.today() + datetime.timedelta(days=20)
    listings = [_listing(db_session, market, f"pl/{i}") for i in range(6)]
    for listing in listings:
        _obs_run(db_session, listing, stay, available=True, run_date=datetime.date(2026, 7, 15))
    db_session.commit()
    day = next(d for d in market_series(db_session, market, days=30) if d.stay_date == stay)
    assert day.booking_pace is None


def test_market_series_median_uses_latest_observation_per_listing(db_session):
    market = _market(db_session)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    l1 = _listing(db_session, market, "pl/a")
    l2 = _listing(db_session, market, "pl/b")
    l3 = _listing(db_session, market, "pl/c")
    # l1: stara obserwacja 100, nowsza 300 — liczy się 300
    _obs(db_session, l1, tomorrow, Decimal("100"), hours=1)
    _obs(db_session, l1, tomorrow, Decimal("300"), hours=5)
    _obs(db_session, l2, tomorrow, Decimal("200"), hours=1)
    _obs(db_session, l3, tomorrow, Decimal("400"), hours=1)
    db_session.commit()

    series = market_series(db_session, market, days=1)
    assert len(series) == 1
    day = series[0]
    assert day.stay_date == tomorrow
    assert day.median_price == Decimal("300")
    assert day.sample_size == 3
    assert day.occupancy is None  # brak danych o niedostępności


def test_market_series_occupancy_from_unavailable_rows(db_session):
    market = _market(db_session)
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    l1 = _listing(db_session, market, "pl/a")
    l2 = _listing(db_session, market, "pl/b")
    l3 = _listing(db_session, market, "pl/c")
    l4 = _listing(db_session, market, "pl/d")
    _obs(db_session, l1, tomorrow, Decimal("100"))
    _obs(db_session, l2, tomorrow, Decimal("200"))
    _obs(db_session, l3, tomorrow, Decimal("300"))
    _obs(db_session, l4, tomorrow, None, available=False)
    db_session.commit()

    day = market_series(db_session, market, days=1)[0]
    assert day.sample_size == 3
    assert day.occupancy == 0.25
    assert day.median_price == Decimal("200")


def test_market_series_empty_market(db_session):
    market = _market(db_session)
    series = market_series(db_session, market, days=3)
    assert len(series) == 3
    assert all(d.median_price is None and d.sample_size == 0 for d in series)


def test_price_position():
    assert price_position(Decimal("170"), Decimal("200")) == -0.15
    assert price_position(Decimal("220"), Decimal("200")) == 0.1
