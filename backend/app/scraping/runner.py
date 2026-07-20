"""Orkiestracja scrapingu: adapter → upsert listingów → obserwacje cen.

Mapowanie konkurentów do rynku: wyszukiwanie jest zawężone do miasta rynku
(kontekst geo), a odległość od centrum z karty wyników zapisujemy per listing.
Obiekt znany rynkowi, ale nieobecny w wynikach dla danej daty = niedostępny.
"""

import datetime
import logging
import statistics
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import CompetitorListing, FloorSignal, Market, MarketSupply, PriceObservation
from app.scraping.base import DayObservation, FloorAdapter, SourceAdapter, get_adapter

logger = logging.getLogger(__name__)


def scrape_market_floor(db: Session, market: Market, adapter: FloorAdapter) -> int:
    """Sygnał "minimum rynku" ze źródła bezdatowego (np. nocowanie.pl).

    Agreguje ceny "od" do min + mediany + liczby próbek i zapisuje JEDEN wiersz
    FloorSignal. Świadomie osobne od price_observations (per-data) — §6.4/§11.
    Zwraca liczbę obiektów w próbce (0 = nic nie zapisano).
    """
    listings = adapter.fetch_floor(market)
    prices = [float(item.from_price) for item in listings]
    if not prices:
        logger.info("floor %s/%s: pusta próbka", market.slug, adapter.source)
        return 0
    db.add(
        FloorSignal(
            market_id=market.id,
            source=adapter.source,
            min_price=Decimal(str(min(prices))),
            median_price=Decimal(str(statistics.median(prices))),
            sample_size=len(prices),
            currency_code=market.currency_code,
            observed_at=datetime.datetime.now(datetime.UTC),
        )
    )
    db.commit()
    logger.info(
        "floor %s/%s: min=%s mediana=%s próbka=%d",
        market.slug, adapter.source, min(prices), statistics.median(prices), len(prices),
    )
    return len(prices)


def stay_dates_for_market(market: Market, days_ahead: int) -> list[datetime.date]:
    """Horyzont od jutra w strefie czasowej rynku (§6.2 pkt 4)."""
    today_local = datetime.datetime.now(ZoneInfo(market.timezone)).date()
    return [today_local + datetime.timedelta(days=i) for i in range(1, days_ahead + 1)]


def market_supply_from_totals(totals: list[int | None]) -> int | None:
    """Redukuje dzienne "znaleziono N obiektów" do jednej podaży rynku (A5).

    Nagłówek jest liczony per data pobytu, więc N zmienia się dzień po dniu
    (data o wysokiej dostępności odsłania więcej ofert). Bierzemy MAKSIMUM —
    szczyt najlepiej przybliża realny inwentarz rynku (data z najmniejszą
    liczbą blokad = najbliżej pełnej podaży). Daty z anty-botem dają None i
    są pomijane. Alternatywa: mediana (typowa, odporna na wyskok, lekko zaniża).
    """
    valid = [t for t in totals if t is not None]
    return max(valid) if valid else None


def scrape_market(
    db: Session, market: Market, days_ahead: int = 60, guests: int = 2
) -> int:
    """Pełny przebieg dla rynku. guests=2 = główny nocny skan; guests=1 = lekki
    przebieg pokoi 1-osobowych (płytki, krótszy horyzont — §6.4). Zwraca liczbę
    zapisanych obserwacji."""
    observation_count = 0
    for source in market.active_sources:
        # Głęboki skan i migawka podaży tylko dla głównego przebiegu 2-os.;
        # przebieg 1-os. jest lekki i nie nadpisuje podaży rynku (inna próbka).
        adapter = get_adapter(source, guests=guests, deep_scan=(guests == 2))
        dates = stay_dates_for_market(market, days_ahead)
        totals: list[int | None] = []
        for day in adapter.observe_market(market, dates):
            observation_count += _store_day(db, market, adapter, day, guests=guests)
            totals.append(day.results_total)
            db.commit()  # commit per data pobytu — częściowy przebieg też ma wartość
        if guests == 2:
            _store_supply(db, market, adapter.source, totals)
    return observation_count


def _store_supply(db: Session, market: Market, source: str, totals: list[int | None]) -> None:
    """Zapisuje JEDNĄ migawkę podaży rynku per przebieg (A5). Brak danych = nic."""
    supply = market_supply_from_totals(totals)
    if supply is None:
        return
    db.add(
        MarketSupply(
            market_id=market.id,
            source=source,
            total_listings=supply,
            observed_at=datetime.datetime.now(datetime.UTC),
        )
    )
    db.commit()
    logger.info("podaż %s/%s: %d ofert", market.slug, source, supply)


def _store_day(
    db: Session, market: Market, adapter: SourceAdapter, day: DayObservation, guests: int = 2
) -> int:
    known = {
        listing.source_listing_id: listing
        for listing in db.scalars(
            select(CompetitorListing).where(
                CompetitorListing.market_id == market.id,
                CompetitorListing.source == adapter.source,
            )
        )
    }

    seen_ids: set[str] = set()
    for observed in day.listings:
        seen_ids.add(observed.source_listing_id)
        listing = known.get(observed.source_listing_id)
        if listing is None:
            listing = CompetitorListing(
                market_id=market.id,
                source=adapter.source,
                source_listing_id=observed.source_listing_id,
            )
            db.add(listing)
            known[observed.source_listing_id] = listing
        listing.unit_type = observed.unit_type
        listing.rating = observed.rating
        listing.distance_center_km = observed.distance_center_km
        if observed.amenities:
            listing.amenities = observed.amenities
        db.flush()
        db.add(
            PriceObservation(
                listing_id=listing.id,
                stay_date=day.stay_date,
                price=observed.price,
                currency_code=observed.currency_code,
                available=True,
                observed_at=day.observed_at,
                source=adapter.source,
                guests=guests,
            )
        )

    # "Nieobecny = niedostępny" tylko przy skanie wyczerpującym — inaczej
    # brak w wynikach to zwykle artefakt sortowania/stronicowania, nie zajętość.
    unseen = (
        [listing for sid, listing in known.items() if sid not in seen_ids]
        if day.exhaustive
        else []
    )
    for listing in unseen:
        db.add(
            PriceObservation(
                listing_id=listing.id,
                stay_date=day.stay_date,
                price=None,
                currency_code=market.currency_code,
                available=False,
                observed_at=day.observed_at,
                source=adapter.source,
                guests=guests,
            )
        )

    logger.info(
        "market=%s date=%s dostępne=%d niedostępne=%d",
        market.slug,
        day.stay_date,
        len(seen_ids),
        len(unseen),
    )
    return len(day.listings) + len(unseen)
