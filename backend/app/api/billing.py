import datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import OwnerUser
from app.billing import cancel, view
from app.db import get_db
from app.models import Subscription, SubscriptionStatus

router = APIRouter(prefix="/api/billing", tags=["billing"])

DbSession = Annotated[Session, Depends(get_db)]


class SubscriptionResponse(BaseModel):
    status: SubscriptionStatus
    price_per_property: Decimal
    currency_code: str
    trial_ends_at: datetime.datetime | None
    trial_days_left: int | None
    is_expired: bool


def _current_subscription(db: Session, account_id) -> Subscription:
    subscription = db.scalar(
        select(Subscription).where(Subscription.account_id == account_id)
    )
    if subscription is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="subscription_not_found"
        )
    return subscription


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(user: OwnerUser, db: DbSession) -> SubscriptionResponse:
    subscription = _current_subscription(db, user.account_id)
    v = view(subscription)
    return SubscriptionResponse(
        status=v.status,
        price_per_property=v.price_per_property,
        currency_code=v.currency_code,
        trial_ends_at=v.trial_ends_at,
        trial_days_left=v.trial_days_left,
        is_expired=v.is_expired,
    )


@router.post("/cancel", response_model=SubscriptionResponse)
def cancel_subscription(user: OwnerUser, db: DbSession) -> SubscriptionResponse:
    subscription = _current_subscription(db, user.account_id)
    cancel(db, subscription)
    v = view(subscription)
    return SubscriptionResponse(
        status=v.status,
        price_per_property=v.price_per_property,
        currency_code=v.currency_code,
        trial_ends_at=v.trial_ends_at,
        trial_days_left=v.trial_days_left,
        is_expired=v.is_expired,
    )
