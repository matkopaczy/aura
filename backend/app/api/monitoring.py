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


class MonitoringResponse(BaseModel):
    market_slug: str
    currency_code: str
    days: list[MonitoringDayResponse]


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
) -> MonitoringResponse:
    series = market_series(db, market, days=days)
    # Comp set segmentowy (A2) — tylko w widoku obiektu (segment_type podany).
    segments = (
        segment_medians(db, market, segment_type, days=days)
        if segment_type is not None
        else {}
    )
    return MonitoringResponse(
        market_slug=market.slug,
        currency_code=market.currency_code,
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
    market_slug: str, user: CurrentUser, db: DbSession, days: int = 60
) -> MonitoringResponse:
    market = db.scalar(select(Market).where(Market.slug == market_slug))
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return _series_response(db, market, days, base_price=None)


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
