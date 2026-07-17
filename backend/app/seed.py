"""Seed tabel markets i events — rynek jako dane, nie kod (§6.2 pkt 2).

Uruchomienie: python -m app.seed
Idempotentny: markets po slugu, events po (market, nazwa, data startu).
Pierwsza fala rekomendacji (§5.1): Kraków, Trójmiasto, Poznań.

Eventy: święta ustawowe i długie weekendy (daty pewne) = approved;
festiwale/targi z niepotwierdzonymi datami = draft, do panelu kuracji.
"""

import datetime
import logging
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_engine
from app.models import CoverageLevel, CurationStatus, Event, Market

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_R = CoverageLevel.RECOMMENDATIONS
_M = CoverageLevel.MONITORING

# slug, nazwa (= fraza wyszukiwania w OTA), lat, lng, promień km, poziom
# Decyzja założyciela (2026-07-17): rekomendacje we WSZYSTKICH rynkach
# (miasta wojewódzkie + kurorty). Czynnik eventów poza pierwszą falą zasilany
# ręczną kuracją do czasu dodania źródeł per miasto.
MARKETS: list[tuple[str, str, float, float, float, CoverageLevel]] = [
    # Pierwsza fala rekomendacji (mają też automatyczne źródła eventów).
    # Trójmiasto rozbite na osobne rynki (decyzja założyciela 2026-07-17):
    # gospodarz konkuruje w swoim mieście, a SEO szuka "Gdańsk", nie "Trójmiasto".
    ("krakow", "Kraków", 50.0614, 19.9366, 12.0, _R),
    ("gdansk", "Gdańsk", 54.3520, 18.6466, 10.0, _R),
    ("gdynia", "Gdynia", 54.5189, 18.5305, 8.0, _R),
    ("sopot", "Sopot", 54.4418, 18.5601, 5.0, _R),
    ("poznan", "Poznań", 52.4064, 16.9252, 12.0, _R),
    # Miasta wojewódzkie
    ("warszawa", "Warszawa", 52.2297, 21.0122, 15.0, _R),
    ("wroclaw", "Wrocław", 51.1079, 17.0385, 12.0, _R),
    ("lodz", "Łódź", 51.7592, 19.4560, 12.0, _R),
    ("szczecin", "Szczecin", 53.4285, 14.5528, 12.0, _R),
    ("bydgoszcz", "Bydgoszcz", 53.1235, 18.0084, 10.0, _R),
    ("torun", "Toruń", 53.0138, 18.5984, 8.0, _R),
    ("lublin", "Lublin", 51.2465, 22.5684, 10.0, _R),
    ("bialystok", "Białystok", 53.1325, 23.1688, 10.0, _R),
    ("katowice", "Katowice", 50.2649, 19.0238, 12.0, _R),
    ("kielce", "Kielce", 50.8661, 20.6286, 8.0, _R),
    ("olsztyn", "Olsztyn", 53.7784, 20.4801, 8.0, _R),
    ("opole", "Opole", 50.6751, 17.9213, 8.0, _R),
    ("rzeszow", "Rzeszów", 50.0412, 21.9991, 8.0, _R),
    ("gorzow-wielkopolski", "Gorzów Wielkopolski", 52.7368, 15.2288, 8.0, _R),
    ("zielona-gora", "Zielona Góra", 51.9356, 15.5062, 8.0, _R),
    # Główne miejscowości turystyczne
    ("zakopane", "Zakopane", 49.2992, 19.9496, 8.0, _R),
    ("kolobrzeg", "Kołobrzeg", 54.1755, 15.5835, 8.0, _R),
    ("swinoujscie", "Świnoujście", 53.9105, 14.2478, 8.0, _R),
    ("karpacz", "Karpacz", 50.7794, 15.7530, 6.0, _R),
    ("szklarska-poreba", "Szklarska Poręba", 50.8273, 15.5211, 6.0, _R),
    ("wisla", "Wisła", 49.6563, 18.8592, 6.0, _R),
    ("szczyrk", "Szczyrk", 49.7186, 19.0292, 6.0, _R),
    ("krynica-zdroj", "Krynica-Zdrój", 49.4216, 20.9599, 6.0, _R),
    ("ustka", "Ustka", 54.5805, 16.8614, 6.0, _R),
    ("wladyslawowo", "Władysławowo", 54.7906, 18.4034, 8.0, _R),
    ("mielno", "Mielno", 54.2599, 16.0625, 6.0, _R),
]


_APPROVED = CurationStatus.APPROVED
_DRAFT = CurationStatus.DRAFT
_D = datetime.date

# Święta i długie weekendy — ogólnopolskie, te same daty dla wszystkich rynków.
# (nazwa, kategoria, start, koniec, siła wpływu, status)
NATIONAL_EVENTS: list[tuple[str, str, datetime.date, datetime.date, float, CurationStatus]] = [
    ("Weekend z Wniebowzięciem NMP", "dlugi-weekend",
     _D(2026, 8, 14), _D(2026, 8, 16), 0.7, _APPROVED),
    ("Wszystkich Świętych", "swieto", _D(2026, 10, 30), _D(2026, 11, 1), 0.4, _APPROVED),
    ("Święto Niepodległości", "swieto", _D(2026, 11, 10), _D(2026, 11, 11), 0.5, _APPROVED),
    ("Boże Narodzenie", "swieto", _D(2026, 12, 24), _D(2026, 12, 27), 0.6, _APPROVED),
    ("Sylwester i Nowy Rok", "dlugi-weekend",
     _D(2026, 12, 30), _D(2027, 1, 1), 0.9, _APPROVED),
    ("Trzech Króli", "swieto", _D(2027, 1, 5), _D(2027, 1, 6), 0.4, _APPROVED),
    ("Wielkanoc", "swieto", _D(2027, 3, 26), _D(2027, 3, 29), 0.6, _APPROVED),
    ("Majówka", "dlugi-weekend", _D(2027, 4, 30), _D(2027, 5, 3), 0.95, _APPROVED),
    ("Boże Ciało — długi weekend", "dlugi-weekend",
     _D(2027, 5, 26), _D(2027, 5, 30), 0.85, _APPROVED),
]

# Eventy lokalne — daty 2026/27 do potwierdzenia przez kuratora (draft).
# (market_slug, nazwa, kategoria, dzielnica, start, koniec, siła, status)
CITY_EVENTS: list[tuple] = [
    ("krakow", "Unsound Festival", "festiwal", None,
     _D(2026, 10, 4), _D(2026, 10, 11), 0.6, _DRAFT),
    ("krakow", "Jarmark Bożonarodzeniowy", "jarmark", "Stare Miasto",
     _D(2026, 11, 27), _D(2026, 12, 26), 0.5, _DRAFT),
    ("krakow", "Juwenalia", "juwenalia", None,
     _D(2027, 5, 13), _D(2027, 5, 16), 0.5, _DRAFT),
    ("krakow", "Wianki", "festiwal", "Stare Miasto",
     _D(2027, 6, 19), _D(2027, 6, 19), 0.6, _DRAFT),
    ("poznan", "Poznań Game Arena", "targi", "Grunwald",
     _D(2026, 10, 9), _D(2026, 10, 11), 0.7, _DRAFT),
    ("poznan", "Budma", "targi", "Grunwald",
     _D(2027, 2, 2), _D(2027, 2, 5), 0.7, _DRAFT),
    ("poznan", "Malta Festival", "festiwal", None,
     _D(2027, 6, 18), _D(2027, 6, 27), 0.6, _DRAFT),
    ("gdansk", "Jarmark św. Dominika", "jarmark", "Śródmieście",
     _D(2026, 7, 25), _D(2026, 8, 16), 0.7, _DRAFT),
    ("gdansk", "Jarmark Bożonarodzeniowy", "jarmark", "Śródmieście",
     _D(2026, 11, 20), _D(2026, 12, 23), 0.5, _DRAFT),
    ("gdynia", "Open'er Festival", "festiwal", None,
     _D(2027, 6, 30), _D(2027, 7, 3), 0.9, _DRAFT),
]

# Ferie zimowe 2026/2027 wg MEN (trzy tury, kalendarz oficjalny) — §3:
# dla kurortów to najsilniejszy popyt zimy. Deterministyczne dane urzędowe,
# status APPROVED z definicji. (nazwa, start, koniec)
FERIE_2027: list[tuple[str, datetime.date, datetime.date]] = [
    ("Ferie zimowe — tura 1 (podkarpackie, podlaskie, dolnośląskie, łódzkie, śląskie, opolskie)",
     _D(2027, 1, 18), _D(2027, 1, 31)),
    ("Ferie zimowe — tura 2 (mazowieckie, pomorskie, świętokrzyskie, lubelskie)",
     _D(2027, 2, 1), _D(2027, 2, 14)),
    ("Ferie zimowe — tura 3 (lubuskie, kujawsko-pomorskie, warmińsko-mazurskie, wielkopolskie, zachodniopomorskie, małopolskie)",
     _D(2027, 2, 15), _D(2027, 2, 28)),
]

# Rynki, gdzie ferie realnie podnoszą popyt: góry mocno, uzdrowiska nad morzem
# umiarkowanie. Miasta pomijamy (ferie = odpływ, nie napływ) — bez zgadywania.
FERIE_IMPACT: dict[str, float] = {
    "zakopane": 0.75, "karpacz": 0.75, "szklarska-poreba": 0.75,
    "wisla": 0.75, "szczyrk": 0.75, "krynica-zdroj": 0.7,
    "kolobrzeg": 0.35, "swinoujscie": 0.35,
}

# Współrzędne miejsca wydarzenia dla eventów punktowych (§ event-distance).
# (slug, nazwa) -> (lat, lng). Brak wpisu = event ogólnomiejski (bez venue).
VENUES: dict[tuple[str, str], tuple[float, float]] = {
    ("poznan", "Poznań Game Arena"): (52.3939, 16.8820),  # MTP
    ("poznan", "Budma"): (52.3939, 16.8820),  # MTP
    ("poznan", "Malta Festival"): (52.4030, 16.9660),  # Jezioro Malta
    ("gdynia", "Open'er Festival"): (54.5790, 18.4890),  # Gdynia-Kosakowo
    ("gdansk", "Jarmark św. Dominika"): (54.3490, 18.6530),  # Główne Miasto
    ("krakow", "Wianki"): (50.0540, 19.9350),  # Wawel / bulwary
    ("krakow", "Jarmark Bożonarodzeniowy"): (50.0617, 19.9373),  # Rynek Główny
}


def seed_events(db: Session) -> None:
    markets = {m.slug: m for m in db.scalars(select(Market))}
    existing = {
        (e.market_id, e.name, e.start_date) for e in db.scalars(select(Event))
    }
    created = 0

    def add(market: Market, name: str, category: str, district: str | None,
            start: datetime.date, end: datetime.date, impact: float,
            status: CurationStatus) -> None:
        nonlocal created
        if (market.id, name, start) in existing:
            return
        venue = VENUES.get((market.slug, name))
        db.add(Event(
            market_id=market.id, name=name, category=category, district=district,
            start_date=start, end_date=end, impact_strength=impact,
            source="kurator-seed", curation_status=status,
            venue_lat=venue[0] if venue else None,
            venue_lng=venue[1] if venue else None,
        ))
        created += 1

    # Święta ogólnopolskie do KAŻDEGO rynku — działają wszędzie tak samo.
    for market in markets.values():
        for name, category, start, end, impact, status in NATIONAL_EVENTS:
            add(market, name, category, None, start, end, impact, status)
    # Ferie zimowe do rynków zimowych (kalendarz MEN — dane urzędowe).
    for slug, impact in FERIE_IMPACT.items():
        for name, start, end in FERIE_2027:
            add(markets[slug], name, "ferie", None, start, end, impact, _APPROVED)
    for slug, name, category, district, start, end, impact, status in CITY_EVENTS:
        add(markets[slug], name, category, district, start, end, impact, status)

    db.commit()
    logger.info("Seed eventów: %d nowych", created)


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
        seed_events(session)
