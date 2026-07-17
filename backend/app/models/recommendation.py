import datetime
import enum
import uuid
from decimal import Decimal

from sqlalchemy import JSON, Boolean, Date, DateTime, Enum, ForeignKey, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class RecommendationStatus(enum.StrEnum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class DecisionChannel(enum.StrEnum):
    """Kanałem, którym zapadła decyzja klienta (§6.3): panel czy e-mail."""

    DASHBOARD = "dashboard"
    EMAIL = "email"


class Recommendation(Base, TenantMixin, TimestampMixin):
    """Rekomendacja cenowa z pełnym stanem pod atrybucję (§3 pkt 4).

    Uzasadnienie przechowywane jako klucz szablonu + parametry —
    NIGDY jako sklejone zdania (§6.2 pkt 5).
    """

    __tablename__ = "recommendations"

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False, index=True
    )
    stay_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    recommended_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    previous_price: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    # Mediana konkurencji w momencie rekomendacji — pod licznik konserwatywny (§3.4, §6.3).
    competitor_median: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    explanation_template_key: Mapped[str] = mapped_column(String(100), nullable=False)
    explanation_params: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[RecommendationStatus] = mapped_column(
        Enum(RecommendationStatus, native_enum=False, length=20),
        default=RecommendationStatus.PENDING,
        nullable=False,
    )
    decided_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
    decision_channel: Mapped[DecisionChannel | None] = mapped_column(
        Enum(DecisionChannel, native_enum=False, length=20)
    )
    outcome_sold: Mapped[bool | None] = mapped_column(Boolean)  # NULL = jeszcze nieznany
    revenue_delta: Mapped[Decimal | None] = mapped_column(Numeric(10, 2))
