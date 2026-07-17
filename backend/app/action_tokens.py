"""Tokeny decyzji z e-maila (§8.2, §9): wydawanie, weryfikacja, użycie.

Jeden path: link niesie losowy sekret, baza trzyma tylko jego skrót. Token
działa raz i wygasa; użycie unieważnia token bliźniaczy (drugą akcję).
"""

import datetime
import hashlib
import secrets

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import (
    ActionToken,
    ActionTokenAction,
    DecisionChannel,
    Recommendation,
    RecommendationStatus,
)
from app.models.base import utcnow

TOKEN_BYTES = 32  # ~43 znaki base64url — nie do zgadnięcia


def _hash(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _as_utc(dt: datetime.datetime) -> datetime.datetime:
    # Postgres zwraca aware; SQLite (testy) gubi tzinfo — zakładamy UTC.
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=datetime.UTC)


def issue_tokens(db: Session, rec: Recommendation, ttl_days: int | None = None) -> dict[str, str]:
    """Wydaje parę tokenów (accept, reject) dla rekomendacji; zwraca surowe sekrety.

    Kasuje wcześniejsze niewykorzystane tokeny tej rekomendacji — działa tylko
    link z najświeższego e-maila. Nie commituje (robi to wywołujący).
    """
    if ttl_days is None:
        ttl_days = get_settings().action_token_days
    db.execute(
        delete(ActionToken).where(
            ActionToken.recommendation_id == rec.id, ActionToken.used_at.is_(None)
        )
    )
    expires_at = utcnow() + datetime.timedelta(days=ttl_days)
    raw: dict[str, str] = {}
    for action in (ActionTokenAction.ACCEPT, ActionTokenAction.REJECT):
        token = secrets.token_urlsafe(TOKEN_BYTES)
        raw[action.value] = token
        db.add(
            ActionToken(
                account_id=rec.account_id,
                recommendation_id=rec.id,
                action=action,
                token_hash=_hash(token),
                expires_at=expires_at,
            )
        )
    db.flush()
    return raw


def resolve(
    db: Session, raw_token: str
) -> tuple[ActionToken | None, Recommendation | None, str | None]:
    """Zwraca (token, rekomendacja, kod_błędu). error=None => można zastosować."""
    token = db.scalar(select(ActionToken).where(ActionToken.token_hash == _hash(raw_token)))
    if token is None:
        return None, None, "invalid"
    rec = db.get(Recommendation, token.recommendation_id)
    if rec is None:
        return token, None, "invalid"
    if token.used_at is not None:
        return token, rec, "used"
    if _as_utc(token.expires_at) <= utcnow():
        return token, rec, "expired"
    if rec.status != RecommendationStatus.PENDING:
        return token, rec, "already_decided"
    return token, rec, None


def apply_token(db: Session, token: ActionToken, rec: Recommendation) -> None:
    """Stosuje decyzję z tokenu i unieważnia rodzeństwo. Commituje."""
    rec.status = (
        RecommendationStatus.ACCEPTED
        if token.action == ActionTokenAction.ACCEPT
        else RecommendationStatus.REJECTED
    )
    rec.decided_at = utcnow()
    rec.decision_channel = DecisionChannel.EMAIL
    token.used_at = utcnow()
    db.flush()
    # Druga akcja tej samej rekomendacji nie może już zadziałać.
    db.execute(
        update(ActionToken)
        .where(
            ActionToken.recommendation_id == rec.id,
            ActionToken.used_at.is_(None),
        )
        .values(used_at=utcnow())
    )
    db.commit()
