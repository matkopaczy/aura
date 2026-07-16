import datetime
from decimal import Decimal

from app.alerts import detect_price_spikes
from app.attribution import summarize, update_outcomes
from app.emails import render_weekly_report
from app.i18n import render_factor, t
from app.models import (
    CalendarDay,
    Property,
    Recommendation,
    RecommendationStatus,
)
from app.onboarding import haversine_km, match_market, propose_base_price
from tests.test_api_sprint2 import PROPERTY_BODY, _register, _seed_market
from tests.test_monitoring import _listing, _obs

YESTERDAY = datetime.date.today() - datetime.timedelta(days=1)


def _property_with_recs(client, db_session):
    import uuid

    market = _seed_market(db_session)
    headers = _register(client)
    prop_id = client.post("/api/properties", json=PROPERTY_BODY, headers=headers).json()["id"]
    prop = db_session.get(Property, uuid.UUID(prop_id))
    return market, headers, prop


def _accepted_rec(db, prop, stay_date, previous=Decimal("200"), price=Decimal("260")):
    rec = Recommendation(
        account_id=prop.account_id,
        property_id=prop.id,
        stay_date=stay_date,
        recommended_price=price,
        previous_price=previous,
        currency_code="PLN",
        explanation_template_key="v1",
        explanation_params={"factors": [{"key": "weekend", "pct": 10}]},
        status=RecommendationStatus.ACCEPTED,
        decided_at=datetime.datetime.now(datetime.UTC),
    )
    db.add(rec)
    db.commit()
    return rec


def test_attribution_sold_and_unsold(client, db_session):
    _, _, prop = _property_with_recs(client, db_session)
    sold_rec = _accepted_rec(db_session, prop, YESTERDAY)
    unsold_rec = _accepted_rec(
        db_session, prop, YESTERDAY - datetime.timedelta(days=1)
    )
    db_session.add(
        CalendarDay(
            account_id=prop.account_id,
            property_id=prop.id,
            stay_date=YESTERDAY,
            synced_at=datetime.datetime.now(datetime.UTC),
        )
    )
    db_session.commit()

    assert update_outcomes(db_session, prop) == 2
    assert sold_rec.outcome_sold is True
    assert sold_rec.revenue_delta == Decimal("60")
    assert unsold_rec.outcome_sold is False
    assert unsold_rec.revenue_delta == Decimal("0")

    summary = summarize(db_session, prop)
    assert summary.accepted_count == 2
    assert summary.sold_count == 1
    assert summary.extra_revenue == Decimal("60")

    # ponowny przebieg niczego nie zmienia (outcome ustalony raz)
    assert update_outcomes(db_session, prop) == 0


def test_attribution_endpoint(client, db_session):
    _, headers, prop = _property_with_recs(client, db_session)
    _accepted_rec(db_session, prop, YESTERDAY)
    r = client.get(f"/api/recommendations/attribution/{prop.id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["accepted_count"] == 1
    assert body["currency_code"] == "PLN"


def test_weekly_report_renders_in_polish(client, db_session):
    _, headers, prop = _property_with_recs(client, db_session)
    client.post(f"/api/recommendations/{prop.id}/generate?days=7", headers=headers)
    subject, body = render_weekly_report(db_session, prop)
    assert "rekomendacji czeka na decyzję" in subject
    assert "Najbliższe 14 dni" in body
    assert "Wynik poprzedniego tygodnia" in body
    assert "http://localhost:3000" in body


def test_alert_detects_median_spike(db_session):
    market = _seed_market(db_session)
    stay = datetime.date.today() + datetime.timedelta(days=5)
    l1 = _listing(db_session, market, "pl/a")
    l2 = _listing(db_session, market, "pl/b")
    # przebieg 1: mediana 200; przebieg 2 (dzień później): mediana 300 (+50%)
    for listing, day1, day2 in ((l1, "180", "280"), (l2, "220", "320")):
        db_session.add_all([
            _mk_obs(listing, stay, day1, datetime.datetime(2026, 7, 15, 2, tzinfo=datetime.UTC)),
            _mk_obs(listing, stay, day2, datetime.datetime(2026, 7, 16, 2, tzinfo=datetime.UTC)),
        ])
    db_session.commit()

    spikes = detect_price_spikes(db_session, market)
    assert len(spikes) == 1
    assert spikes[0].stay_date == stay
    assert spikes[0].change_pct == 50


def _mk_obs(listing, stay_date, price, observed_at):
    from app.models import PriceObservation

    return PriceObservation(
        listing_id=listing.id,
        stay_date=stay_date,
        price=Decimal(price),
        currency_code="PLN",
        available=True,
        observed_at=observed_at,
        source="booking",
    )


def test_i18n_templates():
    assert t("email.alert.subject", market="Poznań") == "Aura: skok cen na rynku Poznań"
    assert render_factor({"key": "below_median", "pct": 15, "position": -0.15}) == \
        "15% poniżej mediany"
    assert render_factor({"key": "weekend", "pct": 10}) == "weekend"


def test_onboarding_market_matching(db_session):
    market = _seed_market(db_session)
    # Stary Rynek w Poznaniu — w promieniu
    assert match_market(db_session, 52.408, 16.934).slug == "poznan"
    # Berlin — poza wszystkimi rynkami
    assert match_market(db_session, 52.52, 13.40) is None
    assert haversine_km(52.4064, 16.9252, 52.4064, 16.9252) == 0

    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    listing = _listing(db_session, market, "pl/a")
    _obs(db_session, listing, tomorrow, Decimal("203"))
    db_session.commit()
    assert propose_base_price(db_session, market) == Decimal("205")  # krok 5 zł


def test_property_patch_settings(client, db_session):
    _, headers, prop = _property_with_recs(client, db_session)
    r = client.patch(
        f"/api/properties/{prop.id}",
        json={"min_price": 180, "ical_url": "https://example.com/cal.ics"},
        headers=headers,
    )
    assert r.status_code == 200
    assert Decimal(r.json()["min_price"]) == Decimal("180")
    assert r.json()["ical_url"] == "https://example.com/cal.ics"

    headers_b = _register(client, "obcy@example.com")
    r = client.patch(f"/api/properties/{prop.id}", json={"min_price": 1}, headers=headers_b)
    assert r.status_code == 404
