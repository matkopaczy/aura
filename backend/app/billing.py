"""Cykl życia abonamentu i interfejs operatora płatności (§5, §12 pkt 2).

Wejście: 30 dni triału bez karty (§5). Konwersja na płatny abonament to
decyzja operatora — pilot 5–10 gospodarzy obsługuje ManualProvider (założyciel
wystawia fakturę VAT ręcznie). Automatyczny Stripe/Przelewy24 wchodzi po
walidacji ceny w pilocie (§12 pkt 4), za tym samym interfejsem — nie na zapas (§11).
"""

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Account, Subscription, SubscriptionStatus
from app.models.base import utcnow


@dataclass(frozen=True)
class SubscriptionView:
    status: SubscriptionStatus
    price_per_property: Decimal
    currency_code: str
    trial_ends_at: datetime.datetime | None
    trial_days_left: int | None  # tylko dla triału; None poza triałem
    is_expired: bool  # triał minął, brak aktywacji


class PaymentProvider(ABC):
    """Operator płatności. Nowy operator = nowa implementacja, bez zmian w rdzeniu."""

    @abstractmethod
    def activate(self, db: Session, subscription: Subscription) -> None:
        """Przechodzi z triału/past_due na aktywny abonament."""


class ManualProvider(PaymentProvider):
    """Fakturowanie ręczne (pilot). Aktywacja po potwierdzeniu wpłaty przez założyciela."""

    def activate(self, db: Session, subscription: Subscription) -> None:
        subscription.status = SubscriptionStatus.ACTIVE
        subscription.current_period_end = utcnow() + datetime.timedelta(days=30)
        db.commit()


def get_provider() -> PaymentProvider:
    return ManualProvider()


def start_trial(db: Session, account: Account) -> Subscription:
    """Zakłada 30-dniowy triał przy rejestracji. Idempotentne per konto."""
    existing = db.scalar(
        select(Subscription).where(Subscription.account_id == account.id)
    )
    if existing is not None:
        return existing
    settings = get_settings()
    subscription = Subscription(
        account_id=account.id,
        status=SubscriptionStatus.TRIALING,
        price_per_property=settings.default_price_per_property,
        currency_code=settings.billing_currency,
        trial_ends_at=utcnow() + datetime.timedelta(days=settings.trial_days),
    )
    db.add(subscription)
    return subscription


def _as_utc(value: datetime.datetime) -> datetime.datetime:
    """Wartość z DB jest w UTC (§6.2 pkt 4); SQLite gubi tzinfo, więc dokładamy."""
    return value if value.tzinfo is not None else value.replace(tzinfo=datetime.UTC)


def view(subscription: Subscription) -> SubscriptionView:
    now = utcnow()
    trialing = subscription.status == SubscriptionStatus.TRIALING
    trial_ends = (
        _as_utc(subscription.trial_ends_at)
        if subscription.trial_ends_at is not None
        else None
    )
    is_expired = trialing and trial_ends is not None and trial_ends < now
    days_left = None
    if trialing and trial_ends is not None and not is_expired:
        days_left = (trial_ends - now).days
    return SubscriptionView(
        status=subscription.status,
        price_per_property=subscription.price_per_property,
        currency_code=subscription.currency_code,
        trial_ends_at=subscription.trial_ends_at,
        trial_days_left=days_left,
        is_expired=is_expired,
    )


def cancel(db: Session, subscription: Subscription) -> None:
    subscription.status = SubscriptionStatus.CANCELED
    db.commit()
