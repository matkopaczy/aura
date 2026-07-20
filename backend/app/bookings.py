"""Import zrealizowanych rezerwacji gospodarza z CSV (B, §3.4).

Czyste funkcje parsowania i rozwijania rezerwacji na noce — testowalne bez bazy.
Zapis (upsert per noc) w import_bookings. Cel: rzeczywista cena sprzedaży pod
prawdziwy ADR/RevPAR i uczciwy licznik wyniku.
"""

import csv
import datetime
import io
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, BookingChannel, Property
from app.models.base import utcnow

# Elastyczne dopasowanie nagłówków CSV (eksporty Booking/Airbnb różnią się nazwami).
_CHECKIN_KEYS = {"check_in", "checkin", "arrival", "start", "od", "zameldowanie"}
_CHECKOUT_KEYS = {"check_out", "checkout", "departure", "end", "do", "wymeldowanie"}
_PRICE_KEYS = {"price", "total", "amount", "payout", "cena", "kwota", "przychod"}
_CHANNEL_KEYS = {"channel", "source", "kanal", "zrodlo", "platform"}
_REF_KEYS = {"reservation_ref", "reference", "id", "booking_id", "numer", "ref"}


@dataclass(frozen=True)
class ParsedReservation:
    check_in: datetime.date
    check_out: datetime.date  # noc wymeldowania nie jest sprzedana (wyłącznie)
    total_price: Decimal
    channel: BookingChannel
    reservation_ref: str | None


def _pick(row: dict[str, str], keys: set[str]) -> str | None:
    for header, value in row.items():
        if header and header.strip().lower() in keys and value and value.strip():
            return value.strip()
    return None


def _parse_channel(raw: str | None) -> BookingChannel:
    if raw is None:
        return BookingChannel.OTHER
    t = raw.strip().lower()
    if "booking" in t:
        return BookingChannel.BOOKING
    if "airbnb" in t:
        return BookingChannel.AIRBNB
    if "direct" in t or "bezpo" in t:  # "bezpośrednia"
        return BookingChannel.DIRECT
    return BookingChannel.OTHER


def _parse_price(raw: str) -> Decimal:
    # "1 234,50 zł" / "1234.50" -> Decimal. Waluta obsługiwana osobno (kod rynku).
    cleaned = raw.replace(" ", "").replace("\xa0", "").replace("zł", "").replace(",", ".")
    return Decimal(cleaned)


def parse_bookings_csv(content: str) -> tuple[list[ParsedReservation], int]:
    """Parsuje CSV rezerwacji. Zwraca (rezerwacje, liczba pominiętych wierszy).

    Wiersz nieparsowalny (zła data/cena, checkout <= checkin) jest pomijany, nie
    wywala całego importu — bulk import gospodarza ma być odporny na pojedynczy
    śmieciowy wiersz (raportujemy ile pominięto).
    """
    reader = csv.DictReader(io.StringIO(content))
    reservations: list[ParsedReservation] = []
    skipped = 0
    for row in reader:
        check_in = _pick(row, _CHECKIN_KEYS)
        check_out = _pick(row, _CHECKOUT_KEYS)
        price = _pick(row, _PRICE_KEYS)
        if not (check_in and check_out and price):
            skipped += 1
            continue
        try:
            ci = datetime.date.fromisoformat(check_in)
            co = datetime.date.fromisoformat(check_out)
            total = _parse_price(price)
        except (ValueError, InvalidOperation):
            skipped += 1
            continue
        if co <= ci or total <= 0:
            skipped += 1
            continue
        reservations.append(
            ParsedReservation(
                check_in=ci,
                check_out=co,
                total_price=total,
                channel=_parse_channel(_pick(row, _CHANNEL_KEYS)),
                reservation_ref=_pick(row, _REF_KEYS),
            )
        )
    return reservations, skipped


def expand_to_nights(res: ParsedReservation) -> list[tuple[datetime.date, Decimal]]:
    """Rozwija rezerwację na noce z ceną nocną (B — DECYZJA produktowa).

    DOMYŚLNIE: podział RÓWNOMIERNY — cena całkowita / liczba nocy, każda noc
    tyle samo. To uczciwe przybliżenie na pilota (CSV zwykle nie ma rozbicia
    per noc). Zaokrąglenie do grosza; resztę groszy dokładamy do PIERWSZEJ nocy,
    żeby suma nocnych == cena całkowita (bez gubienia grosza, §6.2 pkt 3).

    Alternatywa (gdyby CSV niósł ceny per noc albo chciałbyś ważyć weekendy):
    podział ważony — zmiana tylko tutaj, reszta pipeline'u bez zmian.
    """
    nights = (res.check_out - res.check_in).days
    base = (res.total_price / nights).quantize(Decimal("0.01"))
    remainder = res.total_price - base * nights  # reszta groszy z zaokrąglenia
    result = []
    for i in range(nights):
        night_date = res.check_in + datetime.timedelta(days=i)
        price = base + remainder if i == 0 else base
        result.append((night_date, price))
    return result


def import_bookings(db: Session, prop: Property, reservations: list[ParsedReservation]) -> int:
    """Upsert rezerwacji per noc dla obiektu. Zwraca liczbę zapisanych nocy.

    Idempotentny: jedna noc = jeden wiersz (UniqueConstraint). Ponowny import
    tej samej nocy NADPISUJE (najnowszy CSV wygrywa) — bez duplikatów.
    """
    existing = {
        b.stay_date: b
        for b in db.scalars(
            select(Booking).where(Booking.property_id == prop.id)
        )
    }
    now = utcnow()
    written = 0
    for res in reservations:
        for stay_date, nightly in expand_to_nights(res):
            booking = existing.get(stay_date)
            if booking is None:
                booking = Booking(
                    account_id=prop.account_id,
                    property_id=prop.id,
                    stay_date=stay_date,
                )
                db.add(booking)
                existing[stay_date] = booking
            booking.nightly_price = nightly
            booking.currency_code = prop.currency_code
            booking.channel = res.channel
            booking.reservation_ref = res.reservation_ref
            booking.imported_at = now
            written += 1
    db.commit()
    return written
