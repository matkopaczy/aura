import datetime

from app.event_sources.pge import merge_consecutive, parse_date, parse_month_html

_D = datetime.date


def _cell(day: int, month: str, year: int, events_html: str = "") -> str:
    return (
        f'<td><div class="calendar--day has-events">'
        f'<a data-currentdate="{day:02d} {month} {year}">{day}</a>{events_html}</div></td>'
    )


def _mass(title: str) -> str:
    return (
        '<div class="calendar--day-event mass-event"><div>'
        f'<div class="calendar--event-title">{title}</div></div></div>'
    )


def _plain(title: str) -> str:
    return (
        '<div class="calendar--day-event"><div>'
        f'<div class="calendar--event-title">{title}</div></div></div>'
    )


def test_parse_date():
    assert parse_date("04", "sierpnia", "2026") == _D(2026, 8, 4)
    assert parse_date("31", "lutego", "2026") is None
    assert parse_date("1", "brumaire", "2026") is None


def test_parse_month_html_takes_only_mass_events():
    html = (
        _cell(4, "sierpnia", 2026, _mass("The Weeknd") + _plain("Wtorki z Jogą"))
        + _cell(5, "sierpnia", 2026, _mass("The Weeknd"))
        + _cell(6, "sierpnia", 2026, _plain("Aktywne Czwartki"))
    )
    parsed = parse_month_html(html)
    assert parsed == [(_D(2026, 8, 4), "The Weeknd"), (_D(2026, 8, 5), "The Weeknd")]


def test_merge_consecutive_ranges_and_categories():
    days = [
        (_D(2026, 8, 4), "The Weeknd"),
        (_D(2026, 8, 5), "The Weeknd"),
        (_D(2026, 8, 29), "2026 BOLL FIM Speedway World Cup"),
        (_D(2026, 9, 25), "Liga Narodów: Polska vs. Rumunia"),
    ]
    events = {e.name: e for e in merge_consecutive(days)}
    weeknd = events["The Weeknd"]
    assert weeknd.start_date == _D(2026, 8, 4)
    assert weeknd.end_date == _D(2026, 8, 5)  # kolejne dni scalone w zakres
    assert weeknd.category == "koncert"
    assert events["2026 BOLL FIM Speedway World Cup"].category == "sport"
    assert events["Liga Narodów: Polska vs. Rumunia"].category == "sport"
    assert all(e.venue_lat is not None for e in events.values())


def test_merge_keeps_separate_nonconsecutive_dates():
    days = [(_D(2026, 8, 1), "X"), (_D(2026, 8, 15), "X")]
    events = merge_consecutive(days)
    assert len(events) == 2  # przerwa -> dwa osobne terminy
    assert {(e.start_date, e.end_date) for e in events} == {
        (_D(2026, 8, 1), _D(2026, 8, 1)),
        (_D(2026, 8, 15), _D(2026, 8, 15)),
    }
