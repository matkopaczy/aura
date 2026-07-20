"""Prawdziwe metryki gospodarza z zaimportowanych rezerwacji (B2, §3.4).

ADR / obłożenie / RevPAR liczone z RZECZYWISTYCH sprzedaży (model Booking),
NIE modelowane jak u AirDNA. To jedyny uczciwy sposób pokazania tych liczb —
dostępny dopiero po imporcie rezerwacji gospodarza (B1).
"""

import datetime
from dataclasses import dataclass
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Booking, Market, Property


@dataclass(frozen=True)
class PropertyPerformance:
    window_days: int
    booked_nights: int
    adr: Decimal | None  # średnia cena za SPRZEDANĄ noc; None gdy brak sprzedaży
    occupancy: float  # obłożenie kalendarzowe = sprzedane noce / dni okna
    revpar: Decimal | None  # przychód na DOSTĘPNĄ noc = suma cen / dni okna
    currency_code: str


def compute_performance(
    db: Session,
    prop: Property,
    window_days: int = 30,
    today: datetime.date | None = None,
) -> PropertyPerformance:
    """Metryki za okno wstecz (minione noce). Obłożenie liczone kalendarzowo —
    sprzedane noce / dni okna (zakłada, że obiekt był wystawialny co noc; uczciwie
    NIE udajemy znajomości nocy zablokowanych przez gospodarza)."""
    market = db.get(Market, prop.market_id)
    today = today or datetime.datetime.now(ZoneInfo(market.timezone)).date()
    date_from = today - datetime.timedelta(days=window_days)

    nights = db.scalars(
        select(Booking).where(
            Booking.property_id == prop.id,
            Booking.stay_date >= date_from,
            Booking.stay_date < today,  # tylko minione noce
        )
    ).all()

    booked = len(nights)
    total_revenue = sum((b.nightly_price for b in nights), Decimal("0"))
    adr = (total_revenue / booked).quantize(Decimal("0.01")) if booked else None
    revpar = (total_revenue / window_days).quantize(Decimal("0.01")) if booked else None

    return PropertyPerformance(
        window_days=window_days,
        booked_nights=booked,
        adr=adr,
        occupancy=booked / window_days,
        revpar=revpar,
        currency_code=prop.currency_code,
    )
