"""Wspólny interfejs adapterów źródeł danych (§6.2 pkt 6).

Nowy portal = nowy adapter implementujący SourceAdapter.
Nowy kraj = adaptery + wiersze w tabeli markets. Zero zmian w rdzeniu.

Implementacje (Booking.com jako pierwsza) powstają w Sprincie 1 i muszą
przestrzegać zasad §6.4: tylko dane publiczne, rate limit, praca nocna,
robots.txt; zbieramy wyłącznie ceny, dostępność, typ jednostki, rating,
lokalizację ogólną i udogodnienia.
"""

import datetime
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from decimal import Decimal

from app.models import Market


@dataclass(frozen=True)
class ListingSnapshot:
    """Obiekt konkurencji znaleziony w źródle."""

    source_listing_id: str
    unit_type: str | None
    rating: Decimal | None
    lat: float | None
    lng: float | None
    amenities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PriceSnapshot:
    """Cena/dostępność dla jednej daty pobytu."""

    source_listing_id: str
    stay_date: datetime.date
    price: Decimal | None  # None gdy termin niedostępny
    currency_code: str
    available: bool
    observed_at: datetime.datetime  # UTC


class SourceAdapter(ABC):
    """Adapter jednego portalu. Bezstanowy; harmonogram i zapis to sprawa wywołującego."""

    #: slug źródła, np. "booking" — trafia do markets.active_sources i price_observations.source
    source: str

    @abstractmethod
    def discover_listings(self, market: Market) -> list[ListingSnapshot]:
        """Znajduje obiekty konkurencji w obszarze rynku."""

    @abstractmethod
    def fetch_prices(
        self,
        market: Market,
        source_listing_ids: list[str],
        date_from: datetime.date,
        date_to: datetime.date,
    ) -> list[PriceSnapshot]:
        """Pobiera ceny i dostępność dla zakresu dat pobytu."""


def get_adapter(source: str) -> SourceAdapter:
    """Rejestr adapterów. Sprint 1 doda adapter Booking.com."""
    raise NotImplementedError(f"Brak adaptera dla źródła: {source}")
