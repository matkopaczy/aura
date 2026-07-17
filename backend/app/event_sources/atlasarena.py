"""Źródło eventów: Atlas Arena Łódź (koncerty i sport, ~duża hala miasta).

WordPress z SSR — renderujemy DOZWOLONĄ przez robots.txt stronę /wydarzenia
i czytamy karty z DOM (wzorzec MTP). Typ postu "events" nie jest wystawiony
w WP REST (zweryfikowane 2026-07-17), więc DOM to jedyna czysta ścieżka.
Pierwsza strona = najbliższe wydarzenia, bez doładowywania (§6.4).

Struktura karty (zweryfikowana na żywo 2026-07-17):
- .eventsmain__center__item__title__day  -> "25.07" (dzień.miesiąc, rok wnioskowany)
- .eventsmain__center__item__title__promo__slogan -> "koncert" / "SPORT ARENA"
- img alt -> "sobota 25.07 - Scorpions" (nazwa po " - ")
"""

import datetime
import re

from playwright.sync_api import sync_playwright

from app.event_sources.base import CandidateEvent, EventSource, map_category
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

EVENTS_URL = "https://www.atlasarena.pl/wydarzenia"
# Atlas Arena, al. Bandurskiego 7, Łódź (Sport Arena to ten sam kompleks).
ATLAS_VENUE = (51.7793, 19.4324)


def parse_day_month(text: str) -> tuple[int, int] | None:
    """'25.07' -> (25, 7)."""
    match = re.fullmatch(r"(\d{1,2})\.(\d{1,2})", text.strip())
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2))


def infer_date(day: int, month: int, today: datetime.date) -> datetime.date | None:
    """Kalendarz pokazuje nadchodzące wydarzenia -> najbliższy przyszły rok."""
    year = today.year
    try:
        if datetime.date(year, month, day) < today:
            year += 1
        return datetime.date(year, month, day)
    except ValueError:
        return None


def name_from_alt(alt: str) -> str | None:
    """'sobota 25.07 - Scorpions' -> 'Scorpions'."""
    if " - " not in alt:
        return None
    name = alt.split(" - ", 1)[1].strip()
    return name or None


def name_from_slug(href: str) -> str | None:
    """'https://atlasarena.pl/wydarzenia/scorpions-2/' -> 'Scorpions 2'."""
    match = re.search(r"/wydarzenia/([^/]+)/?$", href)
    if match is None:
        return None
    return match.group(1).replace("-", " ").strip().title() or None


# Słowa w nazwie jednoznacznie wskazujące sport — slogan bywa nazwą hali
# ("SPORT ARENA" = mniejsza hala kompleksu), więc nazwa jest pewniejsza.
SPORT_KEYWORDS = ("puchar", "mecz", "liga", " vs ", "boks", "mma", "gala boksu", "mistrzostwa")


def categorize(slogan: str, name: str) -> tuple[str, float]:
    """Kategoria z nazwy (sport) lub sloganu; 'Sport Arena' w sloganie to hala."""
    lowered = name.lower()
    if any(keyword in lowered for keyword in SPORT_KEYWORDS):
        return map_category("sport")
    slogan_clean = "" if "aren" in slogan.lower() else slogan
    return map_category(slogan_clean, default="koncert")


_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('.eventsmain__center__item')).map(item => ({
  day: item.querySelector('.eventsmain__center__item__title__day')?.innerText?.trim() || '',
  slogan: item.querySelector('.eventsmain__center__item__title__promo__slogan')?.innerText?.trim() || '',
  alt: item.querySelector('img')?.getAttribute('alt') || '',
  href: (item.querySelector('a[href*="/wydarzenia/"]') || item.closest('a[href*="/wydarzenia/"]'))?.href || '',
}))
"""


def parse_cards(cards: list[dict], today: datetime.date) -> list[CandidateEvent]:
    """Czyste parsowanie surowych kart -> kandydaci (jednodniowe koncerty/sport)."""
    result: list[CandidateEvent] = []
    for card in cards:
        day_month = parse_day_month(card["day"])
        if day_month is None:
            continue
        event_date = infer_date(day_month[0], day_month[1], today)
        if event_date is None:
            continue
        name = name_from_alt(card["alt"]) or name_from_slug(card["href"])
        if name is None:
            continue
        category, impact = categorize(card["slogan"], name)
        result.append(
            CandidateEvent(
                name=name,
                category=category,
                start_date=event_date,
                end_date=event_date,
                impact_strength=impact,
                venue_lat=ATLAS_VENUE[0],
                venue_lng=ATLAS_VENUE[1],
                district="Polesie",
            )
        )
    return result


class AtlasArenaSource(EventSource):
    source = "atlasarena"
    market_slug = "lodz"

    def __init__(self, timeout_ms: int = 60_000):
        self.timeout_ms = timeout_ms
        self._robots = read_robots("https://www.atlasarena.pl", USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        if not self._robots.can_fetch(USER_AGENT, EVENTS_URL):
            raise PermissionError(f"robots.txt zabrania: {EVENTS_URL}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
            context.route(
                re.compile(r"\.(png|jpe?g|webp|avif|gif|svg|woff2?|ttf)(\?|$)"),
                lambda route: route.abort(),
            )
            page = context.new_page()
            try:
                page.goto(EVENTS_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_selector(".eventsmain__center__item", timeout=30_000)
                cards = page.evaluate(_EXTRACT_JS)
            finally:
                context.close()
                browser.close()
        return parse_cards(cards, datetime.date.today())
