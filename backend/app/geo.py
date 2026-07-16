"""Geometria współdzielona — bez zależności od Playwright/DB (§11)."""

import math


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Odległość po ortodromie w km między dwoma punktami (lat/lng w stopniach)."""
    radius = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2 - lat1), math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))
