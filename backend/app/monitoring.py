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

from app.models import (
    CompetitorListing,
    FloorSignal,
    Market,
    PriceObservation,
    PropertyType,
)

# Segment min sample: poniżej tylu konkurentów tego samego typu wracamy do
# mediany całego rynku (bezpieczny fallback — nigdy nie pogarszamy §11).
SEGMENT_MIN_SAMPLE = 5


def unit_category(unit_type: str | None) -> PropertyType | None:
    """Mapuje wolnotekstowy unit_type konkurenta na gruby typ obiektu."""
    if not unit_type:
        return None
    t = unit_type.lower()
    if "apart" in t or "studio" in t or "mieszkan" in t:
        return PropertyType.APARTMENT
    if "pokój" in t or "pokoj" in t or "room" in t:
        return PropertyType.ROOM
    if "dom" in t or "willa" in t or "pensjonat" in t or "chata" in t:
        return PropertyType.GUESTHOUSE
    return None


def segment_medians(
    db: Session, market: Market, property_type: PropertyType, days: int = 60
) -> dict[datetime.date, tuple[Decimal, int]]:
    """Mediana cen konkurentów TEGO SAMEGO typu per data pobytu (median, próbka)."""
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
            CompetitorListing.unit_type,
        )
        .join(CompetitorListing, CompetitorListing.id == PriceObservation.listing_id)
        .where(
            CompetitorListing.market_id == market.id,
            PriceObservation.stay_date >= date_from,
            PriceObservation.stay_date <= date_to,
        )
    ).all()

    latest: dict[tuple, tuple] = {}  # (listing, date) -> (price, available, observed_at, type)
    for listing_id, stay_date, price, available, observed_at, unit_type in rows:
        key = (listing_id, stay_date)
        if key not in latest or observed_at > latest[key][2]:
            latest[key] = (price, available, observed_at, unit_category(unit_type))

    by_date: dict[datetime.date, list[Decimal]] = {}
    for (_, stay_date), (price, available, _, category) in latest.items():
        if available and price is not None and category == property_type:
            by_date.setdefault(stay_date, []).append(price)

    return {
        stay_date: (Decimal(statistics.median(prices)), len(prices))
        for stay_date, prices in by_date.items()
    }


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


# Pierścienie odległości od centrum (km) — przybliżona mapa obłożenia miasta
# bez współrzędnych obiektów (mamy tylko distance_center_km z wyników, §6.4).
DISTANCE_RINGS: list[tuple[float, float | None, str]] = [
    (0.0, 1.0, "0-1"),
    (1.0, 3.0, "1-3"),
    (3.0, 6.0, "3-6"),
    (6.0, None, "6+"),
]


@dataclass(frozen=True)
class RingOccupancy:
    ring: str  # etykieta pierścienia, np. "1-3"
    occupancy: float | None  # None gdy brak danych wyczerpujących (jak MarketDay)
    listings: int  # ile obiektów konkurencji w pierścieniu


def occupancy_by_ring(db: Session, market: Market, days: int = 30) -> list[RingOccupancy]:
    """Obłożenie okolicy wg odległości od centrum, zagregowane po horyzoncie."""
    today_local = datetime.datetime.now(ZoneInfo(market.timezone)).date()
    date_from = today_local + datetime.timedelta(days=1)
    date_to = today_local + datetime.timedelta(days=days)

    rows = db.execute(
        select(
            PriceObservation.listing_id,
            PriceObservation.stay_date,
            PriceObservation.available,
            PriceObservation.observed_at,
            CompetitorListing.distance_center_km,
        )
        .join(CompetitorListing, CompetitorListing.id == PriceObservation.listing_id)
        .where(
            CompetitorListing.market_id == market.id,
            CompetitorListing.distance_center_km.is_not(None),
            PriceObservation.stay_date >= date_from,
            PriceObservation.stay_date <= date_to,
        )
    ).all()

    latest: dict[tuple, tuple] = {}  # (listing, date) -> (available, observed_at, distance)
    for listing_id, stay_date, available, observed_at, distance in rows:
        key = (listing_id, stay_date)
        if key not in latest or observed_at > latest[key][1]:
            latest[key] = (available, observed_at, float(distance))

    result = []
    for low, high, label in DISTANCE_RINGS:
        in_ring = [
            (listing_id, available)
            for (listing_id, _), (available, _, distance) in latest.items()
            if distance >= low and (high is None or distance < high)
        ]
        unavailable = sum(1 for _, available in in_ring if not available)
        result.append(
            RingOccupancy(
                ring=label,
                # Jak w market_series: 0 niedostępnych może znaczyć "skan
                # niewyczerpujący", więc nie twierdzimy "0% obłożenia".
                occupancy=unavailable / len(in_ring) if unavailable and in_ring else None,
                listings=len({listing_id for listing_id, _ in in_ring}),
            )
        )
    return result


@dataclass(frozen=True)
class MarketOccupancy:
    slug: str
    name: str
    center_lat: float
    center_lng: float
    occupancy: float | None  # średnia z dni z danymi; None gdy brak


def occupancy_map(db: Session, days: int = 30) -> list[MarketOccupancy]:
    """Obłożenie wszystkich rynków — dane pod mapę Polski (landing, §5.1)."""
    result = []
    for market in db.scalars(select(Market).order_by(Market.name)):
        series = market_series(db, market, days=days)
        values = [d.occupancy for d in series if d.occupancy is not None]
        result.append(
            MarketOccupancy(
                slug=market.slug,
                name=market.name,
                center_lat=float(market.center_lat),
                center_lng=float(market.center_lng),
                occupancy=sum(values) / len(values) if values else None,
            )
        )
    return result
