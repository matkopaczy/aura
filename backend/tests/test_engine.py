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


def _event(impact=0.95, date=FRIDAY, name="Majówka", venue=None) -> Event:
    return Event(
        market_id=uuid.uuid4(),
        name=name,
        category="dlugi-weekend",
        start_date=date,
        end_date=date,
        impact_strength=Decimal(str(impact)),
        source="test",
        curation_status=CurationStatus.APPROVED,
        venue_lat=Decimal(str(venue[0])) if venue else None,
        venue_lng=Decimal(str(venue[1])) if venue else None,
    )


def _event_factor_of(draft):
    return next(f for f in draft.factors if f.key == "event")


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


# --- Event-distance (§ event-distance) ---
# Obiekt jest w (52.4, 16.9). 0.1° szerokości ≈ 11 km.

def test_event_without_venue_is_citywide():
    draft = compute_recommendation(
        _property(), FRIDAY, _day(Decimal("300")), [_event(impact=0.5)]
    )
    ev = _event_factor_of(draft)
    assert ev.multiplier == 1 + 0.4 * 0.5  # pełny wpływ, bez skalowania
    assert "venue_distance_km" not in ev.params


def test_event_at_property_full_impact():
    draft = compute_recommendation(
        _property(), FRIDAY, _day(Decimal("300")),
        [_event(impact=0.5, venue=(52.4, 16.9))],  # venue = pozycja obiektu
    )
    ev = _event_factor_of(draft)
    assert ev.multiplier == 1 + 0.4 * 0.5
    assert ev.params["venue_distance_km"] == 0.0


def test_event_far_from_venue_decays_to_floor():
    draft = compute_recommendation(
        _property(), FRIDAY, _day(Decimal("300")),
        [_event(impact=0.5, venue=(52.5, 16.9))],  # ~11 km > FAR
    )
    ev = _event_factor_of(draft)
    # proximity = FLOOR 0.30 -> wpływ efektywny 0.15
    assert ev.multiplier == 1 + 0.4 * (0.5 * 0.30)
    assert ev.params["venue_distance_km"] > 6.0


def test_nearby_weak_event_beats_distant_strong():
    # A: silny (0.9) ale ~11 km od obiektu -> efektywny 0.27
    # B: słaby (0.5) w pozycji obiektu -> efektywny 0.50 -> wygrywa
    events = [
        _event(impact=0.9, name="Mecz daleko", venue=(52.5, 16.9)),
        _event(impact=0.5, name="Targi blisko", venue=(52.4, 16.9)),
    ]
    draft = compute_recommendation(_property(), FRIDAY, _day(Decimal("300")), events)
    ev = _event_factor_of(draft)
    assert ev.params["name"] == "Targi blisko"
    assert ev.params["venue_distance_km"] == 0.0
