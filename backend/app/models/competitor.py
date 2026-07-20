import datetime
import uuid
from decimal import Decimal

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class CompetitorListing(Base, TimestampMixin):
    """Obiekt konkurencji zmapowany do rynku. Dane wspólne (bez account_id).

    Przechowujemy wyłącznie: ceny, dostępność, typ jednostki, rating,
    lokalizację ogólną, udogodnienia (§6.4). Żadnych zdjęć, opisów, opinii.
    """

    __tablename__ = "competitor_listings"
    __table_args__ = (UniqueConstraint("source", "source_listing_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # slug adaptera, np. booking
    source_listing_id: Mapped[str] = mapped_column(String(200), nullable=False)
    unit_type: Mapped[str | None] = mapped_column(String(100))
    rating: Mapped[Decimal | None] = mapped_column(Numeric(3, 1))
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    # Lokalizacja ogólna z wyników wyszukiwania (gdy brak współrzędnych).
    distance_center_km: Mapped[Decimal | None] = mapped_column(Numeric(6, 2))
    amenities: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class PriceObservation(Base):
    """Time series obserwacji cen/dostępności konkurencji."""

    __tablename__ = "price_observations"
    __table_args__ = (
        Index("ix_price_obs_listing_stay", "listing_id", "stay_date", "observed_at"),
    )

    # Wariant dla SQLite (testy): tylko INTEGER PRIMARY KEY dostaje autoinkrement.
    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    listing_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("competitor_listings.id"), nullable=False
    )
    stay_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))  # NULL gdy niedostępny
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    available: Mapped[bool] = mapped_column(Boolean, nullable=False)
    # Liczba gości wyszukiwania (A: pokoje 1-osobowe). 2 = domyślny skan; 1 =
    # osobny lekki przebieg pod pobyty 1-os. Zapytania segmentują po tym polu,
    # żeby ceny 1-os. nie mieszały się do median 2-os.
    guests: Mapped[int] = mapped_column(
        Integer, nullable=False, default=2, server_default="2"
    )
    observed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    source: Mapped[str] = mapped_column(String(50), nullable=False)
