import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TimestampMixin, uuid_pk


class WaitlistEntry(Base, TimestampMixin):
    """Lead z lead magnetu "zobacz swój rynek" (§5.1).

    Powstaje przed rejestracją konta — dane globalne, bez account_id.
    Napędza priorytet uruchamiania rekomendacji w kolejnych miastach.
    """

    __tablename__ = "waitlist_entries"
    __table_args__ = (UniqueConstraint("email", "market_id"),)

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), nullable=False, index=True)
    market_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("markets.id"), nullable=False, index=True
    )
