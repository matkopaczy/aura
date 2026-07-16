"""Onboarding "wklej link" (§3 pkt 2): z linku ogłoszenia do propozycji ceny.

v1 obsługuje Booking.com: pobieramy stronę obiektu (publiczna, jedna wizyta),
odczytujemy nazwę i współrzędne, dobieramy rynek po odległości od centrum
i proponujemy cenę bazową z mediany rynku na najbliższe 30 dni.
"""

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from playwright.sync_api import TimeoutError as PlaywrightTimeout
from playwright.sync_api import sync_playwright
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.geo import haversine_km
from app.models import Market
from app.monitoring import market_series
from app.scraping.booking import USER_AGENT

BOOKING_HOTEL_URL = re.compile(r"booking\.com/hotel/[a-z]{2}/[^/?#]+")


class ListingUnavailableError(Exception):
    """Nie udało się odczytać ogłoszenia (np. strona-wyzwanie anti-bot)."""


@dataclass(frozen=True)
class ListingInfo:
    name: str
    lat: float
    lng: float


def fetch_booking_listing(url: str) -> ListingInfo:
    if not BOOKING_HOTEL_URL.search(url):
        raise ValueError("Obsługujemy dziś linki do obiektów Booking.com (booking.com/hotel/...)")
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
        page = context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            # Kotwica mapy jest w DOM, ale bywa niewidoczna — czekamy na obecność.
            page.wait_for_selector("[data-atlas-latlng]", state="attached", timeout=30_000)
            latlng = page.get_attribute("[data-atlas-latlng]", "data-atlas-latlng")
            name = page.inner_text("h2")
        except PlaywrightTimeout as exc:
            # Booking bywa serwuje stronę-wyzwanie (anti-bot). Nie obchodzimy jej (§6.4)
            # — zgłaszamy czysty błąd, klient może wpisać dane ręcznie.
            raise ListingUnavailableError(url) from exc
        finally:
            context.close()
            browser.close()
    lat_text, lng_text = latlng.split(",")
    return ListingInfo(name=name.strip(), lat=float(lat_text), lng=float(lng_text))


def match_market(db: Session, lat: float, lng: float) -> Market | None:
    """Najbliższy rynek, w którego promieniu leży obiekt (geo, §6.2 pkt 2)."""
    best: tuple[float, Market] | None = None
    for market in db.scalars(select(Market)):
        distance = haversine_km(lat, lng, float(market.center_lat), float(market.center_lng))
        if distance <= float(market.radius_km) and (best is None or distance < best[0]):
            best = (distance, market)
    return best[1] if best else None


def propose_base_price(db: Session, market: Market) -> Decimal | None:
    """Mediana median rynku na 30 dni, w krokach po 5 zł."""
    series = market_series(db, market, days=30)
    medians = [float(day.median_price) for day in series if day.median_price is not None]
    if not medians:
        return None
    medians.sort()
    middle = medians[len(medians) // 2]
    return (Decimal(str(middle)) / 5).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * 5
