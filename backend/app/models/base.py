import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Uuid
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    """Wszystkie znaczniki czasu w UTC (§6.2 pkt 4)."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class TenantMixin:
    """Każda tabela biznesowa należy do konta klienta (§6.2 pkt 1).

    Zapytania o dane biznesowe ZAWSZE filtrują po account_id.
    """

    account_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("accounts.id"), nullable=False, index=True
    )


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
