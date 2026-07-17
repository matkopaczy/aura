"""Zapis kandydatów na eventy do bazy jako DRAFT (kurator zatwierdza)."""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.event_sources.base import EventSource
from app.models import CurationStatus, Event, Market

logger = logging.getLogger(__name__)


def ingest_events(db: Session, source: EventSource) -> int:
    """Dokłada nowe wydarzenia ze źródła jako DRAFT. Zwraca liczbę nowych.

    Idempotentne po (market, nazwa, data startu). Istniejących NIE nadpisujemy —
    decyzje kuratora (approved/rejected, skorygowana siła/venue) zostają nietknięte.
    """
    market = db.scalar(select(Market).where(Market.slug == source.market_slug))
    if market is None:
        raise ValueError(f"Rynek {source.market_slug} nie istnieje")

    existing = {
        (e.name, e.start_date)
        for e in db.scalars(select(Event).where(Event.market_id == market.id))
    }
    created = 0
    for cand in source.fetch():
        if (cand.name, cand.start_date) in existing:
            continue
        db.add(
            Event(
                market_id=market.id,
                name=cand.name,
                category=cand.category,
                district=cand.district,
                start_date=cand.start_date,
                end_date=cand.end_date,
                impact_strength=Decimal(str(cand.impact_strength)),
                source=source.source,
                curation_status=CurationStatus.DRAFT,
                venue_lat=Decimal(str(cand.venue_lat)) if cand.venue_lat is not None else None,
                venue_lng=Decimal(str(cand.venue_lng)) if cand.venue_lng is not None else None,
            )
        )
        created += 1
    db.commit()
    logger.info("Zasilanie eventów %s: %d nowych kandydatów (DRAFT)", source.source, created)
    return created


def run() -> None:
    """Wejście do crona/harmonogramu: zasila ze wszystkich źródeł eventów."""
    from sqlalchemy.orm import Session as _Session

    from app.db import get_engine
    from app.event_sources.mtp import MtpPoznanSource

    logging.basicConfig(level=logging.INFO)
    with _Session(get_engine()) as db:
        ingest_events(db, MtpPoznanSource())


if __name__ == "__main__":
    run()
