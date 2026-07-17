"""Źródło eventów: PGE Narodowy Warszawa (największe koncerty/sport w Polsce).

Kalendarz strony ładuje miesiące XHR-em z /calendar/calendar-graphic.php
(month, year) — endpoint DOZWOLONY przez robots.txt (zweryfikowane 2026-07-17),
zwraca gotowy HTML siatki. Wołamy go wprost httpx-em (bez Playwrighta, jak
tribe): kilka lekkich zapytań tygodniowo, po jednym na miesiąc.

Bierzemy TYLKO wydarzenia masowe (klasa "mass-event": The Weeknd, Speedway...)
— joga i "Aktywne Czwartki" nie wpływają na popyt hotelowy. Każda komórka dnia
ma data-currentdate="04 sierpnia 2026" (pełna data, zero zgadywania roku).
Ten sam tytuł w kolejnych dniach scalamy w jeden zakres (trasy dwudniowe).
"""

import datetime
import re

import httpx

from app.event_sources.base import CandidateEvent, EventSource, merge_consecutive_days
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

BASE_URL = "https://www.pgenarodowy.pl"
CALENDAR_PATH = "/calendar/calendar-graphic.php"
PGE_VENUE = (52.2395, 21.0446)  # al. Poniatowskiego 1
MONTHS_AHEAD = 6

# Dopełniacz miesięcy z data-currentdate ("04 sierpnia 2026").
POLISH_MONTHS = {
    "stycznia": 1, "lutego": 2, "marca": 3, "kwietnia": 4, "maja": 5, "czerwca": 6,
    "lipca": 7, "sierpnia": 8, "września": 9, "wrzesnia": 9, "października": 10,
    "pazdziernika": 10, "listopada": 11, "grudnia": 12,
}

_DAY_SPLIT = re.compile(r'data-currentdate="(\d{1,2}) ([^" ]+) (\d{4})"')
_MASS_TITLE = re.compile(
    r'class="calendar--day-event mass-event"[^>]*>.*?calendar--event-title[^>]*>([^<]+)',
    re.DOTALL,
)


def parse_date(day: str, month_name: str, year: str) -> datetime.date | None:
    month = POLISH_MONTHS.get(month_name.strip().lower())
    if month is None:
        return None
    try:
        return datetime.date(int(year), month, int(day))
    except ValueError:
        return None


def parse_month_html(html: str) -> list[tuple[datetime.date, str]]:
    """Fragment miesiąca -> [(data, tytuł wydarzenia masowego)]."""
    result: list[tuple[datetime.date, str]] = []
    matches = list(_DAY_SPLIT.finditer(html))
    for i, match in enumerate(matches):
        date = parse_date(match.group(1), match.group(2), match.group(3))
        if date is None:
            continue
        segment_end = matches[i + 1].start() if i + 1 < len(matches) else len(html)
        segment = html[match.end():segment_end]
        for title_match in _MASS_TITLE.finditer(segment):
            title = title_match.group(1).strip()
            if title:
                result.append((date, title))
    return result


def merge_consecutive(days: list[tuple[datetime.date, str]]) -> list[CandidateEvent]:
    """Ten sam tytuł w kolejnych dniach -> jeden event z zakresem dat."""
    return merge_consecutive_days(days, venue=PGE_VENUE, district="Praga-Południe")


class PgeNarodowySource(EventSource):
    source = "pge-narodowy"
    market_slug = "warszawa"

    def __init__(self, months_ahead: int = MONTHS_AHEAD, timeout_s: float = 20.0):
        self.months_ahead = months_ahead
        self.timeout_s = timeout_s
        self._robots = read_robots(BASE_URL, USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        url = f"{BASE_URL}{CALENDAR_PATH}"
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt zabrania: {url}")
        today = datetime.date.today()
        days: list[tuple[datetime.date, str]] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=self.timeout_s) as client:
            for offset in range(self.months_ahead + 1):
                month = (today.month - 1 + offset) % 12 + 1
                year = today.year + (today.month - 1 + offset) // 12
                response = client.get(
                    url, params={"month": f"{month:02d}", "year": str(year)}
                )
                response.raise_for_status()
                days += parse_month_html(response.text)
        # Miniona część bieżącego miesiąca nie jest kandydatem.
        return merge_consecutive([(d, t) for d, t in days if d >= today])
