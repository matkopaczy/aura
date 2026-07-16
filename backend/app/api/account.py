from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.db import get_db
from app.models import (
    Account,
    CalendarDay,
    Property,
    Recommendation,
    ReportSent,
    Subscription,
    User,
    WaitlistEntry,
)

router = APIRouter(prefix="/api/account", tags=["account"])

DbSession = Annotated[Session, Depends(get_db)]


@router.get("/export")
def export_account(user: CurrentUser, db: DbSession) -> dict:
    """Eksport danych konta na żądanie (RODO, §9). Wszystko czego trzyma tenant."""
    account = db.get(Account, user.account_id)
    users = db.scalars(select(User).where(User.account_id == user.account_id)).all()
    properties = db.scalars(
        select(Property).where(Property.account_id == user.account_id)
    ).all()
    recommendations = db.scalars(
        select(Recommendation).where(Recommendation.account_id == user.account_id)
    ).all()
    subscription = db.scalar(
        select(Subscription).where(Subscription.account_id == user.account_id)
    )
    return {
        "account": {"id": str(account.id), "name": account.name},
        "users": [{"email": u.email, "locale": u.locale} for u in users],
        "properties": [
            {
                "name": p.name,
                "type": p.property_type,
                "min_price": str(p.min_price),
                "base_price": str(p.base_price) if p.base_price is not None else None,
                "currency_code": p.currency_code,
            }
            for p in properties
        ],
        "recommendations": [
            {
                "stay_date": r.stay_date.isoformat(),
                "recommended_price": str(r.recommended_price),
                "status": r.status,
            }
            for r in recommendations
        ],
        "subscription": (
            {
                "status": subscription.status,
                "price_per_property": str(subscription.price_per_property),
                "currency_code": subscription.currency_code,
            }
            if subscription is not None
            else None
        ),
    }


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(user: CurrentUser, db: DbSession) -> None:
    """Usunięcie konta na żądanie (RODO, §9). Kasuje wszystkie dane tenanta."""
    account_id = user.account_id
    emails = list(
        db.scalars(select(User.email).where(User.account_id == account_id))
    )
    # Dzieci przed rodzicem — brak kaskady na poziomie DB (jedna ścieżka, §11).
    db.execute(delete(Recommendation).where(Recommendation.account_id == account_id))
    db.execute(delete(CalendarDay).where(CalendarDay.account_id == account_id))
    db.execute(delete(Property).where(Property.account_id == account_id))
    db.execute(delete(ReportSent).where(ReportSent.account_id == account_id))
    db.execute(delete(Subscription).where(Subscription.account_id == account_id))
    if emails:
        db.execute(delete(WaitlistEntry).where(WaitlistEntry.email.in_(emails)))
    db.execute(delete(User).where(User.account_id == account_id))
    db.execute(delete(Account).where(Account.id == account_id))
    db.commit()
