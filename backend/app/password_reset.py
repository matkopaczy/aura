"""Self-service reset hasła (bezpieczeństwo przy skali — audyt 2026-07-19).

Ten sam wzorzec co action_tokens.py: token = zdolność, w bazie tylko skrót
SHA-256, jednorazowy, wygasający. Checklist bezpieczeństwa pkt 6: nigdy nie
zdradzamy, czy konto istnieje — router zawsze zwraca ten sam komunikat,
niezależnie od wyniku request_reset.
"""

import datetime
import hashlib
import secrets

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.auth.security import hash_password
from app.models import PasswordResetToken, User
from app.models.base import utcnow

TOKEN_BYTES = 32  # ~43 znaki base64url — nie do zgadnięcia
RESET_TOKEN_TTL_MINUTES = 30  # krótszy niż tokeny decyzji (§9) — reset to zmiana tożsamości


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime.datetime) -> datetime.datetime:
    # Postgres zwraca aware; SQLite (testy) gubi tzinfo — zakładamy UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=datetime.UTC)


def request_reset(db: Session, email: str) -> str | None:
    """Wydaje token resetu dla e-maila, jeśli konto istnieje i jest aktywne.

    Zwraca surowy token albo None (konto nie istnieje) — wywołujący (router)
    NIE ujawnia różnicy w odpowiedzi HTTP (zawsze ten sam komunikat, §9).
    Kasuje wcześniejsze niewykorzystane tokeny tego użytkownika.
    """
    user = db.scalar(
        select(User).where(User.email == email.lower(), User.is_active.is_(True))
    )
    if user is None:
        return None
    db.execute(
        delete(PasswordResetToken).where(
            PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None)
        )
    )
    token = secrets.token_urlsafe(TOKEN_BYTES)
    db.add(
        PasswordResetToken(
            account_id=user.account_id,
            user_id=user.id,
            token_hash=_hash(token),
            expires_at=utcnow() + datetime.timedelta(minutes=RESET_TOKEN_TTL_MINUTES),
        )
    )
    db.commit()
    return token


def resolve(
    db: Session, raw_token: str
) -> tuple[PasswordResetToken | None, User | None, str | None]:
    """Zwraca (token, user, kod_błędu). error=None => można zastosować."""
    token = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == _hash(raw_token))
    )
    if token is None:
        return None, None, "invalid"
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        return token, None, "invalid"
    if token.used_at is not None:
        return token, user, "used"
    if _as_utc(token.expires_at) <= utcnow():
        return token, user, "expired"
    return token, user, None


def apply_reset(db: Session, token: PasswordResetToken, user: User, new_password: str) -> None:
    """Ustawia nowe hasło i unieważnia WSZYSTKIE tokeny tego użytkownika
    (nie tylko użyty) — zapobiega wyścigowi, gdy ktoś ma kilka linków."""
    user.password_hash = hash_password(new_password)
    token.used_at = utcnow()
    db.flush()
    db.execute(
        update(PasswordResetToken)
        .where(PasswordResetToken.user_id == user.id, PasswordResetToken.used_at.is_(None))
        .values(used_at=utcnow())
    )
    db.commit()
