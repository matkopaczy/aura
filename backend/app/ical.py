"""Import kalendarza klienta przez iCal (Airbnb/Booking, tylko odczyt — §6.4 pkt 1).

Każdy VEVENT traktujemy jako blokadę: noce [DTSTART, DTEND) są zajęte.
Synchronizacja podmienia stan w horyzoncie — dni bez wiersza są wolne.
"""

import datetime
import logging

import httpx
from icalendar import Calendar
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import CalendarDay, Property

logger = logging.getLogger(__name__)

SYNC_HORIZON_DAYS = 400


def busy_days_from_ical(ical_text: str) -> set[datetime.date]:
    calendar = Calendar.from_ical(ical_text)
    busy: set[datetime.date] = set()
    for event in calendar.walk("VEVENT"):
        start = event["DTSTART"].dt
        end = event["DTEND"].dt if "DTEND" in event else start + datetime.timedelta(days=1)
        if isinstance(start, datetime.datetime):
            start = start.date()
        if isinstance(end, datetime.datetime):
            end = end.date()
        day = start
        while day < end:
            busy.add(day)
            day += datetime.timedelta(days=1)
    return busy


def sync_property_calendar(db: Session, prop: Property) -> int:
    """Pobiera iCal obiektu i podmienia dni zajętości. Zwraca liczbę zajętych dni."""
    if not prop.ical_url:
        raise ValueError(f"Obiekt {prop.id} nie ma skonfigurowanego ical_url")

    response = httpx.get(prop.ical_url, timeout=30, follow_redirects=True)
    response.raise_for_status()

    today = datetime.date.today()
    horizon_end = today + datetime.timedelta(days=SYNC_HORIZON_DAYS)
    busy = {d for d in busy_days_from_ical(response.text) if today <= d < horizon_end}
    synced_at = datetime.datetime.now(datetime.UTC)

    existing = set(
        db.scalars(
            select(CalendarDay.stay_date).where(
                CalendarDay.property_id == prop.id,
                CalendarDay.stay_date >= today,
                CalendarDay.stay_date < horizon_end,
            )
        )
    )
    db.execute(
        delete(CalendarDay).where(
            CalendarDay.property_id == prop.id,
            CalendarDay.stay_date.in_(existing - busy),
        )
    )
    for day in busy - existing:
        db.add(
            CalendarDay(
                account_id=prop.account_id,
                property_id=prop.id,
                stay_date=day,
                synced_at=synced_at,
            )
        )
    db.commit()
    logger.info("property=%s zajęte=%d nowe=%d zwolnione=%d",
                prop.id, len(busy), len(busy - existing), len(existing - busy))
    return len(busy)
