import datetime
import enum
import uuid
from decimal import Decimal

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class BookingChannel(enum.StrEnum):
    """Kanał sprzedaży rezerwacji (z importu gospodarza)."""

    BOOKING = "booking"
    AIRBNB = "airbnb"
    DIRECT = "direct"
    OTHER = "other"


class Booking(Base, TenantMixin, TimestampMixin):
    """Zrealizowana rezerwacja gospodarza (import CSV) — PER NOC.

    Prywatne dane gospodarza (TenantMixin, §6.2 pkt 1), NIE dane rynkowe.
    Odróżnia się od CalendarDay (iCal = tylko zajętość) tym, że niesie
    RZECZYWISTĄ cenę sprzedaży — fundament pod prawdziwy ADR/RevPAR i uczciwy
    licznik wyniku (B, §3.4/§7.2). Rezerwacja wielonocna jest rozwijana na
    wiersze per noc przy imporcie; cena nocna z podziału ceny całkowitej.
    Jedna noc = jeden wiersz (UniqueConstraint) — import idempotentny (upsert).
    """

    __tablename__ = "bookings"
    __table_args__ = (UniqueConstraint("property_id", "stay_date"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False, index=True
    )
    stay_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    nightly_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    channel: Mapped[BookingChannel] = mapped_column(
        Enum(BookingChannel, native_enum=False, length=20), nullable=False
    )
    # Referencja rezerwacji ze źródła (opcjonalna) — ślad audytowy importu.
    reservation_ref: Mapped[str | None] = mapped_column(String(100))
    imported_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
