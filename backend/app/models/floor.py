import datetime
import uuid
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class FloorSignal(Base):
    """Sygnał "minimum rynku" ze źródeł bez cen per-data (np. nocowanie.pl).

    Dane rynkowe (bez account_id). Świadomie ODDZIELONE od price_observations
    (per-data), bo cena "od X zł" jest bezdatowa — nie wolno jej mieszać do
    mediany per-data (§6.4, §11). To osobny, uczciwy sygnał kontekstu.
    """

    __tablename__ = "floor_signals"
    __table_args__ = (Index("ix_floor_market_observed", "market_id", "observed_at"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # np. "nocowanie"
    min_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    median_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    sample_size: Mapped[int] = mapped_column(Integer, nullable=False)
    currency_code: Mapped[str] = mapped_column(String(3), nullable=False)
    observed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
