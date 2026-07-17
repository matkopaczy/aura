# CLAUDE.md — jak pracować w tym repo

Aura: SaaS B2B — dynamiczny pricing dla samodzielnych gospodarzy najmu
krótkoterminowego w Polsce. Mówimy gospodarzowi, jaką cenę ustawić na każdą noc
i DLACZEGO. Nie przejmujemy rezerwacji.

**Jedyne źródło prawdy o produkcie: `docs/spec.md` (v1.1).** Sekcje §6.2
(global-ready), §6.4 (etyka scrapingu) i §11 (zasady realizacji) są
niepodważalne — gdy wybór stoi między "sprytnie" a "zgodnie ze specem",
wygrywa spec. Decyzje founderskie nadpisujące spec (np. rozbicie Trójmiasta
na Gdańsk/Gdynia/Sopot) zapadają wyłącznie w rozmowie z użytkownikiem —
nigdy nie podejmuj ich samodzielnie.

## Twarde zasady (łamiesz = wracasz)

1. **Multi-tenant**: każda tabela biznesowa dziedziczy `TenantMixin`
   (`account_id`); KAŻDE zapytanie o dane biznesowe filtruje po
   `account_id`. Cudzy zasób = **404**, nigdy 403 (nie zdradzamy istnienia).
   Wyjątki (dane globalne, bez account_id): `markets`, `events`,
   `competitor_listings`, `price_observations`, `floor_signals`,
   `waitlist_entries` — lista zamknięta, egzekwowana testem strażniczym.
   Decyzja (2026-07): na pilota izolacja wyłącznie aplikacyjna; RLS
   w Postgresie dopiero przed komercjalizacją (§11 — bez infry na zapas).
2. **Enumy**: `enum.StrEnum` + `Enum(..., native_enum=False, length=20)`.
   **W bazie leżą NAZWY członków** (`"APPROVED"`, `"RECOMMENDATIONS"`), nie
   wartości. Surowy SQL porównuje z nazwą; Python porównuje z członkiem enuma.
3. **Pieniądze**: `Numeric(10, 2)` + `Decimal`, zawsze z kolumną
   `currency_code` (ISO 4217) obok. Bez założenia PLN. Bez floatów w kwotach.
4. **Czas**: w bazie wyłącznie UTC (`DateTime(timezone=True)`, `TimestampMixin`,
   `utcnow()` z `app.models.base`). Logika "dzisiaj/jutro" — w strefie rynku:
   `datetime.now(ZoneInfo(market.timezone)).date()`. Naiwny `DateTime` wywala
   test strażniczy.
5. **i18n — zero sklejanych zdań**: każdy tekst widoczny dla użytkownika to
   klucz szablonu + parametry. Frontend: `frontend/src/messages/pl.json` +
   `useTranslations`. Backend (e-maile, strony akcji): `app/i18n/pl.json` +
   `t(key, **params)`. Wyjaśnienia rekomendacji: klucz + `explanation_params`,
   renderowane po stronie klienta (`lib/explanations.ts`). Napis inline w
   komponencie/mailu = błąd.
6. **Rynek jako dane**: nowe miasto = wiersz w `markets` (seed), nie kod.
   Poziom pokrycia (`coverage_level`) steruje funkcjami, nie if-y po slugach.
7. **§11**: jedna ścieżka, bez fallbacków; fail fast (brak konfiguracji =
   brak startu, brak klucza i18n = KeyError); zmiany chirurgiczne; żadnej
   infrastruktury "na zapas" (Redis, kolejki, mikroserwisy — dopiero przy
   zmierzonym problemie); jedna odpowiedzialność na funkcję.
8. **Język**: cały UI, e-maile, komentarze w kodzie, komunikaty commitów —
   po polsku. Identyfikatory w kodzie — po angielsku.

## Mapa kodu (gdzie co żyje)

Backend (`backend/app/`, Python 3.12, FastAPI + SQLAlchemy 2 `Mapped` + Alembic,
Postgres 16):

| Moduł | Odpowiedzialność |
|---|---|
| `engine.py` | silnik regułowy: czyste funkcje czynników `-> Factor \| None`, stałe strojenia NA GÓRZE pliku |
| `monitoring.py` | mediany/obłożenie/pace z obserwacji; mediana segmentowa; pierścienie odległości; mapa obłożenia |
| `attribution.py` | licznik wyniku: pełny + konserwatywny (≥ mediana konkurencji) |
| `action_tokens.py` | one-tap decyzje z maila: token=zdolność, w bazie tylko SHA-256, jednorazowy |
| `scraping/` | ceny konkurencji: `SourceAdapter` (per-data, booking) i `FloorAdapter` (bezdatowy, nocowanie) |
| `event_sources/` | zasilanie eventów z oficjalnych kalendarzy; wspólne helpery w `base.py` |
| `robots.py` | `read_robots(base, ua)` — JEDYNY sposób czytania robots.txt |
| `api/` | routery; publiczne w `public.py` i `actions.py`, reszta za JWT |
| `seed.py` | rynki + eventy kuratorskie + ferie MEN; idempotentny; NADPISUJE `coverage_level` z listy `MARKETS` |
| `scheduler.py` | APScheduler: scraping 03:00/rynek, iCal 01:00, atrybucja 05:00, raporty pn 07:00, eventy pn 04:00 |

Frontend (`frontend/src/`, Next 15 App Router + next-intl, TS strict):
`app/` — strony (`rynek/[slug]` = publiczne raporty SEO, server component);
`lib/api.ts` — JEDYNY klient HTTP (typy + fetchery; **sprawdź, czy fetcher już
istnieje, zanim dodasz** — była już raz zdublowana `getMarketEvents`);
`lib/publicServer.ts` — fetch serwerowy (ISR) dla stron SEO;
`messages/pl.json` — wszystkie teksty.

## Migracje Alembic — procedura

1. Zmień model w `app/models/`, wyeksportuj w `models/__init__.py` (+ `__all__`).
2. Napisz migrację RĘCZNIE w stylu istniejących (`alembic/versions/`):
   docstring po polsku z § specu, `down_revision` = aktualna głowa.
   **Nie ufaj autogeneracji** — dodaje fałszywy alter na `price_observations`
   (historyczny artefakt); jeśli jej używasz, wytnij go.
3. Pułapki: autoinkrement na SQLite wymaga
   `BigInteger().with_variant(Integer, "sqlite")`; enum w migracji =
   `sa.Enum('NAZWA1', 'NAZWA2', name='...', native_enum=False, length=20)`.
4. Zastosuj i zweryfikuj na dev (patrz komendy w DoD).

## Testy — jak i pułapki

- Testy jeżdżą na **SQLite** (produkcja/CI-migracje na Postgresie). Skutki:
  SQLite gubi tzinfo — porównując `DateTime` z bazy koercuj
  (`dt.replace(tzinfo=UTC)` gdy naiwny; wzorzec `_as_utc` w `billing.py`
  i `action_tokens.py`).
- `tests/test_design_rules.py` = testy strażnicze §6.2 (nowa tabela bez
  `account_id`, naiwny DateTime, kwota bez waluty → czerwono). Nowa tabela
  globalna wymaga świadomego dopisania do listy wyjątków w tym teście.
- Rate limiter auth jest w pamięci procesu — conftest woła
  `reset_rate_limit()`; jeśli piszesz testy auth poza standardowym `client`,
  pamiętaj o tym.
- Decimal z API porównuj przez `Decimal(...)`, nie przez format stringa
  ("200" vs "200.00").
- Konta dev (lokalne fikstury w dev-Postgresie, NIE sekrety — nic nie chronią
  poza localhostem): `smoke@example.com` / `smoke-test-haslo-123` (kurator,
  obiekt "Apartament Stary Rynek" w Poznaniu), `roles_owner@` /
  `roles_rec@example.com`. Prawdziwe sekrety wyłącznie w `.env`
  (niewersjonowany).

## Scraping i źródła eventów — §6.4 (prawnie wrażliwe)

Checklist przed JAKIMKOLWIEK nowym fetch-em zewnętrznym:
1. `read_robots(base_url, USER_AGENT)` + `can_fetch` na dokładny URL.
   **Nigdy** `RobotFileParser.read()` (używa domyślnego UA urlliba, część
   witryn go 403-uje i parser fałszywie blokuje wszystko).
2. Nasz UA z kontaktem (`app/scraping/booking.py:USER_AGENT`) we WSZYSTKICH
   zapytaniach, także Playwright context.
3. Anty-bota NIE obchodzimy (Booking strony obiektów serwują challenge —
   zwracamy 503, nie kombinujemy). Żadnych proxy-rotacji, żadnego udawania
   człowieka.
4. Odstępy między zapytaniami (2,5 s wzorzec bookinga); praca nocna dla
   masowego scrapingu; Playwright blokuje obrazy/fonty (`context.route`).
5. Przechowujemy tylko: ceny, dostępność, typ jednostki, rating, lokalizację
   ogólną, udogodnienia. Żadnych zdjęć, opisów, opinii.

Nowe źródło eventów — kolejność rekonesansu (od najtańszego):
1. tribe REST: `/wp-json/tribe/events/v1/events` (wzorzec: `tribe.py`),
2. WP REST typy: `/wp-json/wp/v2/types` — czy custom post type wystawiony
   Z DATAMI (uwaga: często `acf` puste = bez dat = ślepa uliczka),
3. podejrzyj XHR kalendarza Playwrightem (`page.on("request")`) — endpointy
   typu `calendar-graphic.php?month=` (`pge.py`) albo `admin-ajax.php`
   z akcją (`stulecia.py`, `tarczynski.py`); admin-ajax jest standardowo
   dozwolony w robots WP,
4. w odpowiedziach szukaj bloków **JSON-LD schema.org Event** — dane
   strukturalne > selektory CSS (`tarczynski.py`),
5. SSR HTML przez httpx + regex (`katowice.py`, `stulecia.py`),
6. Playwright render DOM — ostateczność (`mtp.py`, `trojmiasto.py`,
   `atlasarena.py`).

Zasady źródeł: kandydaci ląduja jako **DRAFT** (kurator zatwierdza w
`/admin/events`); ingest idempotentny po `(market, name, start_date)` i NIGDY
nie nadpisuje decyzji kuratora; serie cykliczne (joga, jam session) tnie
`drop_recurring_series`; kategorie z nazwy — `category_from_name`; wystąpienia
dzienne scala `merge_consecutive_days`; nowe źródło rejestrujesz w
`ingest.all_sources()`. Eventy mają sens tylko dla rynków
`coverage=recommendations`; przy nazwach pól z witryn uważaj na pułapki typu
"SPORT ARENA" = nazwa hali, nie kategoria. Daty słowne: usuń rok z tekstu
PRZED tokenizacją dni (`\d{1,2}` łyka "2026" jako 20+26).

## Silnik cen — jak dodać czynnik

Czysta funkcja `_nazwa_factor(...) -> Factor | None` w `engine.py`; stałe
(progi, mnożniki) na górze pliku z komentarzem; dołącz do listy `candidates`
w `compute_recommendation`; klucz czynnika + szablon po polsku w
`frontend/src/messages/pl.json` (sekcja `explanations`) i — jeśli występuje
w mailach — w `app/i18n/pl.json` (`factor.*`); test jednostkowy na progi.
Czynniki wymagające kalibracji, której nie mamy — NIE zgadujemy (patrz §11);
przykład: ferie dodane tylko do rynków, gdzie kierunek wpływu jest pewny.

## Środowisko dev (Windows!) — rzeczy, które gryzą

- **TLS interception** (antywirus podmienia certy): naprawione globalnie przez
  `truststore.inject_into_ssl()` w `app/__init__.py`. NIE wyłączaj weryfikacji
  SSL. Jeśli `pip`/`git` płacze o certy — to ta sama przyczyna.
- Baza: `docker start aura-db-1` (kontener istnieje; `docker compose up -d db`
  tylko przy pierwszym uruchomieniu). Po restarcie Windows Docker Desktop
  bywa martwy — najpierw on.
- Backend: uruchamiaj Z KATALOGU `backend/` (`.env` ładuje się stamtąd):
  `./.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000`.
  Bez `--reload` — po zmianie kodu ubij proces (netstat → taskkill) i wystartuj
  ponownie; nie zakładaj, że działający serwer ma twój nowy kod.
- Alembic wymaga env: `export DATABASE_URL="postgresql+psycopg://aura:aura@localhost:5432/aura"`.
- Frontend: przez `.claude/launch.json` (`name=frontend`, port 3000).
  **Next trzyma fetch-cache ISR NA DYSKU** (`frontend/.next/cache/fetch-cache`)
  — restart dev serwera go NIE czyści; po zmianie listy rynków usuń katalog.
- E-mail dev: `python -m aiosmtpd -n -l localhost:1025` + `SMTP_HOST=localhost`,
  `SMTP_PORT=1025` w `.env`.
- Konsola Windows = cp1250: printy z polskimi/unicode znakami w skryptach
  owijaj `io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")`.
- Seed: `./.venv/Scripts/python.exe -m app.seed` (idempotentny). Ingest eventów
  ręcznie: `python -m app.event_sources.ingest`.

## Definition of Done — zanim powiesz "gotowe"

Praca NIE jest skończona, dopóki wszystkie kroki nie są zielone:

```bash
cd backend
./.venv/Scripts/python.exe -m ruff check .        # lint (CI to sprawdza!)
./.venv/Scripts/python.exe -m pytest -q            # CAŁA suita, nie tylko nowe testy
# jeśli była migracja:
export DATABASE_URL="postgresql+psycopg://aura:aura@localhost:5432/aura"
./.venv/Scripts/python.exe -m alembic upgrade head
docker exec aura-db-1 psql -U aura -d aura -c "\d nazwa_tabeli"   # kolumna/tabela istnieje
```

Frontend przy KAŻDEJ zmianie w `frontend/` (oba kroki są też w CI):

```bash
cd frontend
npm run lint        # eslint; reguła set-state-in-effect = warn (3 stare miejsca)
npm run typecheck   # tsc --noEmit
```

oraz: strona renderuje się w podglądzie bez błędów w konsoli/logach dev serwera.

Ponadto:
1. **Weryfikacja na żywo, nie tylko testy**: nowy endpoint → curl/przeglądarka
   na działającym serwerze; nowy scraper/źródło → jeden realny fetch i obejrzyj
   próbkę danych (złapaliśmy tak mislabelowane koncerty jako "sport" i kategorię
   z nazwy hali); zmiana UI → render + zrzut/odczyt strony. Po refaktorze
   scrapera — ponowny realny fetch, nawet gdy testy przechodzą.
2. Nowe stringi UI mają klucze w `pl.json` (obu, jeśli dotyczy maili).
3. Migracja zastosowana na dev-bazie i zweryfikowana (nie tylko plik w repo).
4. Nowa logika = nowe testy (suita ma rosnąć razem z kodem; guardian testy
   nietknięte, chyba że świadomie rozszerzasz listę wyjątków).
5. Commit po polsku: pierwsza linia = co i po co (z § specu, jeśli dotyczy),
   body = decyzje i pułapki, stopka `Co-Authored-By: Claude <model>`.
   Commituj na `main` dopiero, gdy wszystko powyżej zielone; po zakończonym
   wątku `git push origin main`.
6. Sprzątnij po sobie: dane demo z bazy, procesy tła (uvicorn na portach
   pomocniczych), pliki tymczasowe poza scratchpadem.

## Czego NIE robić (najczęstsze błędy)

- Nie dodawaj zależności/warstw bez wyraźnej potrzeby (§11). Nowa biblioteka =
  pytanie do użytkownika.
- Nie pisz `try/except` połykających błędy "na wszelki wypadek" — fail fast.
  Wyjątki: pętle po źródłach/rynkach, gdzie jeden padły element nie może
  zatrzymać reszty (wzorzec w `ingest.run()` i `scheduler.py`) — zawsze
  z logowaniem `exception`.
- Nie obchodź anty-botów, nie ignoruj robots.txt, nie zwiększaj częstotliwości
  scrapingu (§6.4 — ryzyko prawne całego produktu).
- Nie porównuj enumów z wartościami w surowym SQL (w bazie są NAZWY).
- Nie zostawiaj `main` czerwonego (ruff/pytest) — CI leci na każdy push.
- Nie twórz drugiej ścieżki dla tej samej operacji (drugi klient HTTP, drugi
  parser robots, drugi fetcher tego samego endpointu).
- Nie podejmuj decyzji produktowych (ceny, gwarancje, rynki, publiczne treści
  o konkurencji) — to decyzje foundera; zaproponuj i zapytaj.
