"""Teksty backendu (e-maile) z plików tłumaczeń — §6.2 pkt 5.

Szablony z parametrami, nigdy sklejane zdania. Dziś tylko pl;
nowy język = nowy plik JSON.
"""

import json
from functools import lru_cache
from pathlib import Path


@lru_cache
def _messages(locale: str) -> dict[str, str]:
    path = Path(__file__).parent / f"{locale}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def t(key: str, locale: str = "pl", **params) -> str:
    template = _messages(locale)[key]  # brak klucza = KeyError, fail fast
    return template.format(**params)


def render_factor(factor: dict, locale: str = "pl") -> str:
    params = dict(factor)
    key = params.pop("key")
    if "position" in params:
        params["positionPct"] = abs(round(params["position"] * 100))
    # Event z miejscem wydarzenia -> szablon z odległością (§ event-distance).
    if key == "event" and "venue_distance_km" in params:
        params["km"] = params["venue_distance_km"]
        key = "event_venue"
    return t(f"factor.{key}", locale=locale, **params)
