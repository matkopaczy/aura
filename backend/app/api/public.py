import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import CoverageLevel, Market, WaitlistEntry
from app.monitoring import latest_floor, market_series, occupancy_map

router = APIRouter(prefix="/api/public", tags=["public"])

DbSession = Annotated[Session, Depends(get_db)]


class PublicMarket(BaseModel):
    slug: str
    name: str
    coverage_level: CoverageLevel


class MarketPreviewDay(BaseModel):
    stay_date: datetime.date
    median_price: Decimal | None
    occupancy: float | None


class MarketFloor(BaseModel):
    source: str
    min_price: Decimal
    median_price: Decimal
    sample_size: int


class MarketPreview(BaseModel):
    market_slug: str
    market_name: str
    currency_code: str
    coverage_level: CoverageLevel
    days: list[MarketPreviewDay]
    floor: MarketFloor | None  # "minimum rynku" z nocowanie.pl (bezdatowe)


class WaitlistRequest(BaseModel):
    email: EmailStr
    market_slug: str


def _get_market(db: Session, slug: str) -> Market:
    market = db.scalar(select(Market).where(Market.slug == slug))
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    return market


@router.get("/markets", response_model=list[PublicMarket])
def public_markets(db: DbSession) -> list[PublicMarket]:
    markets = db.scalars(select(Market).order_by(Market.name)).all()
    return [
        PublicMarket(slug=m.slug, name=m.name, coverage_level=m.coverage_level)
        for m in markets
    ]


@router.get("/preview/{market_slug}", response_model=MarketPreview)
def market_preview(market_slug: str, db: DbSession, days: int = 30) -> MarketPreview:
    """Lead magnet "zobacz swój rynek" (§5.1): agregaty rynkowe, bez logowania."""
    market = _get_market(db, market_slug)
    series = market_series(db, market, days=days)
    floor = latest_floor(db, market)
    return MarketPreview(
        market_slug=market.slug,
        market_name=market.name,
        currency_code=market.currency_code,
        coverage_level=market.coverage_level,
        days=[
            MarketPreviewDay(
                stay_date=day.stay_date,
                median_price=day.median_price,
                occupancy=day.occupancy,
            )
            for day in series
        ],
        floor=(
            MarketFloor(
                source=floor.source,
                min_price=floor.min_price,
                median_price=floor.median_price,
                sample_size=floor.sample_size,
            )
            if floor is not None
            else None
        ),
    )


class OccupancyPoint(BaseModel):
    slug: str
    name: str
    center_lat: float
    center_lng: float
    occupancy: float | None  # None = rynek bez danych wyczerpujących


@router.get("/occupancy", response_model=list[OccupancyPoint])
def public_occupancy(db: DbSession, days: int = 30) -> list[OccupancyPoint]:
    """Obłożenie wszystkich rynków — mapa Polski na landingu (§5.1)."""
    return [
        OccupancyPoint(
            slug=m.slug,
            name=m.name,
            center_lat=m.center_lat,
            center_lng=m.center_lng,
            occupancy=m.occupancy,
        )
        for m in occupancy_map(db, days=days)
    ]


@router.post("/waitlist", status_code=status.HTTP_201_CREATED)
def join_waitlist(body: WaitlistRequest, db: DbSession) -> dict:
    market = _get_market(db, body.market_slug)
    email = body.email.lower()
    existing = db.scalar(
        select(WaitlistEntry).where(
            WaitlistEntry.email == email, WaitlistEntry.market_id == market.id
        )
    )
    if existing is None:
        db.add(WaitlistEntry(email=email, market_id=market.id))
        db.commit()
    return {"status": "ok"}
