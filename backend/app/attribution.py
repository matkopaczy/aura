"""Licznik wyniku (§3 pkt 4): uczciwa atrybucja rekomendacji.

Po minięciu daty pobytu sprawdzamy, czy termin się sprzedał. Źródło prawdy
(B3): zaimportowane rezerwacje gospodarza (Booking) — znamy RZECZYWISTĄ cenę
sprzedaży, więc delta = cena_sprzedaży - poprzednia (prawdziwy uplift, nie
założenie). Fallback: iCal (sama zajętość, delta szacowana z rekomendacji),
gdy gospodarz nie zaimportował rezerwacji. Raportujemy "dodatkowy przychód
z zaakceptowanych podwyżek" — sumę dodatnich delt. Nigdy "zarobiliśmy Ci X".
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Booking,
    CalendarDay,
    Market,
    Property,
    Recommendation,
    RecommendationStatus,
)


def update_outcomes(db: Session, prop: Property) -> int:
    """Uzupełnia wynik (sprzedane/nie, delta) dla minionych, rozstrzygniętych dat.

    Zwraca liczbę zaktualizowanych rekomendacji.
    """
    market = db.get(Market, prop.market_id)
    today_local = datetime.datetime.now(ZoneInfo(market.timezone)).date()

    pending_outcome = db.scalars(
        select(Recommendation).where(
            Recommendation.property_id == prop.id,
            Recommendation.status == RecommendationStatus.ACCEPTED,
            Recommendation.outcome_sold.is_(None),
            Recommendation.stay_date < today_local,
        )
    ).all()
    if not pending_outcome:
        return 0

    pending_dates = [r.stay_date for r in pending_outcome]
    # Źródło prawdy: rzeczywiste rezerwacje z ceną (B3). Fallback: iCal (zajętość).
    booked_prices = dict(
        db.execute(
            select(Booking.stay_date, Booking.nightly_price).where(
                Booking.property_id == prop.id,
                Booking.stay_date.in_(pending_dates),
            )
        ).all()
    )
    booked_ical = set(
        db.scalars(
            select(CalendarDay.stay_date).where(
                CalendarDay.property_id == prop.id,
                CalendarDay.stay_date.in_(pending_dates),
            )
        )
    )
    for rec in pending_outcome:
        actual_price = booked_prices.get(rec.stay_date)
        rec.outcome_sold = actual_price is not None or rec.stay_date in booked_ical
        if rec.previous_price is None or not rec.outcome_sold:
            rec.revenue_delta = Decimal("0")
        elif actual_price is not None:
            # Prawdziwy uplift z rzeczywistej ceny sprzedaży (nie założenie).
            rec.revenue_delta = actual_price - rec.previous_price
        else:
            # Fallback iCal — delta szacowana z rekomendowanej ceny.
            rec.revenue_delta = rec.recommended_price - rec.previous_price
    db.commit()
    return len(pending_outcome)


@dataclass(frozen=True)
class AttributionSummary:
    accepted_count: int
    sold_count: int
    extra_revenue: Decimal  # wariant pełny: suma dodatnich delt sprzedanych podwyżek
    # Wariant konserwatywny (§3.4): liczymy tylko noce sprzedane przy cenie
    # ≥ mediana konkurencji w momencie rekomendacji. Odcina przypadki, w których
    # obiekt sprzedałby się i tak — najostrożniejsza dolna granica atrybucji.
    conservative_sold_count: int
    conservative_revenue: Decimal


def _positive_delta(rec: Recommendation) -> Decimal:
    return rec.revenue_delta if rec.revenue_delta and rec.revenue_delta > 0 else Decimal("0")


def _at_or_above_median(rec: Recommendation) -> bool:
    return rec.competitor_median is not None and rec.recommended_price >= rec.competitor_median


def summarize(
    db: Session, prop: Property, since: datetime.date | None = None
) -> AttributionSummary:
    query = select(Recommendation).where(
        Recommendation.property_id == prop.id,
        Recommendation.status == RecommendationStatus.ACCEPTED,
    )
    if since is not None:
        query = query.where(Recommendation.stay_date >= since)
    accepted = db.scalars(query).all()
    sold = [r for r in accepted if r.outcome_sold]
    extra = sum((_positive_delta(r) for r in sold), Decimal("0"))

    conservative = [r for r in sold if _at_or_above_median(r)]
    conservative_extra = sum((_positive_delta(r) for r in conservative), Decimal("0"))

    return AttributionSummary(
        accepted_count=len(accepted),
        sold_count=len(sold),
        extra_revenue=extra,
        conservative_sold_count=len(conservative),
        conservative_revenue=conservative_extra,
    )
