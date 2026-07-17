import datetime
import enum
import uuid

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class ActionTokenAction(enum.StrEnum):
    ACCEPT = "accept"
    REJECT = "reject"


class ActionToken(Base, TenantMixin, TimestampMixin):
    """Jednorazowy, wygasający token decyzji z e-maila bez logowania (§8.2, §9).

    Token to zdolność (capability): w linku wysyłamy losowy sekret, w bazie
    trzymamy tylko jego skrót SHA-256 (wyciek bazy nie pozwala odtworzyć linku).
    Działa raz (used_at) i wygasa (expires_at) — po użyciu unieważniamy też
    token bliźniaczy (druga akcja tej samej rekomendacji).
    """

    __tablename__ = "action_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    recommendation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("recommendations.id"), nullable=False, index=True
    )
    action: Mapped[ActionTokenAction] = mapped_column(
        Enum(ActionTokenAction, native_enum=False, length=20), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
