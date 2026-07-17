"""Źródło eventów: Hala Stulecia Wrocław (koncerty, kongresy, targi, sport).

Kalendarz strony ładuje miesiące POST-em do /wp-admin/admin-ajax.php
(action=show_events2, mon, rok) — ścieżka DOZWOLONA w robots.txt
(zweryfikowane 2026-07-17); endpoint zwraca HTML z <article> per wydarzenie.
Wołamy go wprost httpx-em (wzorzec PGE), miesiąc po miesiącu — WP REST
wystawia typ "wydarzenie", ale bez dat (acf puste), więc AJAX to jedyna
czysta ścieżka. Kandydaci jako DRAFT — drobne darmowe imprezy (Lato na
Pergoli) odrzuca kurator.

Karta: <time>31.07.2026 / 18:00 - 21:40</time> (zakresy "05.07 - 06.07")
+ tytuł w .post-title.
"""

import datetime
import html as html_lib
import re

import httpx

from app.event_sources.base import (
    CandidateEvent,
    EventSource,
    category_from_name,
    drop_recurring_series,
)
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

BASE_URL = "https://halastulecia.pl"
AJAX_PATH = "/wp-admin/admin-ajax.php"
STULECIA_VENUE = (51.1069, 17.0770)
MONTHS_AHEAD = 6

_DATE = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4})\b")
_TIME_TEXT = re.compile(r"<time[^>]*>\s*([^<]+)</time>")
_TITLE = re.compile(r'class="post-title entry-title">\s*<a[^>]*>([^<]+)</a>')


def parse_dates(time_text: str) -> tuple[datetime.date, datetime.date] | None:
    """'31.07.2026 / 18:00' -> (data, data); '05.07.2026 - 06.07.2026' -> zakres."""
    found = _DATE.findall(time_text)
    if not found:
        return None
    try:
        dates = [datetime.date(int(y), int(m), int(d)) for d, m, y in found]
    except ValueError:
        return None
    return min(dates), max(dates)


def parse_month_html(page_html: str) -> list[CandidateEvent]:
    result: list[CandidateEvent] = []
    for chunk in page_html.split("<article")[1:]:
        time_match = _TIME_TEXT.search(chunk)
        title_match = _TITLE.search(chunk)
        if time_match is None or title_match is None:
            continue
        dates = parse_dates(time_match.group(1))
        if dates is None:
            continue
        name = html_lib.unescape(title_match.group(1)).replace("\xa0", " ").strip()
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
                venue_lat=STULECIA_VENUE[0],
                venue_lng=STULECIA_VENUE[1],
                district="Hala Stulecia",
            )
        )
    return result


class HalaStuleciaSource(EventSource):
    source = "hala-stulecia"
    market_slug = "wroclaw"

    def __init__(self, months_ahead: int = MONTHS_AHEAD, timeout_s: float = 25.0):
        self.months_ahead = months_ahead
        self.timeout_s = timeout_s
        self._robots = read_robots(BASE_URL, USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        url = f"{BASE_URL}{AJAX_PATH}"
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt zabrania: {url}")
        today = datetime.date.today()
        events: list[CandidateEvent] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=self.timeout_s) as client:
            for offset in range(self.months_ahead + 1):
                month = (today.month - 1 + offset) % 12 + 1
                year = today.year + (today.month - 1 + offset) // 12
                response = client.post(
                    url,
                    data={"mon": str(month), "rok": str(year), "action": "show_events2"},
                )
                response.raise_for_status()
                events += parse_month_html(response.text)
        # Dedup (wydarzenie wielomiesięczne może wrócić w kilku miesiącach).
        unique = {(e.name, e.start_date): e for e in events}
        upcoming = [e for e in unique.values() if e.end_date >= today]
        return drop_recurring_series(upcoming)
