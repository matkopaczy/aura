import datetime
from decimal import Decimal

from sqlalchemy import select

from app.bookings import expand_to_nights, parse_bookings_csv
from app.models import Booking, BookingChannel
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market

CSV = """check_in,check_out,price,channel,reference
2026-08-01,2026-08-04,600,Booking.com,RES-1
2026-08-10,2026-08-11,250,Airbnb,RES-2
zła-data,2026-08-12,100,Direct,RES-3
2026-08-20,2026-08-20,100,Direct,RES-4
"""


def test_expand_to_nights_uniform_split():
    res = parse_bookings_csv("check_in,check_out,price\n2026-08-01,2026-08-04,600\n")[0][0]
    nights = expand_to_nights(res)
    assert nights == [
        (datetime.date(2026, 8, 1), Decimal("200.00")),
        (datetime.date(2026, 8, 2), Decimal("200.00")),
        (datetime.date(2026, 8, 3), Decimal("200.00")),  # checkout 08-04 nie sprzedany
    ]


def test_expand_to_nights_penny_remainder_on_first():
    """Reszta z zaokrąglenia trafia na pierwszą noc — suma nocnych == cena całkowita."""
    res = parse_bookings_csv("check_in,check_out,price\n2026-08-01,2026-08-04,301\n")[0][0]
    nights = expand_to_nights(res)
    assert [p for _, p in nights] == [Decimal("100.34"), Decimal("100.33"), Decimal("100.33")]
    assert sum(p for _, p in nights) == Decimal("301.00")


def test_parse_bookings_csv_skips_bad_rows():
    reservations, skipped = parse_bookings_csv(CSV)
    assert len(reservations) == 2  # RES-1, RES-2
    assert skipped == 2  # zła data + checkout==checkin
    assert reservations[0].channel == BookingChannel.BOOKING
    assert reservations[1].channel == BookingChannel.AIRBNB
    assert reservations[0].reservation_ref == "RES-1"


def test_parse_polish_price_format():
    """Cena "1 200,50" (spacja tys. + przecinek dziesiętny) -> Decimal."""
    reservations, _ = parse_bookings_csv(
        "check_in,check_out,cena\n2026-08-01,2026-08-03,\"1 200,50\"\n"
    )
    assert reservations[0].total_price == Decimal("1200.50")


def _import(client, headers, prop_id, csv_text):
    return client.post(
        f"/api/properties/{prop_id}/bookings/import",
        headers={**headers, "Content-Type": "text/csv"},
        content=csv_text.encode("utf-8"),
    )


def test_import_endpoint_stores_nights(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    r = _import(client, headers, prop_id, CSV)
    assert r.status_code == 200
    body = r.json()
    assert body["reservations"] == 2
    assert body["skipped_rows"] == 2
    assert body["imported_nights"] == 4  # 3 noce (RES-1) + 1 noc (RES-2)

    nights = db_session.scalars(select(Booking).order_by(Booking.stay_date)).all()
    assert len(nights) == 4
    assert nights[0].stay_date == datetime.date(2026, 8, 1)
    assert nights[0].nightly_price == Decimal("200.00")
    assert nights[0].currency_code == "PLN"


def test_import_is_idempotent(client, db_session):
    _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]

    _import(client, headers, prop_id, CSV)
    _import(client, headers, prop_id, CSV)  # ten sam import drugi raz
    nights = db_session.scalars(select(Booking)).all()
    assert len(nights) == 4  # bez duplikatów (upsert per noc)


def test_import_tenant_isolation(client, db_session):
    _seed_market(db_session)
    headers_a = _register(client, email="a@example.com")
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers_a).json()["id"]
    headers_b = _register(client, email="b@example.com")

    r = _import(client, headers_b, prop_id, CSV)  # B importuje do obiektu A
    assert r.status_code == 404  # cudzy zasób = 404, nie 403 (§6.2 pkt 1)
