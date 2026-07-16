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

from app.models import CompetitorListing, FloorSignal, Market, PriceObservation


@dataclass(frozen=True)
class FloorView:
    source: str
    min_price: Decimal
    median_price: Decimal
    sample_size: int


def latest_floor(db: Session, market: Market) -> FloorView | None:
    """Najnowszy sygnał "minimum rynku" (nocowanie.pl) — None jeśli brak."""
    signal = db.scalar(
        select(FloorSignal)
        .where(FloorSignal.market_id == market.id)
        .order_by(FloorSignal.observed_at.desc())
        .limit(1)
    )
    if signal is None:
        return None
    return FloorView(
        source=signal.source,
        min_price=signal.min_price,
        median_price=signal.median_price,
        sample_size=signal.sample_size,
    )


# Booking pace: potrzebujemy ≥2 przebiegów scrapera i sensownej próbki, żeby
# porównywać obłożenie w czasie. Inaczej pace = None (jak occupancy).
PACE_MIN_SAMPLE = 5


@dataclass(frozen=True)
class MarketDay:
    stay_date: datetime.date
    median_price: Decimal | None  # None gdy brak próbki
    sample_size: int
    occupancy: float | None  # None gdy brak danych wyczerpujących (§ runner)
    # Tempo wypełniania rynku: zmiana obłożenia między dwoma ostatnimi przebiegami
    # scrapera (+0.15 = o 15 pkt proc. więcej rynku zajęte niż poprzednio). §7.2.
    booking_pace: float | None = None


def _run_occupancy(availabilities: list[bool]) -> float | None:
    """Odsetek niedostępnych w jednym przebiegu; None gdy próbka za mała."""
    if len(availabilities) < PACE_MIN_SAMPLE:
        return None
    return sum(1 for a in availabilities if not a) / len(availabilities)


def _booking_pace(runs: dict[datetime.date, dict]) -> float | None:
    """Zmiana obłożenia między dwoma ostatnimi przebiegami dla danej daty pobytu."""
    run_dates = sorted(runs)
    if len(run_dates) < 2:
        return None
    latest = _run_occupancy(list(runs[run_dates[-1]].values()))
    previous = _run_occupancy(list(runs[run_dates[-2]].values()))
    if latest is None or previous is None:
        return None
    return latest - previous


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
    # runs[stay_date][run_date][listing_id] = available — pod pace (§7.2)
    runs: dict[datetime.date, dict[datetime.date, dict]] = {}
    for listing_id, stay_date, price, available, observed_at in rows:
        key = (listing_id, stay_date)
        if key not in latest or observed_at > latest[key][2]:
            latest[key] = (price, available, observed_at)
        run = runs.setdefault(stay_date, {}).setdefault(observed_at.date(), {})
        run[listing_id] = available

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
                booking_pace=_booking_pace(runs.get(stay_date, {})),
            )
        )
    return series


def price_position(base_price: Decimal, median_price: Decimal) -> float:
    """Pozycja ceny klienta vs mediana: -0.15 = 15% poniżej mediany."""
    return float((base_price - median_price) / median_price)
