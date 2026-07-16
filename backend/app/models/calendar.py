import datetime
import uuid

from sqlalchemy import Date, DateTime, ForeignKey, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class CalendarDay(Base, TenantMixin, TimestampMixin):
    """Zajęty dzień obiektu klienta z importu iCal (tylko odczyt, §6.4).

    Obecność wiersza = termin zajęty. Dni bez wiersza w horyzoncie synchronizacji
    traktujemy jako wolne.
    """

    __tablename__ = "calendar_days"
    __table_args__ = (UniqueConstraint("property_id", "stay_date"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    property_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("properties.id"), nullable=False, index=True
    )
    stay_date: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    synced_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
