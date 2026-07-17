import datetime

from app.event_sources.trojmiasto import (
    city_venue,
    infer_year,
    month_from_abbr,
    parse_articles,
    parse_day_range,
)

TODAY = datetime.date(2026, 7, 17)


def test_month_from_abbr():
    assert month_from_abbr("LIP") == 7
    assert month_from_abbr("LIS") == 11
    assert month_from_abbr("PAŹ") == 10
    assert month_from_abbr("XYZ") is None


def test_parse_day_range():
    assert parse_day_range("18") == (18, 18)
    assert parse_day_range("13-14") == (13, 14)
    assert parse_day_range("brak") is None


def test_infer_year():
    assert infer_year(11, 13, TODAY) == 2026  # listopad jeszcze przed nami
    assert infer_year(1, 10, TODAY) == 2027  # styczeń minął -> nastepny rok


def test_city_venue():
    name, coords = city_venue("Gdańsk,")
    assert name == "Gdańsk"
    assert coords == (54.3520, 18.6466)
    assert city_venue("Sopot,")[1] == (54.4418, 18.5601)
    assert city_venue("Inne Miasto,")[1] is None


def test_parse_articles():
    cards = [
        {"title": "Inside Seaside 2026", "month": "LIS", "day": "13-14", "city": "Gdańsk,"},
        {"title": "Beata i Bajm", "month": "LIP", "day": "22", "city": "Sopot,"},
        {"title": "", "month": "LIP", "day": "18", "city": "Gdynia,"},  # bez tytułu
        {"title": "Zła data", "month": "XXX", "day": "5", "city": "Gdańsk,"},  # zły miesiąc
    ]
    out = parse_articles(cards, TODAY)
    assert len(out) == 2

    seaside = out[0]
    assert seaside.name == "Inside Seaside 2026"
    assert seaside.start_date == datetime.date(2026, 11, 13)
    assert seaside.end_date == datetime.date(2026, 11, 14)
    assert seaside.category == "koncert"
    assert seaside.venue_lat == 54.3520  # Gdańsk
    assert seaside.district == "Gdańsk"

    bajm = out[1]
    assert bajm.start_date == datetime.date(2026, 7, 22)
    assert bajm.venue_lat == 54.4418  # Sopot


def test_parse_articles_sport_category():
    cards = [{"title": "Lechia - Legia", "month": "SIE", "day": "15", "city": "Gdańsk,"}]
    out = parse_articles(cards, TODAY, category="sport", impact=0.7)
    assert len(out) == 1
    assert out[0].category == "sport"
    assert out[0].impact_strength == 0.7
