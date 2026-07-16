from decimal import Decimal

from sqlalchemy import select

from app.models import CoverageLevel, FloorSignal, Market
from app.scraping.base import FloorListing
from app.scraping.nocowanie import (
    name_from_href,
    parse_center_distance_km,
    parse_from_price,
)
from app.scraping.runner import scrape_market_floor

# Realny headless-format karty (nocowanie.pl, Poznań, 2026-07-16).
CARD_TEXT = (
    "Natychmiastowa rezerwacja\nHotel Cezamet Poznań\n8.0\nBardzo dobry\n6 opinii\n"
    "Pokój 2-osobowy\n18 m2\nBez przedpłaty\n185 zł\nza 1 noc, 2 osoby\nZobacz dostępność"
)
# Karta promocyjna: dwie ceny, właściwa to finalna (169) przed "za N noc".
CARD_DISCOUNT = "-15%\n199 zł\n169 zł\nza 1 noc, 2 osoby"


def test_parse_from_price_takes_price_before_za_noc():
    # Bierze 185 (cena), NIE ocenę 8.0 ani "6 opinii"
    assert parse_from_price(CARD_TEXT) == Decimal("185")
    assert parse_from_price("1 250 zł za 1 noc") == Decimal("1250")
    assert parse_from_price("brak ceny") is None


def test_parse_from_price_discount_takes_final():
    assert parse_from_price(CARD_DISCOUNT) == Decimal("169")


def test_parse_center_distance():
    assert parse_center_distance_km("5,0 km od centrum") == Decimal("5.0")
    assert parse_center_distance_km(CARD_TEXT) is None  # headless nie pokazuje dystansu


def test_name_from_href():
    assert name_from_href("/rezerwuj/1573271-hotel-cezamet-poznan/") == "Hotel Cezamet Poznan"
    assert name_from_href("/inne/1573271/") is None


class _FakeNocowanie:
    source = "nocowanie"

    def __init__(self, prices):
        self._prices = prices

    def fetch_floor(self, market):
        return [
            FloorListing(source_listing_id=str(i), from_price=Decimal(str(p)),
                         currency_code="PLN")
            for i, p in enumerate(self._prices)
        ]


def _market(db) -> Market:
    market = Market(
        slug="poznan", name="Poznań", country_code="PL", currency_code="PLN",
        timezone="Europe/Warsaw", language="pl",
        coverage_level=CoverageLevel.RECOMMENDATIONS,
        center_lat=Decimal("52.4064"), center_lng=Decimal("16.9252"), radius_km=Decimal("12.0"),
    )
    db.add(market)
    db.commit()
    return market


def test_scrape_market_floor_stores_min_and_median(db_session):
    market = _market(db_session)
    count = scrape_market_floor(db_session, market, _FakeNocowanie([185, 240, 300, 500]))
    assert count == 4
    signal = db_session.scalar(select(FloorSignal))
    assert signal.source == "nocowanie"
    assert signal.min_price == Decimal("185")
    assert signal.median_price == Decimal("270")  # mediana 240,300 -> 270
    assert signal.sample_size == 4
    assert signal.currency_code == "PLN"


def test_scrape_market_floor_empty_sample_stores_nothing(db_session):
    market = _market(db_session)
    assert scrape_market_floor(db_session, market, _FakeNocowanie([])) == 0
    assert db_session.scalar(select(FloorSignal)) is None
