import datetime

from app.event_sources.tarczynski import parse_ld_events

_D = datetime.date


def _ld(name: str, start: str) -> str:
    return (
        '<script type="application/ld+json"> { "@context": "http://schema.org", '
        f'"@type": "Event", "startDate": "{start}", "name": "{name}", '
        '"url": "https://example.pl/events/x/" } </script>'
    )


def test_parse_ld_events():
    html = (
        _ld("Mecz Śląsk Wrocław vs Raków", "2026-08-02T20:00")
        + _ld("Wro Expo", "2026-09-19")
        + '<script type="application/ld+json">{"@type": "Organization", "name": "X"}</script>'
        + '<script type="application/ld+json">{zepsuty json</script>'
    )
    parsed = parse_ld_events(html)
    assert parsed == [
        (_D(2026, 8, 2), "Mecz Śląsk Wrocław vs Raków"),
        (_D(2026, 9, 19), "Wro Expo"),
    ]


def test_parse_ld_skips_missing_dates():
    html = _ld("Bez daty", "wkrótce")
    assert parse_ld_events(html) == []


def test_category_from_name_tiers():
    from app.event_sources.base import category_from_name

    assert category_from_name("Mecz Śląsk vs Raków")[0] == "sport"
    assert category_from_name("Wro Expo – Targi Mieszkaniowe")[0] == "targi"
    assert category_from_name("XIII Kongres Polonii Medycznej")[0] == "konferencje"
    assert category_from_name("Deep Purple")[0] == "koncert"
