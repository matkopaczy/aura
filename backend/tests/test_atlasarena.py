import datetime

from app.event_sources.atlasarena import (
    categorize,
    infer_date,
    name_from_alt,
    name_from_slug,
    parse_cards,
    parse_day_month,
)

TODAY = datetime.date(2026, 7, 17)


def test_parse_day_month():
    assert parse_day_month("25.07") == (25, 7)
    assert parse_day_month(" 3.1 ") == (3, 1)
    assert parse_day_month("sobota") is None
    assert parse_day_month("") is None


def test_infer_date_rolls_to_next_year():
    assert infer_date(25, 7, TODAY) == datetime.date(2026, 7, 25)
    # data z przeszłości -> przyszły rok (kalendarz pokazuje nadchodzące)
    assert infer_date(10, 1, TODAY) == datetime.date(2027, 1, 10)
    assert infer_date(31, 2, TODAY) is None  # nieistniejąca data


def test_name_extraction():
    assert name_from_alt("sobota 25.07 - Scorpions") == "Scorpions"
    assert name_from_alt("bez separatora") is None
    assert name_from_slug("https://atlasarena.pl/wydarzenia/scorpions-2/") == "Scorpions 2"
    # link paginacji (dwa segmenty) nie jest wydarzeniem -> None
    assert name_from_slug("https://atlasarena.pl/wydarzenia/page/2/") is None


def test_categorize_sport_from_name_not_hall():
    # "SPORT ARENA" w sloganie = nazwa mniejszej hali, nie kategoria
    assert categorize("SPORT ARENA", "Smokie")[0] == "koncert"
    assert categorize("koncert", "Deep Purple")[0] == "koncert"
    # sport rozpoznajemy po nazwie wydarzenia
    assert categorize("", "Superpuchar Polski w piłce ręcznej")[0] == "sport"
    assert categorize("Nie przegap!", "Gala boksu KSW")[0] == "sport"


def test_parse_cards_end_to_end():
    cards = [
        {"day": "25.07", "slogan": "koncert", "alt": "sobota 25.07 - Scorpions",
         "href": "https://atlasarena.pl/wydarzenia/scorpions-2/"},
        {"day": "10.01", "slogan": "SPORT ARENA", "alt": "",
         "href": "https://atlasarena.pl/wydarzenia/final-pucharu-x/"},
        {"day": "zła", "slogan": "", "alt": "x - y", "href": ""},  # odpada
        {"day": "5.09", "slogan": "", "alt": "", "href": ""},  # brak nazwy -> odpada
    ]
    result = parse_cards(cards, TODAY)
    assert len(result) == 2
    scorpions, cup = result
    assert scorpions.name == "Scorpions"
    assert scorpions.start_date == scorpions.end_date == datetime.date(2026, 7, 25)
    assert scorpions.category == "koncert"
    assert scorpions.venue_lat is not None
    assert cup.name == "Final Pucharu X"  # nazwa ze sluga
    assert cup.start_date == datetime.date(2027, 1, 10)  # rok wywnioskowany
    assert cup.category == "sport"  # "puchar" w nazwie, nie hala
