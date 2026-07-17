"""Zasilanie bazy eventów z oficjalnych, publicznych kalendarzy (Poziom 2, §3).

W przeciwieństwie do scrapingu cen: to źródła OFICJALNE (kalendarze miast,
terminarze targów/hal, platformy biletowe). Kandydaci trafiają jako DRAFT —
kurator zatwierdza w /admin/events. To nasz fosa i legalnie czyste (§6.4).
"""

import datetime
import re
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


# Dopełniacz polskich miesięcy ("18 lipca 2026") — wspólny dla źródeł
# parsujących daty słowne (mtp, pge, katowice, stulecia).
POLISH_GENITIVE_MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6,
    "lipca": 7, "sierpnia": 8, "września": 9, "wrzesnia": 9, "października": 10,
    "pazdziernika": 10, "listopada": 11, "grudnia": 12,
}


# Słowa w NAZWIE wydarzenia jednoznacznie wskazujące sport — dla źródeł aren,
# gdzie kategoria nie jest podana wprost (kurator i tak koryguje szkice).
SPORT_NAME_KEYWORDS = (
    "puchar", "mecz", "liga", " vs ", "boks", "mma", "mistrzostwa",
    "speedway", "world cup",
)


TARGI_NAME_KEYWORDS = ("targi", "expo", "jarmark")
KONFERENCJE_NAME_KEYWORDS = ("kongres", "konferencj", "forum", "summit")


def category_from_name(name: str, default: str = "koncert") -> tuple[str, float]:
    """Kategoria wnioskowana z nazwy wydarzenia (słowa kluczowe; kurator koryguje)."""
    lowered = name.lower()
    if any(keyword in lowered for keyword in SPORT_NAME_KEYWORDS):
        return map_category("sport")
    if any(keyword in lowered for keyword in TARGI_NAME_KEYWORDS):
        return map_category("targi")
    if any(keyword in lowered for keyword in KONFERENCJE_NAME_KEYWORDS):
        return map_category("konferencje")
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


def merge_consecutive_days(
    days: list[tuple[datetime.date, str]],
    venue: tuple[float, float],
    district: str | None,
) -> list[CandidateEvent]:
    """Ten sam tytuł w kolejnych dniach -> jeden event z zakresem dat.

    Dla kalendarzy pokazujących każde wystąpienie osobno (trasy dwudniowe,
    targi wielodniowe rozbite na dni).
    """
    by_title: dict[str, list[datetime.date]] = {}
    for date, title in days:
        by_title.setdefault(title, []).append(date)

    result: list[CandidateEvent] = []
    for title, dates in by_title.items():
        dates = sorted(set(dates))
        start = end = dates[0]
        ranges = []
        for date in dates[1:]:
            if (date - end).days == 1:
                end = date
            else:
                ranges.append((start, end))
                start = end = date
        ranges.append((start, end))
        category, impact = category_from_name(title)
        for start, end in ranges:
            result.append(
                CandidateEvent(
                    name=title,
                    category=category,
                    start_date=start,
                    end_date=end,
                    impact_strength=impact,
                    venue_lat=venue[0],
                    venue_lng=venue[1],
                    district=district,
                )
            )
    return result


def _series_key(name: str) -> str:
    """Prefiks serii: tekst przed pierwszym ':' lub '|' ('Lato na Pergoli: Joga')."""
    return re.split(r"[:|]", name, maxsplit=1)[0].strip().lower()


def drop_recurring_series(
    candidates: list[CandidateEvent], threshold: int = 4
) -> list[CandidateEvent]:
    """Odrzuca serie cykliczne (joga, jam session, cotygodniowe strefy).

    Ten sam prefiks tytułu >= threshold razy w jednej partii = zajęcia
    cykliczne venue, nie wydarzenie popytowe — nie zalewamy kuratora.
    """
    counts: dict[str, int] = {}
    for cand in candidates:
        key = _series_key(cand.name)
        counts[key] = counts.get(key, 0) + 1
    return [c for c in candidates if counts[_series_key(c.name)] < threshold]


class EventSource(ABC):
    """Źródło kandydatów na eventy dla jednego rynku."""

    source: str  # slug źródła, np. "mtp"
    market_slug: str  # rynek, do którego należą eventy

    @abstractmethod
    def fetch(self) -> list[CandidateEvent]:
        """Pobiera bieżące wydarzenia z publicznego kalendarza."""
