"""Źródło eventów: trojmiasto.pl — regionalny agregator (koncerty, sport).

Gdańsk/Gdynia/Sopot to od 2026-07-17 OSOBNE rynki — jeden listing agregatora
zasila trzy rynki: instancja źródła per (miasto, kategoria), a miasto z karty
decyduje o przynależności (wydarzenia spoza trzech miast odpadają). Listing
/imprezy/koncerty/ jest SSR i dozwolony przez robots.txt (blokuje /_ajax/,
/ajax/, nie /imprezy/). Parsujemy pierwszą stronę (najbliższe wydarzenia).

Selektory zweryfikowane na żywo 2026-07-17 (.event__item__title / __location__city,
.calendar-icon__icon__month / __day).
"""

import datetime
import re

from playwright.sync_api import sync_playwright

from app.event_sources.base import CandidateEvent, EventSource
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

BASE_URL = "https://www.trojmiasto.pl"

MONTH_ABBR = {
    "sty": 1, "lut": 2, "mar": 3, "kwi": 4, "maj": 5, "cze": 6,
    "lip": 7, "sie": 8, "wrz": 9, "paź": 10, "paz": 10, "lis": 11, "gru": 12,
}
# Centra miast Trójmiasta -> venue (rozległy rynek, odległość ma znaczenie).
CITY_COORDS = {
    "gdańsk": (54.3520, 18.6466), "gdansk": (54.3520, 18.6466),
    "gdynia": (54.5189, 18.5305), "sopot": (54.4418, 18.5601),
}


def month_from_abbr(abbr: str) -> int | None:
    return MONTH_ABBR.get(abbr.strip().lower()[:3])


def parse_day_range(day_text: str) -> tuple[int, int] | None:
    """'18' -> (18,18); '13-14' -> (13,14)."""
    nums = [int(n) for n in re.findall(r"\d{1,2}", day_text)]
    if not nums:
        return None
    return nums[0], nums[-1]


def infer_year(month: int, day: int, today: datetime.date) -> int | None:
    year = today.year
    try:
        if datetime.date(year, month, day) < today:
            year += 1
        datetime.date(year, month, day)
    except ValueError:
        return None
    return year


def city_venue(city_text: str) -> tuple[str, tuple[float, float] | None]:
    """'Gdańsk,' -> ('Gdańsk', coords). Nieznane miasto -> (tekst, None)."""
    name = city_text.strip().rstrip(",").strip()
    return name, CITY_COORDS.get(name.lower())


def parse_articles(
    cards: list[dict], today: datetime.date, category: str = "koncert", impact: float = 0.6
) -> list[CandidateEvent]:
    result: list[CandidateEvent] = []
    for card in cards:
        title = (card.get("title") or "").strip()
        month = month_from_abbr(card.get("month", ""))
        days = parse_day_range(card.get("day", ""))
        if not title or month is None or days is None:
            continue
        start_day, end_day = days
        year = infer_year(month, start_day, today)
        if year is None:
            continue
        city_name, coords = city_venue(card.get("city", ""))
        try:
            start = datetime.date(year, month, start_day)
            end = datetime.date(year, month, end_day)
        except ValueError:
            continue
        result.append(
            CandidateEvent(
                name=title,
                category=category,
                start_date=start,
                end_date=end if end >= start else start,
                impact_strength=impact,
                venue_lat=coords[0] if coords else None,
                venue_lng=coords[1] if coords else None,
                district=city_name or None,
            )
        )
    return result


_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('article')).map(a => ({
  title: a.querySelector('.event__item__title')?.innerText?.trim() || '',
  month: a.querySelector('.calendar-icon__icon__month')?.innerText?.trim() || '',
  day: a.querySelector('.calendar-icon__icon__day')?.innerText?.trim() || '',
  city: a.querySelector('.event__item__location__city')?.innerText?.trim() || '',
})).filter(e => e.title)
"""


class TrojmiastoSource(EventSource):
    """Listing trojmiasto.pl dla jednej kategorii, filtrowany do jednego miasta."""

    def __init__(
        self, source: str, listing_path: str, category: str, impact: float,
        market_slug: str, city: str, timeout_ms: int = 60_000,
    ):
        self.source = source
        self.listing_url = f"{BASE_URL}{listing_path}"
        self.category = category
        self.impact = impact
        self.market_slug = market_slug
        self.city = city.lower()
        self.timeout_ms = timeout_ms
        self._robots = read_robots(BASE_URL, USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        if not self._robots.can_fetch(USER_AGENT, self.listing_url):
            raise PermissionError(f"robots.txt zabrania: {self.listing_url}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
            context.route(
                re.compile(r"\.(png|jpe?g|webp|avif|gif|svg|woff2?|ttf)(\?|$)"),
                lambda route: route.abort(),
            )
            page = context.new_page()
            try:
                page.goto(self.listing_url, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_selector("article .event__item__title", timeout=30_000)
                cards = page.evaluate(_EXTRACT_JS)
            finally:
                context.close()
                browser.close()
        candidates = parse_articles(cards, datetime.date.today(), self.category, self.impact)
        # Miasto z karty decyduje o rynku; spoza Gdańska/Gdyni/Sopotu -> odpada.
        return [c for c in candidates if (c.district or "").lower() == self.city]


# Miasta Trójmiasta jako osobne rynki: instancja per (miasto, kategoria).
TRICITY_SLUGS = ["gdansk", "gdynia", "sopot"]
_CITY_NAMES = {"gdansk": "Gdańsk", "gdynia": "Gdynia", "sopot": "Sopot"}
_LISTINGS = [
    ("koncerty", "/imprezy/koncerty/", "koncert", 0.6),
    ("sport", "/imprezy/sport-rekreacja/", "sport", 0.7),
]


def tricity_sources() -> list[TrojmiastoSource]:
    return [
        TrojmiastoSource(
            source=f"trojmiasto-{kind}-{slug}",
            listing_path=path,
            category=category,
            impact=impact,
            market_slug=slug,
            city=_CITY_NAMES[slug],
        )
        for slug in TRICITY_SLUGS
        for kind, path, category, impact in _LISTINGS
    ]
