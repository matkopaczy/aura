import uuid
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, HttpUrl
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser, OwnerUser
from app.db import get_db
from app.models import Market, Property, PropertyType

router = APIRouter(prefix="/api/properties", tags=["properties"])

DbSession = Annotated[Session, Depends(get_db)]


class PropertyCreate(BaseModel):
    market_slug: str
    name: str = Field(min_length=1, max_length=200)
    property_type: PropertyType
    lat: float = Field(ge=-90, le=90)
    lng: float = Field(ge=-180, le=180)
    capacity: int = Field(ge=1, le=50)
    base_price: Decimal | None = Field(default=None, gt=0)
    min_price: Decimal = Field(gt=0)
    max_price: Decimal | None = Field(default=None, gt=0)
    ical_url: HttpUrl | None = None


class PropertyResponse(BaseModel):
    id: uuid.UUID
    market_slug: str
    name: str
    property_type: PropertyType
    capacity: int
    currency_code: str
    base_price: Decimal | None
    min_price: Decimal
    max_price: Decimal | None
    ical_url: str | None


def _to_response(prop: Property, market: Market) -> PropertyResponse:
    return PropertyResponse(
        id=prop.id,
        market_slug=market.slug,
        name=prop.name,
        property_type=prop.property_type,
        capacity=prop.capacity,
        currency_code=prop.currency_code,
        base_price=prop.base_price,
        min_price=prop.min_price,
        max_price=prop.max_price,
        ical_url=prop.ical_url,
    )


@router.post("", response_model=PropertyResponse, status_code=status.HTTP_201_CREATED)
def create_property(body: PropertyCreate, user: OwnerUser, db: DbSession) -> PropertyResponse:
    market = db.scalar(select(Market).where(Market.slug == body.market_slug))
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="market_not_found")
    if body.max_price is not None and body.max_price < body.min_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="max_below_min"
        )
    prop = Property(
        account_id=user.account_id,
        market_id=market.id,
        name=body.name,
        property_type=body.property_type,
        lat=Decimal(str(body.lat)),
        lng=Decimal(str(body.lng)),
        capacity=body.capacity,
        currency_code=market.currency_code,
        base_price=body.base_price,
        min_price=body.min_price,
        max_price=body.max_price,
        ical_url=str(body.ical_url) if body.ical_url else None,
    )
    db.add(prop)
    db.commit()
    return _to_response(prop, market)


class PropertyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    base_price: Decimal | None = Field(default=None, gt=0)
    min_price: Decimal | None = Field(default=None, gt=0)
    max_price: Decimal | None = Field(default=None, gt=0)
    ical_url: HttpUrl | None = None


@router.patch("/{property_id}", response_model=PropertyResponse)
def update_property(
    property_id: uuid.UUID, body: PropertyUpdate, user: OwnerUser, db: DbSession
) -> PropertyResponse:
    prop = db.scalar(
        select(Property).where(
            Property.id == property_id, Property.account_id == user.account_id
        )
    )
    if prop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="property_not_found")
    changes = body.model_dump(exclude_unset=True)
    if "ical_url" in changes and changes["ical_url"] is not None:
        changes["ical_url"] = str(changes["ical_url"])
    for field, value in changes.items():
        setattr(prop, field, value)
    if prop.max_price is not None and prop.max_price < prop.min_price:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="max_below_min"
        )
    db.commit()
    market = db.get(Market, prop.market_id)
    return _to_response(prop, market)


@router.get("", response_model=list[PropertyResponse])
def list_properties(user: CurrentUser, db: DbSession) -> list[PropertyResponse]:
    rows = db.execute(
        select(Property, Market)
        .join(Market, Market.id == Property.market_id)
        .where(Property.account_id == user.account_id)  # izolacja tenantów (§6.2 pkt 1)
        .order_by(Property.created_at)
    ).all()
    return [_to_response(prop, market) for prop, market in rows]
