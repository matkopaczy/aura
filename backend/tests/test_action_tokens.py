import datetime
from decimal import Decimal

from sqlalchemy import select

from app.action_tokens import _hash, issue_tokens
from app.emails import render_weekly_report
from app.models import (
    ActionToken,
    DecisionChannel,
    Recommendation,
    RecommendationStatus,
)
from app.models.base import utcnow
from tests.test_sprint4 import _property_with_recs

TOMORROW = datetime.date.today() + datetime.timedelta(days=1)


def _pending_rec(db, prop, stay_date=TOMORROW, price=Decimal("260")):
    rec = Recommendation(
        account_id=prop.account_id,
        property_id=prop.id,
        stay_date=stay_date,
        recommended_price=price,
        previous_price=Decimal("200"),
        currency_code="PLN",
        explanation_template_key="v1",
        explanation_params={"factors": []},
        status=RecommendationStatus.PENDING,
    )
    db.add(rec)
    db.commit()
    return rec


def test_issue_tokens_stores_only_hash(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    db_session.commit()
    assert set(raw) == {"accept", "reject"}
    stored = db_session.scalars(
        select(ActionToken).where(ActionToken.recommendation_id == rec.id)
    ).all()
    assert len(stored) == 2
    # W bazie tylko skróty — surowy sekret nieodtwarzalny.
    hashes = {tok.token_hash for tok in stored}
    assert _hash(raw["accept"]) in hashes
    assert not any(tok.token_hash in raw.values() for tok in stored)


def test_get_confirm_page_does_not_mutate(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    db_session.commit()

    r = client.get(f"/api/actions/{raw['accept']}")
    assert r.status_code == 200
    assert "260" in r.text and TOMORROW.isoformat() in r.text
    db_session.refresh(rec)
    assert rec.status == RecommendationStatus.PENDING  # GET nie zmienia stanu


def test_post_accept_applies_and_is_one_time(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    db_session.commit()

    r = client.post(f"/api/actions/{raw['accept']}")
    assert r.status_code == 200
    db_session.refresh(rec)
    assert rec.status == RecommendationStatus.ACCEPTED
    assert rec.decision_channel == DecisionChannel.EMAIL
    assert rec.decided_at is not None

    # Ten sam token drugi raz -> już użyty.
    again = client.post(f"/api/actions/{raw['accept']}")
    assert again.status_code == 410
    # Token bliźniaczy (reject) unieważniony po decyzji.
    sibling = client.post(f"/api/actions/{raw['reject']}")
    assert sibling.status_code == 410


def test_reject_token_rejects(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    db_session.commit()

    client.post(f"/api/actions/{raw['reject']}")
    db_session.refresh(rec)
    assert rec.status == RecommendationStatus.REJECTED


def test_invalid_and_expired_tokens(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    assert client.get("/api/actions/nie-istnieje").status_code == 404

    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    # ręcznie postarz tokeny
    for tok in db_session.scalars(
        select(ActionToken).where(ActionToken.recommendation_id == rec.id)
    ):
        tok.expires_at = utcnow() - datetime.timedelta(days=1)
    db_session.commit()
    r = client.post(f"/api/actions/{raw['accept']}")
    assert r.status_code == 410
    db_session.refresh(rec)
    assert rec.status == RecommendationStatus.PENDING  # wygasły nie działa


def test_already_decided_token_blocked(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    rec = _pending_rec(db_session, prop)
    raw = issue_tokens(db_session, rec)
    rec.status = RecommendationStatus.ACCEPTED  # decyzja z panelu
    db_session.commit()
    r = client.post(f"/api/actions/{raw['accept']}")
    assert r.status_code == 410


def test_weekly_email_carries_decision_links(client, db_session):
    _, headers, prop = _property_with_recs(client, db_session)
    client.post(f"/api/recommendations/{prop.id}/generate?days=7", headers=headers)
    _subject, body = render_weekly_report(db_session, prop)
    assert "/api/actions/" in body
    assert "zatwierdź:" in body and "odrzuć:" in body
