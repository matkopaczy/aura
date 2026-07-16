import datetime
from decimal import Decimal

from sqlalchemy import select

from app.ical import busy_days_from_ical, is_orphan_night
from app.models import Account, CalendarDay, CoverageLevel, Market, Property, PropertyType


def test_is_orphan_night():
    d = datetime.date(2026, 8, 15)
    booked = {datetime.date(2026, 8, 14), datetime.date(2026, 8, 16)}
    assert is_orphan_night(d, booked) is True  # wolna, otoczona z obu stron
    # brak sąsiada z jednej strony -> nie sierota
    assert is_orphan_night(d, {datetime.date(2026, 8, 14)}) is False
    # sama zajęta -> nie sierota
    assert is_orphan_night(datetime.date(2026, 8, 14), booked) is False
    # wolna bez sąsiadów -> nie sierota
    assert is_orphan_night(d, set()) is False

AIRBNB_STYLE_ICAL = """BEGIN:VCALENDAR
PRODID:-//Airbnb Inc//Hosting Calendar 1.0//EN
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
DTSTAMP:20260716T120000Z
DTSTART;VALUE=DATE:20260810
DTEND;VALUE=DATE:20260813
UID:abc123@airbnb.com
SUMMARY:Reserved
END:VEVENT
BEGIN:VEVENT
DTSTAMP:20260716T120000Z
DTSTART;VALUE=DATE:20260901
DTEND;VALUE=DATE:20260902
UID:def456@airbnb.com
SUMMARY:Airbnb (Not available)
END:VEVENT
END:VCALENDAR
"""

ICAL_WITHOUT_SEPTEMBER = """BEGIN:VCALENDAR
PRODID:-//Airbnb Inc//Hosting Calendar 1.0//EN
CALSCALE:GREGORIAN
VERSION:2.0
BEGIN:VEVENT
DTSTAMP:20260716T120000Z
DTSTART;VALUE=DATE:20260810
DTEND;VALUE=DATE:20260813
UID:abc123@airbnb.com
SUMMARY:Reserved
END:VEVENT
END:VCALENDAR
"""


def test_busy_days_from_ical():
    busy = busy_days_from_ical(AIRBNB_STYLE_ICAL)
    # noce [DTSTART, DTEND): 10, 11, 12 sierpnia + 1 września
    assert busy == {
        datetime.date(2026, 8, 10),
        datetime.date(2026, 8, 11),
        datetime.date(2026, 8, 12),
        datetime.date(2026, 9, 1),
    }


def _make_property(db) -> Property:
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
    account = Account(name="Test")
    db.add_all([market, account])
    db.flush()
    prop = Property(
        account_id=account.id,
        market_id=market.id,
        name="Apartament Stary Rynek",
        property_type=PropertyType.APARTMENT,
        lat=Decimal("52.4080"),
        lng=Decimal("16.9330"),
        capacity=4,
        currency_code="PLN",
        min_price=Decimal("150"),
        ical_url="https://example.com/calendar.ics",
    )
    db.add(prop)
    db.commit()
    return prop


class _FakeResponse:
    def __init__(self, text: str):
        self.text = text

    def raise_for_status(self):
        pass


def test_sync_property_calendar_upserts_and_frees_days(db_session, monkeypatch):
    import app.ical as ical_module

    prop = _make_property(db_session)
    monkeypatch.setattr(
        ical_module.httpx, "get", lambda url, **kw: _FakeResponse(AIRBNB_STYLE_ICAL)
    )
    count = ical_module.sync_property_calendar(db_session, prop)
    assert count == 4
    days = set(db_session.scalars(select(CalendarDay.stay_date)))
    assert datetime.date(2026, 8, 10) in days
    assert len(days) == 4

    monkeypatch.setattr(
        ical_module.httpx, "get", lambda url, **kw: _FakeResponse(ICAL_WITHOUT_SEPTEMBER)
    )
    count = ical_module.sync_property_calendar(db_session, prop)
    assert count == 3
    days = set(db_session.scalars(select(CalendarDay.stay_date)))
    assert datetime.date(2026, 9, 1) not in days
    assert len(days) == 3
