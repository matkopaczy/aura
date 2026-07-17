"""Generyczne źródło eventów: WordPress + plugin "The Events Calendar" (tribe).

Wiele polskich obiektów (areny, hale) stoi na tym pluginie, który wystawia
PUBLICZNE REST API /wp-json/tribe/events/v1/events. robots.txt tych witryn
blokuje zwykle /wp-admin/, ale NIE /wp-json/ — więc API jest dozwolone (§6.4).
Czysty JSON, bez Playwrighta. Nowy obiekt na tym pluginie = jedna instancja.
"""

import datetime
import logging

import httpx

from app.event_sources.base import CandidateEvent, EventSource, map_category
from app.robots import read_robots
from app.scraping.booking import USER_AGENT

logger = logging.getLogger(__name__)

_EVENTS_PATH = "/wp-json/tribe/events/v1/events"


def _parse_date(value: str) -> datetime.date | None:
    """'2026-07-24 19:00:00' -> date(2026,7,24)."""
    try:
        return datetime.date.fromisoformat(value[:10])
    except (ValueError, TypeError):
        return None


def parse_tribe_events(
    events: list[dict], venue: tuple[float, float], default_category: str
) -> list[CandidateEvent]:
    result: list[CandidateEvent] = []
    for ev in events:
        title = (ev.get("title") or "").strip()
        start = _parse_date(ev.get("start_date", ""))
        end = _parse_date(ev.get("end_date", "")) or start
        if not title or start is None:
            continue
        # kategoria z pierwszej mapowalnej nazwy; inaczej domyślna dla obiektu
        category, impact = default_category, map_category(default_category, default_category)[1]
        for cat in ev.get("categories") or []:
            slug, imp = map_category(cat.get("name", ""), default_category)
            if slug != default_category:
                category, impact = slug, imp
                break
        result.append(
            CandidateEvent(
                name=title,
                category=category,
                start_date=start,
                end_date=end if end >= start else start,
                impact_strength=impact,
                venue_lat=venue[0],
                venue_lng=venue[1],
            )
        )
    return result


class TribeEventsSource(EventSource):
    def __init__(
        self,
        source: str,
        market_slug: str,
        base_url: str,
        venue_lat: float,
        venue_lng: float,
        default_category: str = "koncert",
    ):
        self.source = source
        self.market_slug = market_slug
        self.base_url = base_url.rstrip("/")
        self.venue = (venue_lat, venue_lng)
        self.default_category = default_category
        self._robots = read_robots(self.base_url, USER_AGENT)

    def fetch(self) -> list[CandidateEvent]:
        url = f"{self.base_url}{_EVENTS_PATH}"
        if not self._robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt zabrania: {url}")
        today = datetime.date.today().isoformat()
        response = httpx.get(
            url,
            params={"per_page": 50, "start_date": today},
            headers={"User-Agent": USER_AGENT},
            timeout=30,
            follow_redirects=True,
        )
        response.raise_for_status()
        events = response.json().get("events", [])
        return parse_tribe_events(events, self.venue, self.default_category)


def tauron_arena_krakow() -> TribeEventsSource:
    # TAURON Arena Kraków, ul. Lema 7 (Czyżyny).
    return TribeEventsSource(
        source="tauron-arena-krakow",
        market_slug="krakow",
        base_url="https://www.tauronarenakrakow.pl",
        venue_lat=50.0678,
        venue_lng=19.9896,
        default_category="koncert",
    )
