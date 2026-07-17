"""Zasilanie bazy eventów z oficjalnych, publicznych kalendarzy (Poziom 2, §3).

W przeciwieństwie do scrapingu cen: to źródła OFICJALNE (kalendarze miast,
terminarze targów/hal, platformy biletowe). Kandydaci trafiają jako DRAFT —
kurator zatwierdza w /admin/events. To nasz fosa i legalnie czyste (§6.4).
"""

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass

# Domyślna siła wpływu per kategoria (kurator koryguje). Targi/sport najsilniej
# podbijają popyt hotelowy; spektakle najsłabiej.
CATEGORY_IMPACT = {
    "targi": 0.7, "sport": 0.7, "koncert": 0.6, "koncerty": 0.6,
    "konferencje": 0.5, "eventy": 0.4, "spektakle": 0.3,
}


def map_category(cat_text: str, default: str = "eventy") -> tuple[str, float]:
    """Tekst kategorii -> (slug kategorii, domyślna siła wpływu)."""
    key = cat_text.strip().lower()
    for slug, impact in CATEGORY_IMPACT.items():
        if key.startswith(slug[:6]):
            return slug, impact
    return default, CATEGORY_IMPACT.get(default, 0.4)


# Słowa w NAZWIE wydarzenia jednoznacznie wskazujące sport — dla źródeł aren,
# gdzie kategoria nie jest podana wprost (kurator i tak koryguje szkice).
SPORT_NAME_KEYWORDS = (
    "puchar", "mecz", "liga", " vs ", "boks", "mma", "mistrzostwa",
    "speedway", "world cup",
)


def category_from_name(name: str, default: str = "koncert") -> tuple[str, float]:
    """Kategoria wnioskowana z nazwy wydarzenia (sport po słowach kluczowych)."""
    lowered = name.lower()
    if any(keyword in lowered for keyword in SPORT_NAME_KEYWORDS):
        return map_category("sport")
    return map_category("", default=default)


@dataclass(frozen=True)
class CandidateEvent:
    name: str
    category: str
    start_date: datetime.date
    end_date: datetime.date
    impact_strength: float
    venue_lat: float | None
    venue_lng: float | None
    district: str | None = None


class EventSource(ABC):
    """Źródło kandydatów na eventy dla jednego rynku."""

    source: str  # slug źródła, np. "mtp"
    market_slug: str  # rynek, do którego należą eventy

    @abstractmethod
    def fetch(self) -> list[CandidateEvent]:
        """Pobiera bieżące wydarzenia z publicznego kalendarza."""
