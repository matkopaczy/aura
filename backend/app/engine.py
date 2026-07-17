"""Silnik rekomendacji v1 — regułowy, przejrzysty (§7.1).

Cena = cena bazowa klienta × iloczyn czynników, z twardym ograniczeniem
min/max. Każdy czynnik zapisuje swój wkład; wyjaśnienie to top 3 czynniki
jako klucz szablonu + parametry — nigdy sklejane zdania (§6.2 pkt 5).

Stałe strojenia zebrane na górze — kalibracja per rynek w pilocie.
"""

import datetime
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.geo import haversine_km
from app.models import Event, Property
from app.monitoring import MarketDay

WEEKEND_MULTIPLIER = 1.10  # piątek, sobota
SUNDAY_MULTIPLIER = 0.95
HIGH_SEASON_MONTHS = {6, 7, 8}
HIGH_SEASON_MULTIPLIER = 1.10
LOW_SEASON_MONTHS = {1, 2, 11}  # grudzień obsługują eventy (święta, sylwester)
LOW_SEASON_MULTIPLIER = 0.95
EVENT_IMPACT_WEIGHT = 0.4  # event o sile 1.0 -> +40%
# Zanik wpływu eventu z odległością obiektu od miejsca wydarzenia (§ event-distance).
EVENT_VENUE_NEAR_KM = 1.5  # do tej odległości pełny wpływ
EVENT_VENUE_FAR_KM = 6.0  # od tej odległości tylko resztkowy, ogólnomiejski
EVENT_VENUE_FLOOR = 0.30  # duży event i tak lekko podnosi cały rynek
OCCUPANCY_HIGH_THRESHOLD, OCCUPANCY_HIGH_MULTIPLIER = 0.7, 1.15
OCCUPANCY_MID_THRESHOLD, OCCUPANCY_MID_MULTIPLIER = 0.5, 1.08
OCCUPANCY_LOW_THRESHOLD, OCCUPANCY_LOW_MULTIPLIER = 0.2, 0.95
# Tempo wypełniania rynku (§7.2): obłożenie = poziom, pace = prędkość zmiany.
# Rynek szybko się zapełnia -> podnieś wcześniej; zwalnia -> odpuść.
PACE_UP_THRESHOLD, PACE_UP_MULTIPLIER = 0.10, 1.08
PACE_DOWN_THRESHOLD, PACE_DOWN_MULTIPLIER = -0.10, 0.96
ORPHAN_MULTIPLIER = 0.92  # wolna noc między rezerwacjami — rabat, by wypełnić lukę
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
    # Mediana konkurencji użyta do pozycjonowania — pod licznik konserwatywny (§3.4).
    # None, gdy brak danych rynkowych (wtedy nie wliczamy do wariantu konserwatywnego).
    competitor_median: Decimal | None = None


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


def _venue_proximity(prop: Property, event: Event) -> tuple[float, float | None]:
    """Zwraca (współczynnik bliskości, odległość_km lub None).

    Event bez venue = ogólnomiejski: pełny wpływ (1.0), brak odległości.
    Z venue: pełny do NEAR, liniowo do FLOOR na FAR, dalej FLOOR (§ event-distance).
    """
    if event.venue_lat is None or event.venue_lng is None:
        return 1.0, None
    distance = haversine_km(
        float(prop.lat), float(prop.lng), float(event.venue_lat), float(event.venue_lng)
    )
    if distance <= EVENT_VENUE_NEAR_KM:
        proximity = 1.0
    elif distance >= EVENT_VENUE_FAR_KM:
        proximity = EVENT_VENUE_FLOOR
    else:
        span = EVENT_VENUE_FAR_KM - EVENT_VENUE_NEAR_KM
        proximity = 1.0 - (1.0 - EVENT_VENUE_FLOOR) * (distance - EVENT_VENUE_NEAR_KM) / span
    return proximity, distance


def _event_factor(
    prop: Property, stay_date: datetime.date, events: list[Event]
) -> Factor | None:
    overlapping = [e for e in events if e.start_date <= stay_date <= e.end_date]
    if not overlapping:
        return None
    # Wybór po wpływie EFEKTYWNYM (siła × bliskość) — bliskie targi wygrywają z
    # odległym meczem, nawet jeśli mecz ma wyższą surową siłę.
    scored = [
        (float(e.impact_strength) * _venue_proximity(prop, e)[0], e) for e in overlapping
    ]
    _, strongest = max(scored, key=lambda pair: pair[0])
    proximity, distance = _venue_proximity(prop, strongest)
    effective_impact = float(strongest.impact_strength) * proximity
    params: dict = {"name": strongest.name, "impact": round(effective_impact, 2)}
    if distance is not None:
        params["venue_distance_km"] = round(distance, 1)
    return Factor("event", 1 + EVENT_IMPACT_WEIGHT * effective_impact, params)


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


def _booking_pace_factor(pace: float | None) -> Factor | None:
    """Tempo wypełniania rynku (§7.2). Poziom obłożenia obsługuje occupancy;
    tu liczy się prędkość: rynek szybko się zapełnia -> podnieś wcześniej."""
    if pace is None:
        return None
    if pace >= PACE_UP_THRESHOLD:
        return Factor("booking_pace_up", PACE_UP_MULTIPLIER, {"pace": round(pace, 2)})
    if pace <= PACE_DOWN_THRESHOLD:
        return Factor("booking_pace_down", PACE_DOWN_MULTIPLIER, {"pace": round(pace, 2)})
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


def _orphan_night_factor(is_orphan: bool) -> Factor | None:
    if not is_orphan:
        return None
    return Factor("orphan_night", ORPHAN_MULTIPLIER, {})


def compute_recommendation(
    prop: Property,
    stay_date: datetime.date,
    market_day: MarketDay | None,
    events: list[Event],
    is_orphan: bool = False,
    position_median: Decimal | None = None,
) -> RecommendationDraft:
    if prop.base_price is None:
        raise ValueError(f"Obiekt {prop.id} nie ma ceny bazowej — wymagana dla rekomendacji")

    occupancy = market_day.occupancy if market_day else None
    pace = market_day.booking_pace if market_day else None
    # Pozycja liczona względem mediany segmentowej (ten sam typ obiektu), gdy podana;
    # inaczej mediana całego rynku (bezpieczny fallback — § mediana segmentowa).
    median = position_median if position_median is not None else (
        market_day.median_price if market_day else None
    )

    candidates = [
        _day_of_week_factor(stay_date),
        _season_factor(stay_date),
        _event_factor(prop, stay_date, events),
        _occupancy_factor(occupancy),
        _booking_pace_factor(pace),
        _position_factor(prop.base_price, median),
        _orphan_night_factor(is_orphan),
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
        competitor_median=median,
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
