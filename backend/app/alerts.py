"""Alerty ad hoc (§8.2): tylko zdarzenia pilne.

v1: skokowa zmiana mediany cen rynku dzień do dnia. Porównujemy medianę
z najnowszego przebiegu scrapera z medianą z poprzedniego przebiegu
(po dacie obserwacji). Alert idzie do kont z obiektami na danym rynku.
"""

import datetime
import logging
import statistics
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.emails import send_email
from app.i18n import t
from app.models import (
    CompetitorListing,
    Market,
    PriceObservation,
    Property,
    ReportKind,
    ReportSent,
    User,
)

logger = logging.getLogger(__name__)

SPIKE_THRESHOLD = 0.20
HORIZON_DAYS = 30


@dataclass(frozen=True)
class PriceSpike:
    stay_date: datetime.date
    old_median: Decimal
    new_median: Decimal

    @property
    def change_pct(self) -> int:
        return round((float(self.new_median) - float(self.old_median))
                     / float(self.old_median) * 100)


def detect_price_spikes(db: Session, market: Market) -> list[PriceSpike]:
    today = datetime.date.today()
    rows = db.execute(
        select(
            PriceObservation.listing_id,
            PriceObservation.stay_date,
            PriceObservation.price,
            PriceObservation.observed_at,
        )
        .join(CompetitorListing, CompetitorListing.id == PriceObservation.listing_id)
        .where(
            CompetitorListing.market_id == market.id,
            PriceObservation.available.is_(True),
            PriceObservation.guests == 2,  # alert o skokach cen z głównego skanu
            PriceObservation.stay_date >= today,
            PriceObservation.stay_date <= today + datetime.timedelta(days=HORIZON_DAYS),
        )
    ).all()

    # Grupujemy obserwacje po dacie przebiegu scrapera (dzień obserwacji).
    by_stay_and_run: dict[datetime.date, dict[datetime.date, dict]] = {}
    for listing_id, stay_date, price, observed_at in rows:
        runs = by_stay_and_run.setdefault(stay_date, {})
        run = runs.setdefault(observed_at.date(), {})
        # najnowsza obserwacja listingu w ramach przebiegu
        if listing_id not in run or observed_at > run[listing_id][1]:
            run[listing_id] = (price, observed_at)

    spikes = []
    for stay_date, runs in by_stay_and_run.items():
        if len(runs) < 2:
            continue
        run_dates = sorted(runs)
        latest, previous = runs[run_dates[-1]], runs[run_dates[-2]]
        new_prices = [float(p) for p, _ in latest.values() if p is not None]
        old_prices = [float(p) for p, _ in previous.values() if p is not None]
        if not new_prices or not old_prices:
            continue
        old_median = Decimal(str(statistics.median(old_prices)))
        new_median = Decimal(str(statistics.median(new_prices)))
        if old_median == 0:
            continue
        change = abs(float(new_median - old_median)) / float(old_median)
        if change >= SPIKE_THRESHOLD:
            spikes.append(PriceSpike(stay_date, old_median, new_median))
    return sorted(spikes, key=lambda s: s.stay_date)


def send_spike_alerts(db: Session, market: Market) -> int:
    spikes = detect_price_spikes(db, market)
    if not spikes:
        return 0
    top = spikes[0]
    users = db.scalars(
        select(User)
        .join(Property, Property.account_id == User.account_id)
        .where(Property.market_id == market.id, User.is_active.is_(True))
        .distinct()
    ).all()
    for user in users:
        subject = t("email.alert.subject", locale=user.locale, market=market.name)
        body = t(
            "email.alert.body",
            locale=user.locale,
            date=top.stay_date.isoformat(),
            pct=top.change_pct,
            old=top.old_median,
            new=top.new_median,
            url=get_settings().dashboard_url,
        )
        send_email(user.email, subject, body)
        db.add(
            ReportSent(
                account_id=user.account_id,
                kind=ReportKind.ALERT,
                sent_at=datetime.datetime.now(datetime.UTC),
                meta={"market": market.slug, "stay_date": top.stay_date.isoformat(),
                      "change_pct": top.change_pct},
            )
        )
    db.commit()
    logger.info("Alert cenowy %s: %d skoków, %d maili", market.slug, len(spikes), len(users))
    return len(users)
