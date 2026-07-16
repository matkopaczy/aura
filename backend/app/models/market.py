import datetime
import enum
import uuid

from sqlalchemy import JSON, Date, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class CoverageLevel(enum.StrEnum):
    """Dwa poziomy pokrycia miast (§5.1)."""

    MONITORING = "monitoring"
    RECOMMENDATIONS = "recommendations"


class CurationStatus(enum.StrEnum):
    DRAFT = "draft"
    APPROVED = "approved"
    REJECTED = "rejected"


class Market(Base, TimestampMixin):
    """Rynek jako dane, nie kod (§6.2 pkt 2).

    Dodanie miasta/kraju = nowy wiersz + ewentualny adapter scrapera.
    Dane rynkowe są wspólne dla wszystkich tenantów (bez account_id).
    """

    __tablename__ = "markets"

    id: Mapped[uuid.UUID] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    country_code: Mapped[str] = mapped_column(String(2), nullable=False)  # ISO 3166-1 alpha-2
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)  # ISO 4217
    timezone: Mapped[str] = mapped_column(String(64), nullable=False)  # IANA, np. Europe/Warsaw
    language: Mapped[str] = mapped_column(String(10), nullable=False)  # BCP 47, np. pl
    coverage_level: Mapped[CoverageLevel] = mapped_column(
        Enum(CoverageLevel, native_enum=False, length=20), nullable=False
    )
    # Obszar rynku: środek + promień. PostGIS dopiero gdy będzie zmierzony problem (§11).
    center_lat: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    center_lng: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    radius_km: Mapped[float] = mapped_column(Numeric(5, 1), nullable=False)
    # Aktywne źródła danych, np. ["booking"] — sloty na adaptery scrapera (§6.2 pkt 6).
    active_sources: Mapped[list] = mapped_column(JSON, default=list, nullable=False)


class Event(Base, TimestampMixin):
    """Kuratorowana baza lokalnych eventów — moduł rdzeniowy (§3 pkt 1)."""

    __tablename__ = "events"

    id: Mapped[uuid.UUID] = uuid_pk()
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False, index=True
    )
    district: Mapped[str | None] = mapped_column(String(100))
    name: Mapped[str] = mapped_column(String(300), nullable=False)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    start_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    end_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    impact_strength: Mapped[float] = mapped_column(Numeric(3, 2), nullable=False)  # 0.00–1.00
    # Miejsce wydarzenia (opcjonalne): eventy punktowe (mecz, targi) mają współrzędne,
    # ogólnomiejskie (długi weekend, święto) zostają NULL i działają na cały rynek.
    venue_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    venue_lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    curation_status: Mapped[CurationStatus] = mapped_column(
        Enum(CurationStatus, native_enum=False, length=20),
        default=CurationStatus.DRAFT,
        nullable=False,
    )
