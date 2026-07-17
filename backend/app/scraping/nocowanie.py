"""Adapter nocowanie.pl — sygnał "minimum rynku" (§6.4).

Scrapujemy WYŁĄCZNIE publiczny listing miasta (`/noclegi/<slug>/`), który
robots.txt dopuszcza. Ceny per-data siedzą za pluginem dostępności, który
robots.txt JAWNIE blokuje (`/plugin/_obiekty_uslugi_frontend_Dostepnosc/`) —
NIE dotykamy go. Stąd tylko cena bezdatowa jako sygnał floor.

Selektory i format ceny zweryfikowane na żywo 2026-07-16 headless
(karty `article` + `[data-id]`, cena tuż przed "za N noc").
"""

import re
from decimal import Decimal

from playwright.sync_api import sync_playwright

from app.models import Market
from app.robots import read_robots
from app.scraping.base import FloorAdapter, FloorListing
from app.scraping.booking import USER_AGENT

BASE_URL = "https://www.nocowanie.pl"

# Cena = liczba tuż przed "za N noc" (finalna, po ew. rabacie: karta promocyjna
# ma dwie ceny, bierzemy ostatnią). Kotwica "za N noc" jednoznacznie wskazuje
# właściwą kwotę; klasa znaków obejmuje twardą spację z tysięcy.
_PRICE_RE = re.compile(r"(\d[\d\s ]*)\s*zł\s*za\s+\d+\s+noc", re.IGNORECASE)
_DISTANCE_RE = re.compile(r"([\d,]+)\s*km\s+od\s+centrum", re.IGNORECASE)


def parse_from_price(text: str) -> Decimal | None:
    match = _PRICE_RE.search(text)
    if match is None:
        return None
    digits = re.sub(r"\D", "", match.group(1))
    return Decimal(digits) if digits else None


def parse_center_distance_km(text: str) -> Decimal | None:
    match = _DISTANCE_RE.search(text)
    return Decimal(match.group(1).replace(",", ".")) if match else None


# Karty listingu; z każdej bierzemy id, link i tekst (cena z regexa).
_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('article')).map(card => {
  const idEl = card.matches('[data-id]') ? card : card.closest('[data-id]');
  const link = card.querySelector('a[href*="/rezerwuj/"]');
  return {
    id: idEl ? idEl.getAttribute('data-id') : null,
    href: link ? link.getAttribute('href') : null,
    text: card.innerText || '',
  };
})
"""


def name_from_href(href: str) -> str | None:
    """/rezerwuj/1573271-hotel-cezamet-poznan/ -> 'Hotel Cezamet Poznan'."""
    match = re.search(r"/rezerwuj/\d+-([^/?]+)", href)
    if match is None:
        return None
    return match.group(1).replace("-", " ").strip().title()


class NocowanieAdapter(FloorAdapter):
    source = "nocowanie"

    def __init__(self, request_timeout_ms: int = 60_000):
        self.request_timeout_ms = request_timeout_ms
        self._robots = read_robots(BASE_URL, USER_AGENT)

    def _city_url(self, market: Market) -> str:
        return f"{BASE_URL}/noclegi/{market.slug}/"

    def fetch_floor(self, market: Market) -> list[FloorListing]:
        url = self._city_url(market)
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt zabrania pobrania: {url}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
            context.route(
                re.compile(r"\.(png|jpe?g|webp|avif|gif|svg|woff2?)(\?|$)"),
                lambda route: route.abort(),
            )
            page = context.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=self.request_timeout_ms)
                page.wait_for_selector("article", timeout=30_000)
                raw = page.evaluate(_EXTRACT_JS)
            finally:
                context.close()
                browser.close()

        seen: dict[str, FloorListing] = {}
        for card in raw:
            listing = self._to_listing(card, market.currency_code)
            if listing is not None:
                seen[listing.source_listing_id] = listing
        return list(seen.values())

    @staticmethod
    def _to_listing(card: dict, currency_code: str) -> FloorListing | None:
        if not card["id"] or not card["href"]:
            return None
        price = parse_from_price(card["text"])
        if price is None:
            return None
        return FloorListing(
            source_listing_id=card["id"],
            from_price=price,
            currency_code=currency_code,
            name=name_from_href(card["href"]),
            distance_center_km=parse_center_distance_km(card["text"]),
        )
