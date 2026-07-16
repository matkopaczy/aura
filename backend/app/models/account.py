import enum
import uuid

from sqlalchemy import Boolean, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantMixin, TimestampMixin, uuid_pk


class UserRole(enum.StrEnum):
    """Rola w koncie. OWNER: pełny dostęp (ceny, rozliczenia, zespół).
    RECEPTION: tylko codzienny accept/reject rekomendacji (§ role)."""

    OWNER = "owner"
    RECEPTION = "reception"


class Account(Base, TimestampMixin):
    """Klient B2B (gospodarz / firma). Korzeń izolacji tenantów."""

    __tablename__ = "accounts"

    id: Mapped[uuid.UUID] = uuid_pk()
    name: Mapped[str] = mapped_column(String(200), nullable=False)


class User(Base, TenantMixin, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    locale: Mapped[str] = mapped_column(String(10), default="pl", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, native_enum=False, length=20),
        default=UserRole.OWNER,
        nullable=False,
    )
    # Kurator bazy eventów — funkcja wewnętrzna platformy (założyciel), nie klienta.
    is_curator: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
