import datetime
import uuid

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MarketSupply(Base):
    """Podaż rynku (A5): liczba ofert widocznych w wynikach wyszukiwania, migawka
    per przebieg scrapera. Źródło: nagłówek "znaleziono N obiektów".

    Dane rynkowe (bez account_id) — jak floor_signals. Trend tych migawek w
    czasie = presja konkurencyjna (rosnąca podaż = więcej konkurencji o gościa).
    Świadomie NIE waluta (to liczba obiektów), więc bez currency_code.
    """

    __tablename__ = "market_supply"
    __table_args__ = (Index("ix_supply_market_observed", "market_id", "observed_at"),)

    id: Mapped[int] = mapped_column(
        BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True
    )
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False
    )
    source: Mapped[str] = mapped_column(String(50), nullable=False)  # np. "booking"
    total_listings: Mapped[int] = mapped_column(Integer, nullable=False)
    observed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
