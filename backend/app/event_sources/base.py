"""Zasilanie bazy eventów z oficjalnych, publicznych kalendarzy (Poziom 2, §3).

W przeciwieństwie do scrapingu cen: to źródła OFICJALNE (kalendarze miast,
terminarze targów/hal, platformy biletowe). Kandydaci trafiają jako DRAFT —
kurator zatwierdza w /admin/events. To nasz fosa i legalnie czyste (§6.4).
"""

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass


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
