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

    with Session(get_engine()) as db:
        market = db.get(Market, market_id)
        if market is None:
            raise ValueError(f"Rynek {market_id} nie istnieje")
        count = scrape_market(db, market)
        logger.info("Zakończono scraping %s: %d obserwacji", market.slug, count)


def run_ical_sync() -> None:
    from sqlalchemy.orm import Session

    with Session(get_engine()) as db:
        properties = db.scalars(select(Property).where(Property.ical_url.is_not(None))).all()
        for prop in properties:
            sync_property_calendar(db, prop)
        logger.info("Zakończono synchronizację iCal: %d obiektów", len(properties))


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
    return scheduler


if __name__ == "__main__":
    build_scheduler().start()
