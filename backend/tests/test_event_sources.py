import datetime
from decimal import Decimal

from sqlalchemy import select

from app.event_sources.base import CandidateEvent, EventSource
from app.event_sources.ingest import ingest_events
from app.event_sources.mtp import infer_dates, map_category, month_number, parse_cards
from app.models import CoverageLevel, CurationStatus, Event, Market

TODAY = datetime.date(2026, 7, 17)


def test_month_number():
    assert month_number("LIPCA") == 7
    assert month_number("Września") == 9
    assert month_number("grudnia") == 12
    assert month_number("cokolwiek") is None


def test_map_category():
    assert map_category("TARGI") == ("targi", 0.7)
    assert map_category("KONFERENCJE") == ("konferencje", 0.5)
    assert map_category("KONCERT") == ("koncert", 0.6)
    assert map_category("Nieznane") == ("eventy", 0.4)


def test_infer_dates_same_month():
    assert infer_dates(["08", "11"], ["WRZEŚNIA"], TODAY) == (
        datetime.date(2026, 9, 8), datetime.date(2026, 9, 11)
    )


def test_infer_dates_single_day():
    assert infer_dates(["17"], ["LIPCA"], TODAY) == (
        datetime.date(2026, 7, 17), datetime.date(2026, 7, 17)
    )


def test_infer_dates_past_month_rolls_to_next_year():
    # styczeń już minął w 2026 -> 2027
    assert infer_dates(["10"], ["stycznia"], TODAY) == (
        datetime.date(2027, 1, 10), datetime.date(2027, 1, 10)
    )


def test_infer_dates_spanning_year_boundary():
    assert infer_dates(["30", "02"], ["grudnia", "stycznia"], TODAY) == (
        datetime.date(2026, 12, 30), datetime.date(2027, 1, 2)
    )


def test_parse_cards_filters_non_poznan():
    cards = [
        {"title": "DREMA 2026", "cat": "TARGI", "days": ["08", "11"],
         "months": ["WRZEŚNIA"], "city": "Poznań"},
        {"title": "Coś w Warszawie", "cat": "TARGI", "days": ["01", "02"],
         "months": ["WRZEŚNIA"], "city": "Warszawa"},
        {"title": "", "cat": "TARGI", "days": ["05"], "months": ["LIPCA"], "city": "Poznań"},
    ]
    out = parse_cards(cards, TODAY)
    assert len(out) == 1
    assert out[0].name == "DREMA 2026"
    assert out[0].venue_lat == 52.3939
    assert out[0].impact_strength == 0.7


class _FakeSource(EventSource):
    source = "mtp"
    market_slug = "poznan"

    def fetch(self):
        return [
            CandidateEvent("DREMA 2026", "targi", datetime.date(2026, 9, 8),
                           datetime.date(2026, 9, 11), 0.7, 52.3939, 16.882, "Grunwald"),
        ]


def _poznan(db):
    m = Market(slug="poznan", name="Poznań", country_code="PL", currency_code="PLN",
               timezone="Europe/Warsaw", language="pl",
               coverage_level=CoverageLevel.RECOMMENDATIONS,
               center_lat=Decimal("52.4"), center_lng=Decimal("16.9"), radius_km=Decimal("12"))
    db.add(m)
    db.commit()
    return m


def test_ingest_creates_draft_with_venue_and_is_idempotent(db_session):
    _poznan(db_session)
    assert ingest_events(db_session, _FakeSource()) == 1
    ev = db_session.scalar(select(Event))
    assert ev.name == "DREMA 2026"
    assert ev.curation_status == CurationStatus.DRAFT
    assert ev.source == "mtp"
    assert ev.venue_lat == Decimal("52.393900")
    # drugie zasilanie nic nie dubluje
    assert ingest_events(db_session, _FakeSource()) == 0


def test_ingest_preserves_curator_decisions(db_session):
    market = _poznan(db_session)
    ingest_events(db_session, _FakeSource())
    ev = db_session.scalar(select(Event))
    ev.curation_status = CurationStatus.APPROVED  # kurator zatwierdził
    db_session.commit()
    # ponowne zasilanie NIE nadpisuje decyzji
    ingest_events(db_session, _FakeSource())
    ev2 = db_session.scalar(select(Event).where(Event.market_id == market.id))
    assert ev2.curation_status == CurationStatus.APPROVED
    assert db_session.scalar(select(Event).where(Event.name == "DREMA 2026")) is not None