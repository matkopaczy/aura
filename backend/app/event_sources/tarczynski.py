"""Źródło eventów: Tarczyński Arena Wrocław (stadion — mecze, mega-koncerty).

WordPress + plugin Modern Events Calendar. Kalendarz ładuje miesiące POST-em
do admin-ajax.php (action=mec_monthly_view_load_month, mec_year, mec_month;
ścieżka dozwolona w robots.txt, zweryfikowane 2026-07-17). Odpowiedź to JSON
{"month": "<html>"}, a w HTML siedzą bloki JSON-LD schema.org Event
(startDate, name) — parsujemy DANE STRUKTURALNE, nie selektory CSS.

Każde wystąpienie dnia to osobny blok -> scalamy kolejne dni w zakres;
codzienne kursy (rolki) wycina filtr serii cyklicznych.
"""

import datetime
import json
import re

import httpx

from app.event_sources.base import (
    CandidateEvent,
    EventSource,
    drop_recurring_series,
    merge_consecutive_days,
)
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

BASE_URL = "https://tarczynskiarenawroclaw.pl"
AJAX_PATH = "/wp-admin/admin-ajax.php"
TARCZYNSKI_VENUE = (51.1409, 16.9430)  # Stadion Wrocław, al. Śląska 1
MONTHS_AHEAD = 6

_LD_BLOCK = re.compile(
    r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', re.DOTALL
)


def parse_ld_events(month_html: str) -> list[tuple[datetime.date, str]]:
    """Bloki JSON-LD Event -> [(data startu, nazwa)]. Zepsute bloki pomijamy."""
    result: list[tuple[datetime.date, str]] = []
    for match in _LD_BLOCK.finditer(month_html):
        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError:
            continue
        if data.get("@type") != "Event":
            continue
        name = (data.get("name") or "").strip()
        start_raw = (data.get("startDate") or "")[:10]
        try:
            start = datetime.date.fromisoformat(start_raw)
        except ValueError:
            continue
        if name:
            result.append((start, name))
    return result


class TarczynskiArenaSource(EventSource):
    source = "tarczynski-arena"
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
        days: list[tuple[datetime.date, str]] = []
        with httpx.Client(headers={"User-Agent": USER_AGENT}, timeout=self.timeout_s) as client:
            for offset in range(self.months_ahead + 1):
                month = (today.month - 1 + offset) % 12 + 1
                year = today.year + (today.month - 1 + offset) // 12
                response = client.post(
                    url,
                    data={
                        "action": "mec_monthly_view_load_month",
                        "mec_year": str(year),
                        "mec_month": f"{month:02d}",
                    },
                )
                response.raise_for_status()
                days += parse_ld_events(response.json().get("month", ""))
        merged = merge_consecutive_days(
            [(d, t) for d, t in set(days) if d >= today],
            venue=TARCZYNSKI_VENUE,
            district="Pilczyce",
        )
        return drop_recurring_series(merged)
