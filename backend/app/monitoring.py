"""Serwis Monitoringu (§5.1): mediana rynku, obłożenie okolicy, pozycja ceny.

Mediana liczona w Pythonie z najnowszej obserwacji per (listing, data) —
przenośne między Postgresem a SQLite w testach, a wolumeny są małe
(dziesiątki listingów na rynek).
"""

import datetime
import statistics
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompetitorListing, Market, PriceObservation


@dataclass(frozen=True)
class MarketDay:
    stay_date: datetime.date
    median_price: Decimal | None  # None gdy brak próbki
    sample_size: int
    occupancy: float | None  # None gdy brak danych wyczerpujących (§ runner)


def market_series(db: Session, market: Market, days: int = 60) -> list[MarketDay]:
    today_local = datetime.datetime.now(ZoneInfo(market.timezone)).date()
    date_from = today_local + datetime.timedelta(days=1)
    date_to = today_local + datetime.timedelta(days=days)

    rows = db.execute(
        select(
            PriceObservation.listing_id,
            PriceObservation.stay_date,
            PriceObservation.price,
            PriceObservation.available,
            PriceObservation.observed_at,
        )
        .join(CompetitorListing, CompetitorListing.id == PriceObservation.listing_id)
        .where(
            CompetitorListing.market_id == market.id,
            PriceObservation.stay_date >= date_from,
            PriceObservation.stay_date <= date_to,
        )
    ).all()

    latest: dict[tuple, tuple] = {}
    for listing_id, stay_date, price, available, observed_at in rows:
        key = (listing_id, stay_date)
        if key not in latest or observed_at > latest[key][2]:
            latest[key] = (price, available, observed_at)

    by_date: dict[datetime.date, list[tuple]] = {}
    for (_, stay_date), value in latest.items():
        by_date.setdefault(stay_date, []).append(value)

    series = []
    for offset in range((date_to - date_from).days + 1):
        stay_date = date_from + datetime.timedelta(days=offset)
        observations = by_date.get(stay_date, [])
        prices = [price for price, available, _ in observations if available and price is not None]
        unavailable = sum(1 for _, available, _ in observations if not available)
        series.append(
            MarketDay(
                stay_date=stay_date,
                median_price=Decimal(statistics.median(prices)) if prices else None,
                sample_size=len(prices),
                occupancy=(
                    unavailable / len(observations) if unavailable and observations else None
                ),
            )
        )
    return series


def price_position(base_price: Decimal, median_price: Decimal) -> float:
    """Pozycja ceny klienta vs mediana: -0.15 = 15% poniżej mediany."""
    return float((base_price - median_price) / median_price)
