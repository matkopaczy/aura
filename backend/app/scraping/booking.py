"""Adapter Booking.com — scraping publicznych wyników wyszukiwania (§6.4).

Strategia: dla każdej daty pobytu JEDNO załadowanie strony wyników 1-nocnych;
kolejne partie po 25 wyników doładowuje infinite scroll (parametr offset w URL
jest przez Booking ignorowany — zweryfikowane na żywo 2026-07-18: 4 różne
offsety zwróciły identyczne karty). Karta obiektu daje naraz: identyfikator
(slug z linku), cenę, rating, typ jednostki i odległość od centrum — czyli
listing i obserwację ceny w jednym.
Selektory zweryfikowane na żywo 2026-07-16 (data-testid="property-card" itd.).
"""

import datetime
import re
import time
import urllib.parse
from collections.abc import Iterator
from decimal import Decimal

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

from app.models import Market
from app.robots import read_robots
from app.scraping.base import DayObservation, ObservedListing, SourceAdapter

BASE_URL = "https://www.booking.com"
SEARCH_PATH = "/searchresults.pl.html"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
)

# Jeden skrypt ekstrakcji — ten sam, którym zweryfikowano DOM ręcznie.
_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('[data-testid="property-card"]')).map(card => {
  const link = card.querySelector('a[href*="/hotel/"]');
  return {
    href: link ? link.getAttribute('href').split('?')[0] : null,
    price: card.querySelector('[data-testid="price-and-discounted-price"]')?.innerText ?? null,
    review: card.querySelector('[data-testid="review-score"]')?.innerText ?? null,
    distance: card.querySelector('[data-testid="distance"]')?.innerText ?? null,
    unit: card.querySelector('[data-testid="recommended-units"]')?.innerText ?? null,
  };
})
"""


def parse_price(text: str) -> Decimal | None:
    """'1 189 zł' / 'od 189 zł' → Decimal('1189'). Booking pokazuje ceny całkowite."""
    digits = re.sub(r"\D", "", text)
    return Decimal(digits) if digits else None


def parse_rating(text: str) -> Decimal | None:
    """'Oceniony na 8,9\\n8,9\\nFantastyczny…' → Decimal('8.9')."""
    match = re.search(r"(\d{1,2})[.,](\d)", text)
    return Decimal(f"{match.group(1)}.{match.group(2)}") if match else None


def parse_distance_km(text: str) -> Decimal | None:
    """'0,6 km od centrum' / '650 m od centrum' → km."""
    match = re.search(r"([\d\s]+(?:[.,]\d+)?)\s*(km|m)\b", text)
    if match is None:
        return None
    value = Decimal(match.group(1).replace(" ", "").replace(",", "."))
    return value / 1000 if match.group(2) == "m" else value


def listing_id_from_href(href: str) -> str | None:
    """https://www.booking.com/hotel/pl/altus.pl.html → 'pl/altus'."""
    match = re.search(r"/hotel/([a-z]{2})/([^/.]+)", href)
    return f"{match.group(1)}/{match.group(2)}" if match else None


def parse_results_total(text: str) -> int | None:
    """'Karpacz: znaleziono 207 obiektów' → 207 (łączna liczba wyników)."""
    match = _TOTAL_RE.search(text)
    return int(re.sub(r"\D", "", match.group(1))) if match else None


def scan_is_exhaustive(cards: int, total: int | None) -> bool:
    """Czy załadowane karty pokrywają (niemal) wszystkie wyniki rynku.

    Tylko wtedy wolno interpretować nieobecność listingu jako niedostępność.
    Nagłówek nieodczytany (None) = zachowawczo nie-wyczerpujący.
    """
    return total is not None and cards >= total * EXHAUSTIVE_MIN_COVERAGE


# Małe rynki (kurorty, mniejsze miasta — promień z markets.radius_km) skanujemy
# głębiej, żeby osiągnąć skan WYCZERPUJĄCY (liczba kart >= liczby wyników
# z nagłówka strony): tylko wtedy wolno liczyć obłożenie (nieobecny=zajęty
# wymaga pełnej listy). Duże miasta mają setki ofert — tam głębiej nie znaczy
# wyczerpująco, więc zostaje płycej (§6.4: nie zwiększamy obciążenia bez zysku).
SMALL_MARKET_RADIUS_KM = 8.0
# Limit partii po RESULTS_PER_BATCH wyników. To sufit bezpieczeństwa, nie cel:
# scroll kończy się naturalnie z końcem wyników, więc głębiej ładujemy tylko
# tam, gdzie podaż realnie istnieje. Rekonesans 2026-07-18 (szczyt sezonu):
# Zakopane 581, Sopot 421, Kołobrzeg 305, Władysławowo 224, Karpacz 206 —
# 30 partii (750) pokrywa maksimum z zapasem sezonowym, a tnie patologie
# (np. wyszukiwanie rozlane na "okolice").
SMALL_MARKET_PAGES = 30

RESULTS_PER_BATCH = 25  # tyle kart serwuje Booking na start i na jedną partię scrolla
HYDRATION_WAIT_S = 5.0  # obserwator doładowywania podpina się dopiero po hydracji JS
GROWTH_TIMEOUT_S = 8.0  # brak nowych kart w tym czasie po scrollu = koniec wyników

# Nagłówek wyników — łączna liczba wyników. Dwa warianty zaobserwowane na żywo:
# "Karpacz: znaleziono 207 obiektów" i "Znaleziono 64 obiekty w miejscu Gorzów
# Wielkopolski i okolicach" (stąd IGNORECASE).
_TOTAL_RE = re.compile(r"znaleziono\s+([\d\s]+)\s+obiekt", re.IGNORECASE)

# Nagłówek bywa o 1-2 wyniki wyższy niż realnie renderowane karty (pomiar
# 2026-07-18: Zakopane 579 kart przy nagłówku 581, ostatnia partia niepełna =
# koniec wyników). Pokrycie >= 99% nagłówka uznajemy za skan wyczerpujący;
# utknięcie w połowie (np. 250/581 = 43%) nadal wypada poniżej progu.
EXHAUSTIVE_MIN_COVERAGE = 0.99


class BookingAdapter(SourceAdapter):
    source = "booking"

    def __init__(
        self,
        pages_per_date: int = 2,
        request_interval_s: float = 2.5,
        guests: int = 2,
        deep_scan: bool = True,
    ):
        self.pages_per_date = pages_per_date
        self.request_interval_s = request_interval_s
        self.guests = guests  # liczba dorosłych w wyszukiwaniu (1 = pokoje 1-os.)
        # deep_scan=False: zawsze płytko (lekki przebieg 1-os., §6.4 — nie mnożymy
        # obciążenia; głęboki skan tylko dla głównego przebiegu 2-os.).
        self.deep_scan = deep_scan
        self._robots = read_robots(BASE_URL, USER_AGENT)

    def pages_for_market(self, market: Market) -> int:
        if self.deep_scan and float(market.radius_km) <= SMALL_MARKET_RADIUS_KM:
            return max(self.pages_per_date, SMALL_MARKET_PAGES)
        return self.pages_per_date

    def _search_url(self, market: Market, stay_date: datetime.date) -> str:
        params = urllib.parse.urlencode(
            {
                "ss": market.name,
                "checkin": stay_date.isoformat(),
                "checkout": (stay_date + datetime.timedelta(days=1)).isoformat(),
                "group_adults": self.guests,
                "no_rooms": 1,
                "group_children": 0,
            }
        )
        return f"{BASE_URL}{SEARCH_PATH}?{params}"

    @staticmethod
    def _card_count(page) -> int:
        return page.evaluate(
            "() => document.querySelectorAll('[data-testid=\"property-card\"]').length"
        )

    @staticmethod
    def _results_total(page) -> int | None:
        """Łączna liczba wyników z nagłówka strony; None = nagłówek nieodczytany
        (wtedy zachowawczo NIE uznajemy skanu za wyczerpujący)."""
        try:
            header = page.locator("h1").first.inner_text(timeout=5_000)
        except PlaywrightTimeoutError:
            return None
        return parse_results_total(header)

    def _wait_for_card_growth(self, page, previous: int) -> int:
        """Czeka, aż infinite scroll doładuje karty; zwraca nową liczbę kart
        (== previous, gdy nic nie przyszło w GROWTH_TIMEOUT_S)."""
        deadline = time.monotonic() + GROWTH_TIMEOUT_S
        while time.monotonic() < deadline:
            count = self._card_count(page)
            if count > previous:
                return count
            page.wait_for_timeout(500)
        return previous

    @staticmethod
    def _dismiss_overlays(page) -> None:
        """Dwa overlaye potrafią przechwycić kliknięcia na dole strony wyników:
        modal promujący logowanie (aria-modal — zamyka go Escape) oraz baner
        cookies OneTrust (odrzucamy zbędne — wariant najbardziej prywatny).
        Brak overlayu = nic do zrobienia."""
        if page.evaluate("() => !!document.querySelector('[data-bui-trap-root]')"):
            page.keyboard.press("Escape")
            page.wait_for_timeout(500)
        reject = page.locator("#onetrust-reject-all-handler")
        if reject.count() and reject.first.is_visible():
            reject.first.click(timeout=5_000)
            page.wait_for_timeout(500)

    def observe_market(
        self, market: Market, stay_dates: list[datetime.date]
    ) -> Iterator[DayObservation]:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
            # Nie pobieramy zasobów, których nie wolno nam przechowywać (§6.4).
            context.route(
                re.compile(r"\.(png|jpe?g|webp|avif|gif|svg|woff2?)(\?|$)"),
                lambda route: route.abort(),
            )
            page = context.new_page()
            cards_limit = self.pages_for_market(market) * RESULTS_PER_BATCH
            try:
                for stay_date in stay_dates:
                    url = self._search_url(market, stay_date)
                    if not self._robots.can_fetch(USER_AGENT, url):
                        raise PermissionError(f"robots.txt zabrania pobrania: {url}")
                    page.goto(url, wait_until="domcontentloaded", timeout=60_000)
                    page.wait_for_selector('[data-testid="property-card"]', timeout=30_000)
                    page.wait_for_timeout(int(HYDRATION_WAIT_S * 1000))
                    self._dismiss_overlays(page)

                    # Kolejne partie doładowuje scroll (po 3 partiach Booking
                    # przechodzi na przycisk "Załaduj więcej wyników"); koniec,
                    # gdy nic nie przyszło albo osiągnęliśmy limit partii
                    # (§6.4 — budżet obciążenia).
                    count = self._card_count(page)
                    while count < cards_limit:
                        page.evaluate(
                            "() => window.scrollTo(0, document.documentElement.scrollHeight)"
                        )
                        grown = self._wait_for_card_growth(page, count)
                        if grown == count:
                            load_more = page.get_by_role(
                                "button", name="Załaduj więcej wyników"
                            )
                            if not load_more.count():
                                break
                            load_more.first.click(timeout=10_000)
                            grown = self._wait_for_card_growth(page, count)
                            if grown == count:
                                break
                        count = grown
                        time.sleep(self.request_interval_s)

                    raw_cards = page.evaluate(_EXTRACT_JS)
                    total = self._results_total(page)
                    exhaustive = scan_is_exhaustive(len(raw_cards), total)
                    parsed = (self._to_listing(c, market.currency_code) for c in raw_cards)
                    seen: dict[str, ObservedListing] = {
                        listing.source_listing_id: listing
                        for listing in parsed
                        if listing is not None
                    }
                    yield DayObservation(
                        stay_date=stay_date,
                        observed_at=datetime.datetime.now(datetime.UTC),
                        listings=list(seen.values()),
                        exhaustive=exhaustive,
                        results_total=total,  # podaż (A5) — liczba ofert z nagłówka
                    )
                    time.sleep(self.request_interval_s)
            finally:
                context.close()
                browser.close()

    @staticmethod
    def _to_listing(card: dict, currency_code: str) -> ObservedListing | None:
        if not card["href"] or not card["price"]:
            return None
        listing_id = listing_id_from_href(card["href"])
        price = parse_price(card["price"])
        if listing_id is None or price is None:
            return None
        return ObservedListing(
            source_listing_id=listing_id,
            price=price,
            currency_code=currency_code,
            unit_type=card["unit"].split("\n")[0] if card["unit"] else None,
            rating=parse_rating(card["review"]) if card["review"] else None,
            distance_center_km=parse_distance_km(card["distance"]) if card["distance"] else None,
        )
