"""Kontrola jakości danych po przebiegu (ochrona przed cichą degradacją)."""

import datetime
from decimal import Decimal

from app.data_quality import DROP_THRESHOLD, MIN_BASELINE, find_quality_issues
from app.models import CompetitorListing, CoverageLevel, Market, PriceObservation

NOW = datetime.datetime(2026, 7, 19, 6, 0, tzinfo=datetime.UTC)


def _make_market(db, slug: str) -> Market:
    market = Market(
        slug=slug,
        name=slug.capitalize(),
        country_code="PL",
        currency_code="PLN",
        timezone="Europe/Warsaw",
        language="pl",
        coverage_level=CoverageLevel.RECOMMENDATIONS,
        center_lat=Decimal("52.0"),
        center_lng=Decimal("19.0"),
        radius_km=Decimal("8.0"),
        active_sources=["booking"],
    )
    db.add(market)
    db.commit()
    return market


def _add_observations(db, market: Market, observed_at: datetime.datetime, count: int) -> None:
    listing = CompetitorListing(
        market_id=market.id,
        source="booking",
        source_listing_id=f"pl/{market.slug}-{observed_at:%d%H}",
    )
    db.add(listing)
    db.flush()
    for i in range(count):
        db.add(
            PriceObservation(
                listing_id=listing.id,
                stay_date=datetime.date(2026, 7, 20) + datetime.timedelta(days=i % 30),
                price=Decimal("200"),
                currency_code="PLN",
                available=True,
                observed_at=observed_at,
                source="booking",
            )
        )
    db.commit()


def test_detects_volume_drop(db_session):
    market = _make_market(db_session, "karpacz")
    _add_observations(db_session, market, NOW - datetime.timedelta(hours=30), 200)
    _add_observations(db_session, market, NOW - datetime.timedelta(hours=3), 40)

    issues = find_quality_issues(db_session, NOW)
    assert len(issues) == 1
    assert issues[0].market_slug == "karpacz"
    assert issues[0].previous == 200
    assert issues[0].current == 40
    assert issues[0].drop_pct == 80


def test_detects_total_silence(db_session):
    """Scenariusz 2026-07-19: przebieg padł w całości — zero nowych obserwacji."""
    market = _make_market(db_session, "gorzow")
    _add_observations(db_session, market, NOW - datetime.timedelta(hours=30), MIN_BASELINE)

    issues = find_quality_issues(db_session, NOW)
    assert len(issues) == 1
    assert issues[0].current == 0
    assert issues[0].drop_pct == 100


def test_ignores_small_baseline_and_stable_markets(db_session):
    fresh = _make_market(db_session, "nowy-rynek")
    _add_observations(db_session, fresh, NOW - datetime.timedelta(hours=30), MIN_BASELINE - 1)
    # świeży rynek bez danych dziś — poniżej bazy, nie alarmujemy

    stable = _make_market(db_session, "stabilny")
    _add_observations(db_session, stable, NOW - datetime.timedelta(hours=30), 200)
    kept = int(200 * DROP_THRESHOLD) + 1  # tuż nad progiem
    _add_observations(db_session, stable, NOW - datetime.timedelta(hours=3), kept)

    assert find_quality_issues(db_session, NOW) == []
