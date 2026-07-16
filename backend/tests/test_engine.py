import datetime
import uuid
from decimal import Decimal

import pytest

from app.engine import compute_recommendation
from app.models import CurationStatus, Event, Property, PropertyType
from app.monitoring import MarketDay

FRIDAY = datetime.date(2026, 8, 14)  # piątek, sezon wysoki
TUESDAY = datetime.date(2026, 3, 10)  # wtorek, poza sezonem


def _property(base=Decimal("200"), min_price=Decimal("100"), max_price=None) -> Property:
    return Property(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        market_id=uuid.uuid4(),
        name="Test",
        property_type=PropertyType.APARTMENT,
        lat=Decimal("52.4"),
        lng=Decimal("16.9"),
        capacity=4,
        currency_code="PLN",
        base_price=base,
        min_price=min_price,
        max_price=max_price,
    )


def _day(median, sample=20, occupancy=None, date=FRIDAY) -> MarketDay:
    return MarketDay(
        stay_date=date, median_price=median, sample_size=sample, occupancy=occupancy
    )


def _event(impact=0.95, date=FRIDAY) -> Event:
    return Event(
        market_id=uuid.uuid4(),
        name="Majówka",
        category="dlugi-weekend",
        start_date=date,
        end_date=date,
        impact_strength=Decimal(str(impact)),
        source="test",
        curation_status=CurationStatus.APPROVED,
    )


def test_factors_compose_and_price_rounds_to_5():
    # baza 200, piątek ×1.10, sezon ×1.10, event 0.95 ×1.38, poniżej mediany +15%
    draft = compute_recommendation(
        _property(), FRIDAY, _day(Decimal("300")), [_event()]
    )
    keys = {f.key for f in draft.factors}
    assert keys == {"weekend", "high_season", "event", "below_median"}
    # 200 × 1.1 × 1.1 × 1.38 × 1.15 = 384.05 → 385
    assert draft.price == Decimal("385")
    assert draft.price % Decimal("5") == 0
    assert draft.previous_price == Decimal("200")


def test_explanation_has_top3_factors_sorted_by_impact():
    draft = compute_recommendation(
        _property(), FRIDAY, _day(Decimal("300"), occupancy=0.75), [_event()]
    )
    explanation_keys = [f["key"] for f in draft.explanation_params["factors"]]
    assert len(explanation_keys) == 3
    assert explanation_keys[0] == "event"  # +38% to najsilniejszy czynnik
    assert draft.explanation_template_key == "v1"
    assert draft.explanation_params["sample_size"] == 20


def test_max_price_clamps_and_is_recorded():
    draft = compute_recommendation(
        _property(max_price=Decimal("250")), FRIDAY, _day(Decimal("300")), [_event()]
    )
    assert draft.price == Decimal("250")
    assert draft.explanation_params["clamped"] is True


def test_min_price_clamps():
    draft = compute_recommendation(
        _property(base=Decimal("110"), min_price=Decimal("105")),
        TUESDAY,
        _day(Decimal("80")),  # rynek dużo taniej -> czynnik w dół
        [],
    )
    assert draft.price == Decimal("105")


def test_above_median_pulls_price_down():
    draft = compute_recommendation(
        _property(base=Decimal("300")), TUESDAY, _day(Decimal("200")), []
    )
    keys = {f.key for f in draft.factors}
    assert "above_median" in keys
    assert draft.price < Decimal("300")


def test_no_market_data_uses_calendar_factors_only():
    draft = compute_recommendation(_property(), FRIDAY, _day(None, sample=0), [])
    keys = {f.key for f in draft.factors}
    assert keys == {"weekend", "high_season"}
    # 200 × 1.1 × 1.1 = 242 → 240
    assert draft.price == Decimal("240")


def test_missing_base_price_fails_fast():
    with pytest.raises(ValueError):
        compute_recommendation(_property(base=None), FRIDAY, _day(Decimal("200")), [])


def test_neutral_tuesday_keeps_base_price():
    draft = compute_recommendation(
        _property(), TUESDAY, _day(Decimal("205")), []  # w paśmie ±5% od mediany
    )
    assert draft.factors == []
    assert draft.price == Decimal("200")
