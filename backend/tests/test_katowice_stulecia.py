import datetime

from app.event_sources.base import CandidateEvent, drop_recurring_series
from app.event_sources.katowice import parse_date_range, parse_listing
from app.event_sources.stulecia import parse_dates, parse_month_html

_D = datetime.date


def test_katowice_parse_date_range():
    assert parse_date_range("03 lipca 2026") == (_D(2026, 7, 3), _D(2026, 7, 3))
    assert parse_date_range("02-05 lipca 2026") == (_D(2026, 7, 2), _D(2026, 7, 5))
    assert parse_date_range("30 lipca - 02 sierpnia 2026") == (_D(2026, 7, 30), _D(2026, 8, 2))
    assert parse_date_range("wkrótce") is None


def test_katowice_parse_listing():
    html = (
        '<li><a href="x"><small>26-28 września 2026</small><div><h3>Mistrzostwa '
        "Świata Mażoretek</h3></div></a></li>"
        '<li><a href="y"><small>bez daty</small><div><h3>Zepsute</h3></div></a></li>'
    )
    events = parse_listing(html, venue=(50.26, 19.02))
    assert len(events) == 1
    assert events[0].name == "Mistrzostwa Świata Mażoretek"
    assert events[0].category == "sport"  # "mistrzostwa" w nazwie
    assert events[0].start_date == _D(2026, 9, 26)
    assert events[0].end_date == _D(2026, 9, 28)


def test_stulecia_parse_dates():
    assert parse_dates("31.07.2026 / 18:00 - 21:40") == (_D(2026, 7, 31), _D(2026, 7, 31))
    assert parse_dates("05.07.2026 - 06.07.2026") == (_D(2026, 7, 5), _D(2026, 7, 6))
    assert parse_dates("brak") is None


def test_stulecia_parse_month_html():
    html = (
        "<article><time>10.09.2026 / 10:00</time>"
        '<h2 class="post-title entry-title"><a href="x">XIII Kongres Polonii</a></h2>'
        "</article>"
        "<article><time>zepsute</time>"
        '<h2 class="post-title entry-title"><a href="y">Bez daty</a></h2></article>'
    )
    events = parse_month_html(html)
    assert [e.name for e in events] == ["XIII Kongres Polonii"]
    assert events[0].venue_lat is not None


def _cand(name):
    return CandidateEvent(
        name=name, category="koncert", start_date=_D(2026, 8, 1), end_date=_D(2026, 8, 1),
        impact_strength=0.6, venue_lat=None, venue_lng=None,
    )


def test_drop_recurring_series():
    batch = (
        [_cand(f"Lato na Pergoli: Odcinek {i}") for i in range(5)]  # seria -> odpada
        + [_cand("JAM SESSION"), _cand("JAM SESSION"), _cand("JAM SESSION"), _cand("JAM SESSION")]
        + [_cand("Smokie | The Legacy Tour"), _cand("Liga Narodów: Polska vs Rumunia")]
    )
    kept = drop_recurring_series(batch)
    assert {c.name for c in kept} == {"Smokie | The Legacy Tour", "Liga Narodów: Polska vs Rumunia"}
