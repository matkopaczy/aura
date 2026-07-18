from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, HttpUrl
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.onboarding import (
    ListingUnavailableError,
    fetch_booking_listing,
    match_market,
    propose_base_price,
)

router = APIRouter(prefix="/api/onboarding", tags=["onboarding"])

DbSession = Annotated[Session, Depends(get_db)]


class ParseRequest(BaseModel):
    url: HttpUrl


class ParseResponse(BaseModel):
    name: str
    lat: float
    lng: float
    market_slug: str
    market_name: str
    currency_code: str
    proposed_base_price: Decimal | None


@router.post("/parse", response_model=ParseResponse)
def parse_listing(body: ParseRequest, user: CurrentUser, db: DbSession) -> ParseResponse:
    try:
        listing = fetch_booking_listing(str(body.url))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail="unsupported_url"
        ) from exc
    except ListingUnavailableError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="listing_unavailable"
        ) from exc
    market = match_market(db, listing.lat, listing.lng)
    if market is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="no_market_for_location")
    return ParseResponse(
        name=listing.name,
        lat=listing.lat,
        lng=listing.lng,
        market_slug=market.slug,
        market_name=market.name,
        currency_code=market.currency_code,
        proposed_base_price=propose_base_price(db, market),
    )
