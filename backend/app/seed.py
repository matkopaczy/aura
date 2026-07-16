"""Seed tabeli markets — rynek jako dane, nie kod (§6.2 pkt 2).

Uruchomienie: python -m app.seed
Idempotentny: upsert po slugu. Pierwsza fala rekomendacji (§5.1): Kraków,
Trójmiasto, Poznań. Pozostałe miasta wojewódzkie i turystyczne: monitoring.
"""

import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import CoverageLevel, Market

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_R = CoverageLevel.RECOMMENDATIONS
_M = CoverageLevel.MONITORING

# slug, nazwa (= fraza wyszukiwania w OTA), lat, lng, promień km, poziom
MARKETS: list[tuple[str, str, float, float, float, CoverageLevel]] = [
    # Pierwsza fala rekomendacji
    ("krakow", "Kraków", 50.0614, 19.9366, 12.0, _R),
    ("trojmiasto", "Trójmiasto", 54.4416, 18.5601, 20.0, _R),
    ("poznan", "Poznań", 52.4064, 16.9252, 12.0, _R),
    # Miasta wojewódzkie — monitoring
    ("warszawa", "Warszawa", 52.2297, 21.0122, 15.0, _M),
    ("wroclaw", "Wrocław", 51.1079, 17.0385, 12.0, _M),
    ("lodz", "Łódź", 51.7592, 19.4560, 12.0, _M),
    ("szczecin", "Szczecin", 53.4285, 14.5528, 12.0, _M),
    ("bydgoszcz", "Bydgoszcz", 53.1235, 18.0084, 10.0, _M),
    ("torun", "Toruń", 53.0138, 18.5984, 8.0, _M),
    ("lublin", "Lublin", 51.2465, 22.5684, 10.0, _M),
    ("bialystok", "Białystok", 53.1325, 23.1688, 10.0, _M),
    ("katowice", "Katowice", 50.2649, 19.0238, 12.0, _M),
    ("kielce", "Kielce", 50.8661, 20.6286, 8.0, _M),
    ("olsztyn", "Olsztyn", 53.7784, 20.4801, 8.0, _M),
    ("opole", "Opole", 50.6751, 17.9213, 8.0, _M),
    ("rzeszow", "Rzeszów", 50.0412, 21.9991, 8.0, _M),
    ("gorzow-wielkopolski", "Gorzów Wielkopolski", 52.7368, 15.2288, 8.0, _M),
    ("zielona-gora", "Zielona Góra", 51.9356, 15.5062, 8.0, _M),
    # Główne miejscowości turystyczne — monitoring
    ("zakopane", "Zakopane", 49.2992, 19.9496, 8.0, _M),
    ("kolobrzeg", "Kołobrzeg", 54.1755, 15.5835, 8.0, _M),
    ("swinoujscie", "Świnoujście", 53.9105, 14.2478, 8.0, _M),
    ("karpacz", "Karpacz", 50.7794, 15.7530, 6.0, _M),
    ("szklarska-poreba", "Szklarska Poręba", 50.8273, 15.5211, 6.0, _M),
    ("wisla", "Wisła", 49.6563, 18.8592, 6.0, _M),
    ("szczyrk", "Szczyrk", 49.7186, 19.0292, 6.0, _M),
    ("krynica-zdroj", "Krynica-Zdrój", 49.4216, 20.9599, 6.0, _M),
    ("ustka", "Ustka", 54.5805, 16.8614, 6.0, _M),
    ("wladyslawowo", "Władysławowo", 54.7906, 18.4034, 8.0, _M),
    ("mielno", "Mielno", 54.2599, 16.0625, 6.0, _M),
]


def seed_markets(db: Session) -> None:
    existing = {m.slug: m for m in db.scalars(select(Market))}
    created = 0
    for slug, name, lat, lng, radius, coverage in MARKETS:
        market = existing.get(slug)
        if market is None:
            market = Market(
                slug=slug,
                name=name,
                country_code="PL",
                currency_code="PLN",
                timezone="Europe/Warsaw",
                language="pl",
                coverage_level=coverage,
                center_lat=Decimal(str(lat)),
                center_lng=Decimal(str(lng)),
                radius_km=Decimal(str(radius)),
                active_sources=["booking"],
            )
            db.add(market)
            created += 1
        else:
            market.coverage_level = coverage
    db.commit()
    logger.info("Seed rynków: %d nowych, %d razem", created, len(MARKETS))


if __name__ == "__main__":
    from sqlalchemy.orm import Session as _Session

    with _Session(get_engine()) as session:
        seed_markets(session)
