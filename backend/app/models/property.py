import enum
import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class PropertyType(enum.StrEnum):
    APARTMENT = "apartment"
    GUESTHOUSE = "guesthouse"
    ROOM = "room"


class Property(Base, TenantMixin, TimestampMixin):
    """Obiekt klienta. Kwoty zawsze z kodem waluty (§6.2 pkt 3);
    strefa czasowa obiektu dziedziczona z rynku (§6.2 pkt 4)."""

    __tablename__ = "properties"

    id: Mapped[uuid.UUID] = uuid_pk()
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    property_type: Mapped[PropertyType] = mapped_column(
        Enum(PropertyType, native_enum=False, length=20), nullable=False
    )
    lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    base_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    max_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    ical_url: Mapped[str | None] = mapped_column(String(1000))
