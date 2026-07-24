import datetime
import uuid

from sqlalchemy import DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class PasswordResetToken(Base, TenantMixin, TimestampMixin):
    """Jednorazowy, wygasający token resetu hasła (bezpieczeństwo przy skali).

    Ten sam wzorzec bezpieczeństwa co ActionToken (token = zdolność, w bazie
    tylko skrót SHA-256, jednorazowy, TTL, account_id z TenantMixin §6.2 pkt 1)
    — ale to OSOBNY model, nie reużycie ActionToken: reset hasła weryfikuje
    TOŻSAMOŚĆ użytkownika, nie decyzję o rekomendacji (inna odpowiedzialność,
    §11).
    """

    __tablename__ = "password_reset_tokens"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=False, index=True
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))
