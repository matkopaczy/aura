import datetime

from app.event_sources.tribe import parse_tribe_events

VENUE = (50.0678, 19.9896)

SAMPLE = [
    {
        "title": "Maroon 5",
        "start_date": "2026-09-15 20:00:00",
        "end_date": "2026-09-15 23:00:00",
        "categories": [{"name": "Koncerty"}],
    },
    {
        "title": "Memoriał Wagnera",
        "start_date": "2026-08-28 18:00:00",
        "end_date": "2026-08-30 22:00:00",
        "categories": [{"name": "Sport"}],
    },
    {
        "title": "Coś bez kategorii",
        "start_date": "2026-07-24 19:00:00",
        "end_date": "2026-07-24 22:00:00",
        "categories": [],
    },
    {  # bez tytułu / złej daty -> pominięte
        "title": "",
        "start_date": "2026-07-24 19:00:00",
        "categories": [],
    },
]


def test_parse_tribe_events():
    out = parse_tribe_events(SAMPLE, VENUE, default_category="koncert")
    assert len(out) == 3  # pusty tytuł pominięty

    maroon = out[0]
    assert maroon.name == "Maroon 5"
    assert maroon.start_date == datetime.date(2026, 9, 15)
    assert maroon.category == "koncert"
    assert maroon.impact_strength == 0.6
    assert maroon.venue_lat == 50.0678

    sport = out[1]
    assert sport.category == "sport"
    assert sport.impact_strength == 0.7
    assert sport.end_date == datetime.date(2026, 8, 30)

    # brak kategorii -> domyślna obiektu (koncert)
    assert out[2].category == "koncert"


def test_parse_tribe_events_bad_date_skipped():
    out = parse_tribe_events(
        [{"title": "X", "start_date": "brak", "categories": []}], VENUE, "koncert"
    )
    assert out == []
