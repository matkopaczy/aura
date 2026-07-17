"""Nocny harmonogram (§6.1: APScheduler, nie Airflow).

Uruchomienie: python -m app.scheduler
Scraping o 03:00 czasu lokalnego każdego rynku (praca nocna, §6.4);
synchronizacja iCal codziennie o 01:00 UTC (lekkie zapytania, po jednym per obiekt).
"""

import logging

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db import get_engine
from app.ical import sync_property_calendar
from app.models import Market, Property
from app.scraping.runner import scrape_market

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def run_market_scrape(market_id) -> None:
    from sqlalchemy.orm import Session

    from app.alerts import send_spike_alerts
    from app.config import get_settings
    from app.scraping.nocowanie import NocowanieAdapter
    from app.scraping.runner import scrape_market_floor

    with Session(get_engine()) as db:
        market = db.get(Market, market_id)
        if market is None:
            raise ValueError(f"Rynek {market_id} nie istnieje")
        count = scrape_market(db, market)
        logger.info("Zakończono scraping %s: %d obserwacji", market.slug, count)
        # Sygnał "minimum rynku" z nocowanie.pl (bezdatowy, §6.4) — best effort.
        try:
            scrape_market_floor(db, market, NocowanieAdapter())
        except Exception:  # floor to sygnał pomocniczy — nie wywala głównego przebiegu
            logger.exception("floor scrape nieudany dla %s", market.slug)
        if get_settings().smtp_host:
            send_spike_alerts(db, market)


def run_weekly_reports() -> None:
    from sqlalchemy.orm import Session

    from app.emails import send_weekly_reports

    with Session(get_engine()) as db:
        send_weekly_reports(db)


def run_attribution_update() -> None:
    from sqlalchemy.orm import Session

    from app.attribution import update_outcomes

    with Session(get_engine()) as db:
        properties = db.scalars(select(Property)).all()
        updated = sum(update_outcomes(db, prop) for prop in properties)
        logger.info("Atrybucja: zaktualizowano %d rekomendacji", updated)


def run_ical_sync() -> None:
    from sqlalchemy.orm import Session

    with Session(get_engine()) as db:
        properties = db.scalars(select(Property).where(Property.ical_url.is_not(None))).all()
        for prop in properties:
            sync_property_calendar(db, prop)
        logger.info("Zakończono synchronizację iCal: %d obiektów", len(properties))


def run_event_ingest() -> None:
    from app.event_sources.ingest import run

    run()  # zasila kandydatów na eventy z oficjalnych źródeł (DRAFT do kuracji)


def build_scheduler() -> BlockingScheduler:
    from sqlalchemy.orm import Session

    scheduler = BlockingScheduler(timezone="UTC")
    with Session(get_engine()) as db:
        markets = db.scalars(select(Market)).all()
    for market in markets:
        if not market.active_sources:
            continue
        scheduler.add_job(
            run_market_scrape,
            CronTrigger(hour=3, minute=0, timezone=market.timezone),
            args=[market.id],
            id=f"scrape:{market.slug}",
            misfire_grace_time=3600,
        )
    scheduler.add_job(
        run_ical_sync,
        CronTrigger(hour=1, minute=0, timezone="UTC"),
        id="ical-sync",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_attribution_update,
        CronTrigger(hour=5, minute=0, timezone="UTC"),
        id="attribution",
        misfire_grace_time=3600,
    )
    scheduler.add_job(
        run_weekly_reports,
        CronTrigger(day_of_week="mon", hour=7, minute=0, timezone="Europe/Warsaw"),
        id="weekly-reports",
        misfire_grace_time=3600,
    )
    # Eventy zmieniają się wolno — odświeżanie raz w tygodniu wystarcza.
    scheduler.add_job(
        run_event_ingest,
        CronTrigger(day_of_week="mon", hour=4, minute=0, timezone="Europe/Warsaw"),
        id="event-ingest",
        misfire_grace_time=3600,
    )
    return scheduler


if __name__ == "__main__":
    build_scheduler().start()
