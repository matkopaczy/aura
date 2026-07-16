import datetime
import enum
import uuid
from decimal import Decimal

from sqlalchemy import JSON, DateTime, Enum, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class SubscriptionStatus(enum.StrEnum):
    TRIALING = "trialing"
    ACTIVE = "active"
    PAST_DUE = "past_due"
    CANCELED = "canceled"


class ReportKind(enum.StrEnum):
    WEEKLY = "weekly"
    ALERT = "alert"


class Subscription(Base, TenantMixin, TimestampMixin):
    """Abonament konta. Neutralne wobec operatora płatności (Stripe vs P24 — §12 pkt 2)."""

    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = uuid_pk()
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False, length=20),
        default=SubscriptionStatus.TRIALING,
        nullable=False,
    )
    price_per_property: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    trial_ends_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    current_period_end: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class ReportSent(Base, TenantMixin, TimestampMixin):
    __tablename__ = "reports_sent"

    id: Mapped[uuid.UUID] = uuid_pk()
    kind: Mapped[ReportKind] = mapped_column(
        Enum(ReportKind, native_enum=False, length=20), nullable=False
    )
    sent_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    meta: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
