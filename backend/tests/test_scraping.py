import datetime
from decimal import Decimal

from sqlalchemy import select

from app.models import CompetitorListing, CoverageLevel, Market, PriceObservation
from app.scraping.base import DayObservation, ObservedListing
from app.scraping.booking import (
    listing_id_from_href,
    parse_distance_km,
    parse_price,
    parse_rating,
    parse_results_total,
)
from app.scraping.runner import _store_day


def test_parse_price():
    assert parse_price("189 zł") == Decimal("189")
    assert parse_price("1 189 zł") == Decimal("1189")
    assert parse_price("od\xa02\xa0450\xa0zł") == Decimal("2450")
    assert parse_price("zł") is None


def test_parse_rating():
    assert parse_rating("Oceniony na 8,9\n8,9\nFantastyczny\n4 863 opinii") == Decimal("8.9")
    assert parse_rating("9.2") == Decimal("9.2")
    assert parse_rating("Nowy obiekt") is None


def test_parse_distance_km():
    assert parse_distance_km("0,6 km od centrum") == Decimal("0.6")
    assert parse_distance_km("650 m od centrum") == Decimal("0.65")
    assert parse_distance_km("bez odległości") is None


def test_listing_id_from_href():
    assert listing_id_from_href("https://www.booking.com/hotel/pl/altus.pl.html") == "pl/altus"
    assert listing_id_from_href("https://www.booking.com/inne/strony.html") is None


def test_parse_results_total():
    """Nagłówek wyników → łączna liczba obiektów; to podstawa flagi exhaustive
    (offset w URL jest ignorowany przez Booking, więc 'ostatnia strona <25'
    przestało być sygnałem końca wyników)."""
    assert parse_results_total("Karpacz: znaleziono 207 obiektów") == 207
    assert parse_results_total("Mielno: znaleziono 1 obiekt") == 1
    assert parse_results_total("Gdańsk: znaleziono 1\xa0234 obiekty") == 1234
    assert (
        parse_results_total("Znaleziono 64 obiekty w miejscu Gorzów Wielkopolski i okolicach")
        == 64
    )
    assert parse_results_total("Ładowanie wyników…") is None


class _FakeAdapter:
    source = "booking"


def _make_market(db) -> Market:
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
        active_sources=["booking"],
    )
    db.add(market)
    db.commit()
    return market


def _observation(listings: list[ObservedListing], exhaustive: bool = True) -> DayObservation:
    return DayObservation(
        stay_date=datetime.date(2026, 8, 10),
        observed_at=datetime.datetime(2026, 7, 16, 1, 0, tzinfo=datetime.UTC),
        listings=listings,
        exhaustive=exhaustive,
    )


def test_store_day_creates_listings_and_observations(db_session):
    market = _make_market(db_session)
    day = _observation(
        [
            ObservedListing(
                source_listing_id="pl/altus",
                price=Decimal("189"),
                currency_code="PLN",
                unit_type="Pokój Dwuosobowy",
                rating=Decimal("8.9"),
                distance_center_km=Decimal("0.6"),
            )
        ]
    )
    count = _store_day(db_session, market, _FakeAdapter(), day)
    db_session.commit()

    assert count == 1
    listing = db_session.scalar(select(CompetitorListing))
    assert listing.source_listing_id == "pl/altus"
    assert listing.market_id == market.id
    obs = db_session.scalar(select(PriceObservation))
    assert obs.price == Decimal("189")
    assert obs.available is True
    assert obs.currency_code == "PLN"


def test_store_day_marks_known_unseen_listing_unavailable(db_session):
    market = _make_market(db_session)
    day1 = _observation(
        [
            ObservedListing(
                source_listing_id="pl/altus", price=Decimal("189"), currency_code="PLN"
            ),
            ObservedListing(
                source_listing_id="pl/drugi", price=Decimal("240"), currency_code="PLN"
            ),
        ]
    )
    _store_day(db_session, market, _FakeAdapter(), day1)

    day2 = _observation(
        [
            ObservedListing(
                source_listing_id="pl/altus", price=Decimal("199"), currency_code="PLN"
            )
        ]
    )
    count = _store_day(db_session, market, _FakeAdapter(), day2)
    db_session.commit()

    assert count == 2  # 1 dostępny + 1 oznaczony jako niedostępny
    unavailable = db_session.scalars(
        select(PriceObservation).where(PriceObservation.available.is_(False))
    ).all()
    assert len(unavailable) == 1
    assert unavailable[0].price is None


def test_store_day_non_exhaustive_scan_never_marks_unavailable(db_session):
    market = _make_market(db_session)
    day1 = _observation(
        [
            ObservedListing(
                source_listing_id="pl/altus", price=Decimal("189"), currency_code="PLN"
            ),
            ObservedListing(
                source_listing_id="pl/drugi", price=Decimal("240"), currency_code="PLN"
            ),
        ]
    )
    _store_day(db_session, market, _FakeAdapter(), day1)

    # Skan częściowy: brak obiektu w wynikach to artefakt stronicowania,
    # nie wolno z niego wnioskować niedostępności.
    day2 = _observation(
        [
            ObservedListing(
                source_listing_id="pl/altus", price=Decimal("199"), currency_code="PLN"
            )
        ],
        exhaustive=False,
    )
    count = _store_day(db_session, market, _FakeAdapter(), day2)
    db_session.commit()

    assert count == 1  # tylko obserwacja dostępnego; zero wpisów o niedostępności
    unavailable = db_session.scalars(
        select(PriceObservation).where(PriceObservation.available.is_(False))
    ).all()
    assert unavailable == []


def test_pages_for_market_deeper_on_small_markets():
    """Małe rynki (promień <= 8 km) skanujemy głębiej — cel: skan wyczerpujący,
    bo tylko on pozwala liczyć obłożenie. Duże miasta zostają płytko (§6.4)."""
    from decimal import Decimal as D

    from app.models import CoverageLevel, Market
    from app.scraping.booking import BookingAdapter

    def _mk(radius):
        return Market(
            slug="x", name="X", country_code="PL", currency_code="PLN",
            timezone="Europe/Warsaw", language="pl",
            coverage_level=CoverageLevel.RECOMMENDATIONS,
            center_lat=D("50"), center_lng=D("20"), radius_km=D(str(radius)),
        )

    adapter = BookingAdapter.__new__(BookingAdapter)  # bez fetchowania robots
    adapter.pages_per_date = 2
    assert adapter.pages_for_market(_mk(6.0)) == 4   # kurort
    assert adapter.pages_for_market(_mk(8.0)) == 4   # granica włącznie
    assert adapter.pages_for_market(_mk(12.0)) == 2  # duże miasto
