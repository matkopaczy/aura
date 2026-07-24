"""Log operacji wrażliwych (bezpieczeństwo przy skali, checklist pkt 24).

Zakres dziś: logowania, reset hasła, zarządzanie zespołem, eksport danych.
NIE obejmuje (świadomie, bo nieaplikowalne): płatności (Stripe niewdrożony),
API key (funkcja nie istnieje). Usunięcie konta NIE jest tu logowane — kasuje
własny log w tej samej operacji (§ account.py delete_account), co jest
poprawnym zachowaniem RODO (prawo do usunięcia obejmuje też ślad audytowy).
"""

from sqlalchemy.orm import Session

from app.models import AuditLog
from app.models.base import utcnow


def log(db: Session, account_id, user_id, action: str, **detail) -> None:
    """Dodaje wiersz audytu. NIE commituje — wywołujący commituje razem
    z resztą operacji (log jest częścią tej samej transakcji, co akcja)."""
    db.add(
        AuditLog(
            account_id=account_id,
            user_id=user_id,
            action=action,
            detail=detail,
            occurred_at=utcnow(),
        )
    )
