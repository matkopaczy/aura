import datetime
import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.models import CoverageLevel, Market, Property, PropertyType
from app.monitoring import (
    SEGMENT_MIN_SAMPLE,
    latest_floor,
    latest_supply,
    market_series,
    occupancy_by_ring,
    price_position,
    segment_medians,
)

router = APIRouter(prefix="/api", tags=["monitoring"])

DbSession = Annotated[Session, Depends(get_db)]


class MarketResponse(BaseModel):
    slug: str
    name: str
    currency_code: str
    coverage_level: CoverageLevel


class MonitoringDayResponse(BaseModel):
    stay_date: datetime.date
    median_price: Decimal | None
    sample_size: int
    occupancy: float | None
    price_position: float | None  # tylko w widoku obiektu
    # Rozkład cen konkurencji (A1) — widełki wokół mediany; None gdy mała próbka.
    price_p10: Decimal | None = None
    price_p25: Decimal | None = None
    price_p75: Decimal | None = None
    price_p90: Decimal | None = None
    # Comp set segmentowy (A2) — mediana konkurentów TEGO SAMEGO typu ("obiekty
    # jak Twój"); tylko w widoku obiektu i tylko gdy próbka >= SEGMENT_MIN_SAMPLE.
    segment_median: Decimal | None = None
    segment_sample: int | None = None
    # Tempo rynku (A4) — zmiana presji dostępności między przebiegami
    # (+0.15 = o 15 pkt proc. więcej rynku zajęte niż poprzednio). None gdy < 2 przebiegi.
    booking_pace: float | None = None


class MonitoringResponse(BaseModel):
    market_slug: str
    currency_code: str
    days: list[MonitoringDayResponse]
    # Spread floor–mediana (A7) — najtańszy dostępny w okolicy vs mediana rynku.
    # None gdy brak sygnału floor (nocowanie.pl).
    floor_min: Decimal | None = None
    floor_median: Decimal | None = None
    # Podaż rynku (A5) — liczba ofert (najnowsza migawka) + poprzednia (trend).
    supply_total: int | None = None
    supply_previous: int | None = None


@router.get("/markets", response_model=list[MarketResponse])
def list_markets(user: CurrentUser, db: DbSession) -> list[MarketResponse]:
    markets = db.scalars(select(Market).order_by(Market.name)).all()
    return [
        MarketResponse(
            slug=m.slug,
            name=m.name,
            currency_code=m.currency_code,
            coverage_level=m.coverage_level,
        )
        for m in markets
    ]


def _series_response(
    db: DbSession,
    market: Market,
    days: int,
    base_price: Decimal | None,
    segment_type: PropertyType | None = None,
    guests: int = 2,
) -> MonitoringResponse:
    series = market_series(db, market, days=days, guests=guests)
    # Comp set segmentowy (A2) — tylko w widoku obiektu (segment_type podany).
    segments = (
        segment_medians(db, market, segment_type, days=days, guests=guests)
        if segment_type is not None
        else {}
    )
    floor = latest_floor(db, market)  # A7: spread floor–mediana
    supply = latest_supply(db, market)  # A5: podaż rynku
    return MonitoringResponse(
        market_slug=market.slug,
        currency_code=market.currency_code,
        floor_min=floor.min_price if floor is not None else None,
        floor_median=floor.median_price if floor is not None else None,
        supply_total=supply.total if supply is not None else None,
        supply_previous=supply.previous if supply is not None else None,
        days=[
            MonitoringDayResponse(
                stay_date=day.stay_date,
                median_price=day.median_price,
                sample_size=day.sample_size,
                occupancy=day.occupancy,
                price_position=(
                    price_position(base_price, day.median_price)
                    if base_price is not None and day.median_price
                    else None
                ),
                price_p10=day.price_p10,
                price_p25=day.price_p25,
                price_p75=day.price_p75,
                price_p90=day.price_p90,
                segment_median=_segment_value(segments.get(day.stay_date)),
                segment_sample=_segment_count(segments.get(day.stay_date)),
                booking_pace=day.booking_pace,
            )
            for day in series
        ],
    )


def _segment_value(seg: tuple[Decimal, int] | None) -> Decimal | None:
    """Mediana segmentu tylko przy próbce >= SEGMENT_MIN_SAMPLE (jak w silniku)."""
    return seg[0] if seg is not None and seg[1] >= SEGMENT_MIN_SAMPLE else None


def _segment_count(seg: tuple[Decimal, int] | None) -> int | None:
    return seg[1] if seg is not None and seg[1] >= SEGMENT_MIN_SAMPLE else None


@router.get("/monitoring/market/{market_slug}", response_model=MonitoringResponse)
def market_monitoring(
    market_slug: str, user: CurrentUser, db: DbSession, days: int = 60, guests: int = 2
) -> MonitoringResponse:
    if guests not in (1, 2):  # segment pobytu: 1-os. lub 2-os.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="invalid_guests"
        )
    market = db.scalar(select(Market).where(Market.slug == market_slug))
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return _series_response(db, market, days, base_price=None, guests=guests)


@router.get("/monitoring/property/{property_id}", response_model=MonitoringResponse)
def property_monitoring(
    property_id: uuid.UUID, user: CurrentUser, db: DbSession, days: int = 60
) -> MonitoringResponse:
    prop = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.account_id == user.account_id,  # izolacja tenantów (§6.2 pkt 1)
        )
    )
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="property_not_found")
    market = db.get(Market, prop.market_id)
    return _series_response(
        db, market, days, base_price=prop.base_price, segment_type=prop.property_type
    )


class PerformanceResponse(BaseModel):
    window_days: int
    booked_nights: int
    adr: Decimal | None
    occupancy: float
    revpar: Decimal | None
    currency_code: str


@router.get("/monitoring/property/{property_id}/performance", response_model=PerformanceResponse)
def property_performance(
    property_id: uuid.UUID, user: CurrentUser, db: DbSession, days: int = 30
) -> PerformanceResponse:
    """Prawdziwe ADR/obłożenie/RevPAR z zaimportowanych rezerwacji (B2)."""
    from app.performance import compute_performance

    prop = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.account_id == user.account_id,  # izolacja tenantów (§6.2 pkt 1)
        )
    )
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="property_not_found")
    perf = compute_performance(db, prop, window_days=days)
    return PerformanceResponse(
        window_days=perf.window_days,
        booked_nights=perf.booked_nights,
        adr=perf.adr,
        occupancy=perf.occupancy,
        revpar=perf.revpar,
        currency_code=perf.currency_code,
    )


class RingResponse(BaseModel):
    ring: str  # km od centrum, np. "1-3"
    occupancy: float | None
    listings: int


@router.get("/monitoring/property/{property_id}/rings", response_model=list[RingResponse])
def property_rings(
    property_id: uuid.UUID, user: CurrentUser, db: DbSession, days: int = 30
) -> list[RingResponse]:
    """Obłożenie okolicy wg odległości od centrum — przybliżona mapa miasta."""
    prop = db.scalar(
        select(Property).where(
            Property.id == property_id,
            Property.account_id == user.account_id,  # izolacja tenantów (§6.2 pkt 1)
        )
    )
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="property_not_found")
    market = db.get(Market, prop.market_id)
    return [
        RingResponse(ring=r.ring, occupancy=r.occupancy, listings=r.listings)
        for r in occupancy_by_ring(db, market, days=days)
    ]
