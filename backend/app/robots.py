"""Poprawny odczyt robots.txt — naszym User-Agentem (§6.4).

RobotFileParser.read() pobiera robots.txt DOMYŚLNYM UA urllib, który część
witryn blokuje (403) — a wtedy robotparser interpretuje to jako "zabroń
wszystkiego" i fałszywie blokuje dozwolone ścieżki. Pobieramy więc robots.txt
tym samym UA, którym będziemy crawlować, i dopiero parsujemy.
"""

import urllib.robotparser

import httpx


def read_robots(base_url: str, user_agent: str) -> urllib.robotparser.RobotFileParser:
    parser = urllib.robotparser.RobotFileParser()
    url = f"{base_url.rstrip('/')}/robots.txt"
    try:
        response = httpx.get(
            url, headers={"User-Agent": user_agent}, timeout=15, follow_redirects=True
        )
    except httpx.HTTPError:
        parser.allow_all = True  # brak dostępu do robots -> brak ograniczeń (RFC 4xx)
        return parser
    if response.status_code == 200:
        parser.parse(response.text.splitlines())
    else:
        # 4xx (brak/zakaz robots) -> dozwolone; 5xx traktujemy tak samo zachowawczo jak stdlib
        parser.allow_all = True
    return parser
