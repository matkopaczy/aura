"""Silnik rekomendacji v1 — regułowy, przejrzysty (§7.1).

Cena = cena bazowa klienta × iloczyn czynników, z twardym ograniczeniem
min/max. Każdy czynnik zapisuje swój wkład; wyjaśnienie to top 3 czynniki
jako klucz szablonu + parametry — nigdy sklejane zdania (§6.2 pkt 5).

Stałe strojenia zebrane na górze — kalibracja per rynek w pilocie.
"""

import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.models import Event, Property
from app.monitoring import MarketDay

WEEKEND_MULTIPLIER = 1.10  # piątek, sobota
SUNDAY_MULTIPLIER = 0.95
HIGH_SEASON_MONTHS = {6, 7, 8}
HIGH_SEASON_MULTIPLIER = 1.10
LOW_SEASON_MONTHS = {1, 2, 11}  # grudzień obsługują eventy (święta, sylwester)
LOW_SEASON_MULTIPLIER = 0.95
EVENT_IMPACT_WEIGHT = 0.4  # event o sile 1.0 -> +40%
OCCUPANCY_HIGH_THRESHOLD, OCCUPANCY_HIGH_MULTIPLIER = 0.7, 1.15
OCCUPANCY_MID_THRESHOLD, OCCUPANCY_MID_MULTIPLIER = 0.5, 1.08
OCCUPANCY_LOW_THRESHOLD, OCCUPANCY_LOW_MULTIPLIER = 0.2, 0.95
POSITION_WEIGHT = 0.5  # domykamy połowę dystansu do mediany
POSITION_MIN, POSITION_MAX = -0.10, 0.15
POSITION_DEADBAND = 0.05  # ±5% od mediany = bez korekty
ROUND_TO = Decimal("5")  # ceny w krokach po 5 zł
TOP_FACTORS_IN_EXPLANATION = 3


@dataclass(frozen=True)
class Factor:
    key: str
    multiplier: float
    params: dict


@dataclass(frozen=True)
class RecommendationDraft:
    stay_date: datetime.date
    price: Decimal
    previous_price: Decimal
    factors: list[Factor]
    explanation_template_key: str
    explanation_params: dict


def _day_of_week_factor(stay_date: datetime.date) -> Factor | None:
    weekday = stay_date.weekday()
    if weekday in (4, 5):
        return Factor("weekend", WEEKEND_MULTIPLIER, {})
    if weekday == 6:
        return Factor("sunday", SUNDAY_MULTIPLIER, {})
    return None


def _season_factor(stay_date: datetime.date) -> Factor | None:
    if stay_date.month in HIGH_SEASON_MONTHS:
        return Factor("high_season", HIGH_SEASON_MULTIPLIER, {})
    if stay_date.month in LOW_SEASON_MONTHS:
        return Factor("low_season", LOW_SEASON_MULTIPLIER, {})
    return None


def _event_factor(stay_date: datetime.date, events: list[Event]) -> Factor | None:
    overlapping = [e for e in events if e.start_date <= stay_date <= e.end_date]
    if not overlapping:
        return None
    strongest = max(overlapping, key=lambda e: e.impact_strength)
    impact = float(strongest.impact_strength)
    return Factor(
        "event",
        1 + EVENT_IMPACT_WEIGHT * impact,
        {"name": strongest.name, "impact": impact},
    )


def _occupancy_factor(occupancy: float | None) -> Factor | None:
    if occupancy is None:
        return None
    if occupancy >= OCCUPANCY_HIGH_THRESHOLD:
        return Factor("high_occupancy", OCCUPANCY_HIGH_MULTIPLIER, {"occupancy": occupancy})
    if occupancy >= OCCUPANCY_MID_THRESHOLD:
        return Factor("mid_occupancy", OCCUPANCY_MID_MULTIPLIER, {"occupancy": occupancy})
    if occupancy <= OCCUPANCY_LOW_THRESHOLD:
        return Factor("low_occupancy", OCCUPANCY_LOW_MULTIPLIER, {"occupancy": occupancy})
    return None


def _position_factor(base_price: Decimal, median: Decimal | None) -> Factor | None:
    if median is None or median == 0:
        return None
    position = float((base_price - median) / median)
    if abs(position) <= POSITION_DEADBAND:
        return None
    gap = float((median - base_price) / base_price)
    adjustment = max(POSITION_MIN, min(POSITION_MAX, POSITION_WEIGHT * gap))
    key = "below_median" if position < 0 else "above_median"
    return Factor(key, 1 + adjustment, {"position": round(position, 2)})


def compute_recommendation(
    prop: Property,
    stay_date: datetime.date,
    market_day: MarketDay | None,
    events: list[Event],
) -> RecommendationDraft:
    if prop.base_price is None:
        raise ValueError(f"Obiekt {prop.id} nie ma ceny bazowej — wymagana dla rekomendacji")

    median = market_day.median_price if market_day else None
    occupancy = market_day.occupancy if market_day else None

    candidates = [
        _day_of_week_factor(stay_date),
        _season_factor(stay_date),
        _event_factor(stay_date, events),
        _occupancy_factor(occupancy),
        _position_factor(prop.base_price, median),
    ]
    factors = [f for f in candidates if f is not None]

    price = float(prop.base_price)
    for factor in factors:
        price *= factor.multiplier

    rounded = (Decimal(str(price)) / ROUND_TO).quantize(
        Decimal("1"), rounding=ROUND_HALF_UP
    ) * ROUND_TO
    clamped = max(prop.min_price, rounded)
    if prop.max_price is not None:
        clamped = min(prop.max_price, clamped)

    top = sorted(factors, key=lambda f: abs(f.multiplier - 1), reverse=True)
    top = top[:TOP_FACTORS_IN_EXPLANATION]
    return RecommendationDraft(
        stay_date=stay_date,
        price=clamped,
        previous_price=prop.base_price,
        factors=factors,
        explanation_template_key="v1",
        explanation_params={
            "factors": [
                {"key": f.key, "pct": round((f.multiplier - 1) * 100), **f.params}
                for f in top
            ],
            "median": str(median) if median is not None else None,
            "sample_size": market_day.sample_size if market_day else 0,
            "clamped": clamped != rounded,
        },
    )
