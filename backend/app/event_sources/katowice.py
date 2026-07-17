"""Źródła eventów: Spodek i MCK Katowice (jedna platforma operatora PTWP).

Obie strony mają identyczny listing SSR /pl/wydarzenia/<id>/ (dozwolony
w robots.txt) — czytamy czysty HTML httpx-em, bez Playwrighta. Karta:
<li><a href="...,NNNN.html"><small>02-05 lipca 2026</small>...<h3>TYTUŁ</h3>.
Zakresy dni ("02-05 lipca 2026") i przez przełom miesięcy
("30 lipca - 02 sierpnia 2026"). Kandydaci jako DRAFT do kuracji.
"""

import datetime
import html as html_lib
import re

import httpx

from app.event_sources.base import (
    CandidateEvent,
    EventSource,
    POLISH_GENITIVE_MONTHS,
    category_from_name,
    drop_recurring_series,
)
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

_CARD = re.compile(
    r"<small>([^<]+)</small>.*?<h3>([^<]+)</h3>", re.DOTALL
)


def parse_date_range(text: str) -> tuple[datetime.date, datetime.date] | None:
    """'03 lipca 2026' | '02-05 lipca 2026' | '30 lipca - 02 sierpnia 2026'."""
    year_match = re.search(r"\b(20\d{2})\b", text)
    if year_match is None:
        return None
    year = int(year_match.group(1))
    day_part = text.lower().replace(year_match.group(1), " ")
    # tokeny: dzień + opcjonalna nazwa miesiąca zaraz po nim
    tokens: list[tuple[int, int | None]] = []
    for day_str, month_name in re.findall(r"(\d{1,2})(?:\s+([a-ząćęłńóśźż]+))?", day_part):
        month = POLISH_GENITIVE_MONTHS.get(month_name) if month_name else None
        tokens.append((int(day_str), month))
    if not tokens:
        return None
    # miesiąc dnia bez własnego miesiąca = miesiąc następnego tokenu ("02-05 lipca")
    resolved: list[tuple[int, int]] = []
    for i, (day, month) in enumerate(tokens):
        if month is None:
            following = [m for _, m in tokens[i + 1:] if m is not None]
            if not following:
                return None
            month = following[0]
        resolved.append((day, month))
    try:
        dates = [datetime.date(year, month, day) for day, month in resolved]
    except ValueError:
        return None
    return min(dates), max(dates)


def parse_listing(page_html: str, venue: tuple[float, float]) -> list[CandidateEvent]:
    result: list[CandidateEvent] = []
    for date_text, title in _CARD.findall(page_html):
        dates = parse_date_range(date_text)
        if dates is None:
            continue
        name = html_lib.unescape(title).replace("\xa0", " ").strip()
        if not name:
            continue
        category, impact = category_from_name(name)
        result.append(
            CandidateEvent(
                name=name,
                category=category,
                start_date=dates[0],
                end_date=dates[1],
                impact_strength=impact,
                venue_lat=venue[0],
                venue_lng=venue[1],
                district="Śródmieście",
            )
        )
    return result


class PtwpVenueSource(EventSource):
    """Listing wydarzeń platformy PTWP (Spodek / MCK) dla jednego venue."""

    market_slug = "katowice"

    def __init__(
        self, source: str, base_url: str, listing_path: str,
        venue: tuple[float, float], timeout_s: float = 25.0,
    ):
        self.source = source
        self.base_url = base_url
        self.listing_url = f"{base_url}{listing_path}"
        self.venue = venue
        self.timeout_s = timeout_s
        self._robots = read_robots(base_url, USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        if not self._robots.can_fetch(USER_AGENT, self.listing_url):
            raise PermissionError(f"robots.txt zabrania: {self.listing_url}")
        response = httpx.get(
            self.listing_url, headers={"User-Agent": USER_AGENT},
            timeout=self.timeout_s, follow_redirects=True,
        )
        response.raise_for_status()
        today = datetime.date.today()
        upcoming = [c for c in parse_listing(response.text, self.venue) if c.end_date >= today]
        return drop_recurring_series(upcoming)


def spodek_katowice() -> PtwpVenueSource:
    return PtwpVenueSource(
        "spodek", "https://www.spodekkatowice.pl", "/pl/wydarzenia/61/",
        venue=(50.2664, 19.0286),
    )


def mck_katowice() -> PtwpVenueSource:
    return PtwpVenueSource(
        "mck-katowice", "https://www.mckkatowice.pl", "/pl/wydarzenia/5/",
        venue=(50.2646, 19.0244),
    )
