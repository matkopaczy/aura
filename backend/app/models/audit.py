import datetime
import uuid

from sqlalchemy import JSON, DateTime, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, uuid_pk


class AuditLog(Base, TenantMixin):
    """Log operacji wrażliwych (bezpieczeństwo przy skali — checklist pkt 24).

    Świadomie BEZ TimestampMixin (created_at) — ma własne pole `occurred_at`,
    żeby nazwa jasno mówiła "kiedy się zdarzyło", nie "kiedy wiersz powstał"
    (to samo w praktyce, ale audit log to dokument, nie encja do edycji).
    Niemodyfikowalny z założenia: brak endpointu UPDATE/DELETE w API — jedyna
    droga usunięcia wiersza to usunięcie całego konta (RODO), patrz account.py.
    """

    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = uuid_pk()
    # None = akcja bez zalogowanego użytkownika w danym momencie (np. request
    # resetu hasła dla adresu, który akurat nie ma konta — i tak nie logujemy
    # tego przypadku, ale pole zostaje nullable dla przyszłych akcji systemowych).
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id"), nullable=True, index=True
    )
    action: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    detail: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    occurred_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
