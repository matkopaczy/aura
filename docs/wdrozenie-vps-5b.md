# Wdrożenie hybrydy 5b (VPS + scraper na łączu domowym) — plan

Decyzja foundera 2026-07-19: wariant 5b. Cel: baza, API, front i joby
nie-scrapingowe przenieść na VPS w UE (niezawodność, §9), a scraper cen
zostawić na łączu rezydencjalnym (mniejsze ryzyko blokady IP, §6.4).
Dokument jest planem do akceptacji — nie uruchamiam serwera bez zgody
(koszt, konto foundera).

Kontekst pilności: w ciągu 3 dni (17–19.07) środowisko padło ≥5 razy
(Docker ×2, nakładka MSIX, antywirus/SSLKEYLOGFILE, reset z aktualizacji
Windows). Każdy pad w oknie 03:00 = noc bez danych. AuraDev + start-dev.ps1
to łata na jednej maszynie; VPS zdejmuje problem dla wszystkiego oprócz
samego scrapingu.

## Podział odpowiedzialności

**VPS (Hetzner CX22, Falkenstein/Nürnberg, ~5 €/mies., 2 vCPU / 4 GB / 40 GB):**
- Postgres 16 (jedyne źródło prawdy; backup tutaj)
- backend API (uvicorn za reverse proxy Caddy — automatyczny TLS/HSTS)
- frontend (Next, za tym samym Caddy)
- scheduler-core: iCal (01:00), atrybucja (05:00), raporty pn (07:00),
  eventy pn (04:00), kontrola jakości (08:00). Wychodzące HTTP tych jobów
  idzie do oficjalnych kalendarzy eventów i iCal gości — nie do Bookinga,
  więc IP datacenter jest OK.
- kontrola jakości danych pilnuje scrapera „z zewnątrz": jeśli laptop nie
  zescrapuje (padł, uśpiony), wolumen leci w dół → alert. To automatyczny
  nadzór nad najbardziej zawodnym elementem.

**Laptop (łącze domowe):**
- scheduler-scraper: tylko `market_scrape` 03:00/rynek (+ floor nocowanie.pl)
- pisze do Postgresa na VPS przez tunel WireGuard (baza NIE wystawiona
  publicznie — nasłuch tylko na interfejsie wg + localhost)
- dalej pod AuraDev + start-dev.ps1 (idempotentne), ale teraz jedyną jego
  robotą jest scraping; pad laptopa nie kładzie API ani frontu

Playwright zostaje na laptopie, więc VPS nie potrzebuje przeglądarki ani
dużego RAM — stąd tańszy CX22 zamiast CX32.

## Zmiana w kodzie (mała, §11)

Jeden przełącznik roli w `scheduler.py`:

```
AURA_SCHEDULER_ROLE = core | scraper | all   (domyślnie all — dev na 1 maszynie)
```

`build_scheduler(role)` dodaje tylko joby swojej roli: `scraper` → pętla
`scrape:*`; `core` → iCal/atrybucja/raporty/eventy/jakość; `all` → wszystko
(bez zmian dla dev i testów). Zero nowych zależności. Test: `role="core"`
nie rejestruje jobów `scrape:*`, `role="scraper"` rejestruje wyłącznie je.

## Sieć i bezpieczeństwo (z audytu 2026-07-19, sekcja B/VPS)

- WireGuard laptop↔VPS; Postgres `listen_addresses` = localhost + IP wg;
  `pg_hba` puszcza tylko podsieć wg. Baza nigdy nie widoczna z internetu.
- Caddy jako reverse proxy: automatyczny Let's Encrypt, HSTS, nagłówki
  bezpieczeństwa; API i front tylko przez niego (nie wystawiać portów
  8000/3000 wprost).
- Kontenery nie jako root; sekrety w `.env` na VPS (poza repo), nie w obrazie.
- Rozdzielone konta Postgres: `aura_app` (CRUD), `aura_migrate` (DDL),
  `aura_backup` (readonly) — sekcja B/6 audytu.
- CSP na froncie Next (sekcja B/4).

## Backup (decyzja „backup bez testu odtworzenia to nie backup")

- `pg_dump` nocny (po 08:00, po kontroli jakości) → plik szyfrowany na VPS.
- Kopia poza VPS: cotygodniowy transfer na niezależny magazyn (np. Hetzner
  Storage Box / S3 UE).
- Test odtworzenia raz w tygodniu: dump → świeża baza `aura_restore_test` →
  sanity-check liczby wierszy `price_observations`. Zautomatyzować jako job.

## Kolejność wdrożenia (szacunek: 1 dzień roboczy)

1. VPS + Docker + WireGuard + Caddy (szkielet, TLS działa na domenie).
2. Postgres na VPS; `pg_dump` z dev → `pg_restore` na VPS; weryfikacja liczb.
3. Przełącznik roli w `scheduler.py` (+ test) — jedyna zmiana w kodzie.
4. Deploy API + front (Compose); smoke-test publicznych endpointów przez Caddy.
5. Laptop: `AURA_SCHEDULER_ROLE=scraper`, `DATABASE_URL` na IP wg; jeden
   ręczny `market_scrape` i podgląd danych w bazie VPS (DoD: realny fetch).
6. Backup + test odtworzenia jako joby; alert jakości na `ADMIN_ALERT_EMAIL`.
7. Przepięcie DNS/landing na VPS; wygaszenie uvicorna/frontu na laptopie.

## Do domówienia z founderem przed startem

- Domena docelowa (dla TLS i publicznych raportów SEO).
- Dostawca kopii zapasowej poza VPS (Storage Box vs S3).
- Czy front też na VPS od razu, czy zostaje na obecnym hostingu do czasu
  przepięcia (jeśli jest osobny) — dziś front chodzi lokalnie, więc VPS.
