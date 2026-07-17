"""Źródło eventów: terminarz MTP Poznań (Międzynarodowe Targi Poznańskie).

Renderujemy DOZWOLONĄ przez robots.txt stronę /kalendarium i czytamy wydarzenia
z DOM (jej własny JS je wypełnia). NIE odpytujemy wprost endpointu /umbraco/...,
który robots.txt blokuje (§6.4). Bierzemy pierwszą stronę (najbliższe wydarzenia),
bez agresywnego doładowywania.

Selektory zweryfikowane na żywo 2026-07-17 (.events__event / __title / __day / __month).
"""

import datetime
import re

from playwright.sync_api import sync_playwright

from app.event_sources.base import CandidateEvent, EventSource, map_category
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

CALENDAR_URL = "https://www.mtp.pl/pl/kalendarium/"
# Wszystkie targi MTP odbywają się na terenie MTP w centrum Poznania.
MTP_VENUE = (52.3939, 16.8820)

POLISH_MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6,
    "lipca": 7, "sierpnia": 8, "września": 9, "wrzesnia": 9, "października": 10,
    "pazdziernika": 10, "listopada": 11, "grudnia": 12,
}


def month_number(name: str) -> int | None:
    return POLISH_MONTHS.get(name.strip().lower())


def infer_dates(
    days: list[str], months: list[str], today: datetime.date
) -> tuple[datetime.date, datetime.date] | None:
    """Buduje (start, end) z dni + miesięcy karty. Rok wnioskowany: kalendarz
    pokazuje nadchodzące wydarzenia, więc wybieramy najbliższy przyszły rok."""
    nums = [int(d) for d in days if d.strip().isdigit()]
    month_nums = [m for m in (month_number(x) for x in months) if m is not None]
    if not nums or not month_nums:
        return None
    start_day, end_day = nums[0], nums[-1]
    start_month, end_month = month_nums[0], month_nums[-1]

    start_year = today.year
    try:
        if datetime.date(start_year, start_month, start_day) < today:
            start_year += 1
    except ValueError:
        return None
    end_year = start_year + 1 if end_month < start_month else start_year
    try:
        return datetime.date(start_year, start_month, start_day), datetime.date(
            end_year, end_month, end_day
        )
    except ValueError:
        return None


_EXTRACT_JS = """
() => Array.from(document.querySelectorAll('.events__event')).map(ev => ({
  title: ev.querySelector('.events__title')?.innerText?.trim() || '',
  cat: ev.querySelector('.events__cat')?.innerText?.trim() || '',
  days: Array.from(ev.querySelectorAll('.events__day')).map(d => d.innerText.trim()),
  months: Array.from(ev.querySelectorAll('.events__month')).map(m => m.innerText.trim()),
  city: ev.querySelector('.events__city')?.innerText?.trim() || '',
}))
"""


def parse_cards(cards: list[dict], today: datetime.date) -> list[CandidateEvent]:
    """Czyste parsowanie surowych kart -> kandydaci (tylko Poznań, z poprawną datą)."""
    result: list[CandidateEvent] = []
    for card in cards:
        if not card["title"] or "pozna" not in card["city"].lower():
            continue
        dates = infer_dates(card["days"], card["months"], today)
        if dates is None:
            continue
        category, impact = map_category(card["cat"])
        result.append(
            CandidateEvent(
                name=card["title"],
                category=category,
                start_date=dates[0],
                end_date=dates[1],
                impact_strength=impact,
                venue_lat=MTP_VENUE[0],
                venue_lng=MTP_VENUE[1],
                district="Grunwald",
            )
        )
    return result


class MtpPoznanSource(EventSource):
    source = "mtp"
    market_slug = "poznan"

    def __init__(self, timeout_ms: int = 60_000):
        self.timeout_ms = timeout_ms
        self._robots = read_robots("https://www.mtp.pl", USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        if not self._robots.can_fetch(USER_AGENT, CALENDAR_URL):
            raise PermissionError(f"robots.txt zabrania: {CALENDAR_URL}")
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            context = browser.new_context(user_agent=USER_AGENT, locale="pl-PL")
            context.route(
                re.compile(r"\.(png|jpe?g|webp|avif|gif|svg|woff2?|ttf)(\?|$)"),
                lambda route: route.abort(),
            )
            page = context.new_page()
            try:
                page.goto(CALENDAR_URL, wait_until="domcontentloaded", timeout=self.timeout_ms)
                page.wait_for_selector(".events__event", timeout=30_000)
                cards = page.evaluate(_EXTRACT_JS)
            finally:
                context.close()
                browser.close()
        return parse_cards(cards, datetime.date.today())
