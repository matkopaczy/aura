from decimal import Decimal

from sqlalchemy import select

from app.models import CurationStatus, Event, User
from tests.test_api_sprint2 import _register, _seed_market


def _curator(client, db_session):
    headers = _register(client)
    user = db_session.scalar(select(User).where(User.email == "gospodarz@example.com"))
    user.is_curator = True
    db_session.commit()
    return headers


def _draft(db, market, name):
    import datetime

    ev = Event(
        market_id=market.id, name=name, category="targi",
        start_date=datetime.date(2026, 9, 1), end_date=datetime.date(2026, 9, 2),
        impact_strength=Decimal("0.7"), source="mtp", curation_status=CurationStatus.DRAFT,
    )
    db.add(ev)
    db.commit()
    return ev


def test_bulk_approve(client, db_session):
    market = _seed_market(db_session)
    headers = _curator(client, db_session)
    ids = [str(_draft(db_session, market, f"E{i}").id) for i in range(3)]

    r = client.post(
        "/api/curation/events/bulk",
        json={"event_ids": ids, "status": "approved"},
        headers=headers,
    )
    assert r.status_code == 200
    assert r.json()["updated"] == 3
    approved = db_session.scalars(
        select(Event).where(Event.curation_status == CurationStatus.APPROVED)
    ).all()
    assert len(approved) == 3


def test_bulk_requires_curator(client, db_session):
    market = _seed_market(db_session)
    headers = _register(client)  # nie kurator
    ev = _draft(db_session, market, "X")
    r = client.post(
        "/api/curation/events/bulk",
        json={"event_ids": [str(ev.id)], "status": "approved"},
        headers=headers,
    )
    assert r.status_code == 403


def test_refresh_requires_curator_and_accepts(client, db_session, monkeypatch):
    _seed_market(db_session)
    # nie kurator -> 403
    non_curator = _register(client, "zwykly@example.com")
    assert client.post("/api/curation/events/refresh", headers=non_curator).status_code == 403

    # kurator -> 202, task w tle nie odpala prawdziwego scrapingu (podmieniony)
    import app.event_sources.ingest as ingest_mod

    called = {"n": 0}
    monkeypatch.setattr(ingest_mod, "run", lambda: called.__setitem__("n", called["n"] + 1))
    headers = _curator(client, db_session)
    r = client.post("/api/curation/events/refresh", headers=headers)
    assert r.status_code == 202
    assert r.json()["status"] == "started"
