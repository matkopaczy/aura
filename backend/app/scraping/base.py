"""Wspólny interfejs adapterów źródeł danych (§6.2 pkt 6).

Nowy portal = nowy adapter implementujący SourceAdapter.
Nowy kraj = adaptery + wiersze w tabeli markets. Zero zmian w rdzeniu.

Zasady §6.4 (twarde): tylko dane publiczne, respektowanie robots.txt,
rate limit ~1 zapytanie / 2–3 s / domenę, praca nocna. Zbieramy wyłącznie:
ceny, dostępność, typ jednostki, rating, lokalizację ogólną, udogodnienia.
Żadnych zdjęć, opisów, treści opinii, danych osobowych.
"""

import datetime
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from decimal import Decimal

from app.models import Market


@dataclass(frozen=True)
class ObservedListing:
    """Obiekt konkurencji widoczny (dostępny) w wynikach dla danej daty pobytu."""

    source_listing_id: str
    price: Decimal
    currency_code: str
    unit_type: str | None = None
    rating: Decimal | None = None
    distance_center_km: Decimal | None = None
    amenities: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class DayObservation:
    """Wynik obserwacji rynku dla jednej daty pobytu.

    exhaustive=True tylko gdy widzieliśmy KOMPLET dostępnych obiektów
    (ostatnia strona wyników była niepełna). Wyłącznie wtedy wolno
    wnioskować "nieobecny w wynikach = niedostępny".
    """

    stay_date: datetime.date
    observed_at: datetime.datetime  # UTC
    listings: list[ObservedListing]
    exhaustive: bool = False


class SourceAdapter(ABC):
    """Adapter jednego portalu. Bezstanowy między wywołaniami;
    harmonogram i zapis do bazy to sprawa runnera."""

    #: slug źródła, np. "booking" — trafia do markets.active_sources
    #: i price_observations.source
    source: str

    @abstractmethod
    def observe_market(
        self, market: Market, stay_dates: list[datetime.date]
    ) -> Iterator[DayObservation]:
        """Dla każdej daty pobytu zwraca listę dostępnych obiektów z cenami.

        Obiekt nieobecny w wynikach traktujemy jako niedostępny w tej dacie
        (interpretacja należy do runnera).
        """


def get_adapter(source: str) -> SourceAdapter:
    from app.scraping.booking import BookingAdapter

    adapters: dict[str, type[SourceAdapter]] = {BookingAdapter.source: BookingAdapter}
    if source not in adapters:
        raise KeyError(f"Brak adaptera dla źródła: {source}")
    return adapters[source]()


@dataclass(frozen=True)
class FloorListing:
    """Obiekt ze źródła bez cen per-data — cena "od X zł" (bezdatowa)."""

    source_listing_id: str
    from_price: Decimal
    currency_code: str
    name: str | None = None
    rating: Decimal | None = None
    distance_center_km: Decimal | None = None


class FloorAdapter(ABC):
    """Adapter źródła "minimum rynku" (§6.4): tylko publiczny listing, bez cen
    per-data (te bywają za zabronionym w robots.txt endpointem). Osobny typ
    od SourceAdapter, bo kształt danych jest inny (§11 — bez wciskania na siłę)."""

    source: str

    @abstractmethod
    def fetch_floor(self, market: Market) -> list[FloorListing]:
        """Publiczny listing rynku → ceny "od" i metadane obiektów."""
