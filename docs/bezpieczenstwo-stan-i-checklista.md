# Bezpieczeństwo: stan faktyczny vs checklista SaaS (audyt 2026-07-19)

Zewnętrzna checklista bezpieczeństwa zderzona z faktycznym stanem repo
(każdy punkt „mamy" ma wskazany plik-dowód). Podział: co jest, co jest
realną luką (z terminem sensownego domknięcia), co jest świadomie
przedwczesne wg §11 specu.

## A. Mamy — z dowodem w kodzie

| Punkt checklisty | Stan | Dowód |
|---|---|---|
| Argon2 (2) | Argon2id z argon2-cffi, salt automatyczny | `auth/security.py` |
| Jeden komunikat błędu logowania (5) | `invalid_credentials` dla obu przypadków + `is_active` | `auth/router.py:67` |
| Rate limit logowania/rejestracji (5,7) | 10/60 s per IP, 429 | `hardening.py` |
| Nagłówki bezpieczeństwa (17) | nosniff, X-Frame-Options DENY, Referrer-Policy | `hardening.py:SECURITY_HEADERS` |
| CORS nie "*" (17) | lista originów z konfiguracji | `main.py` + `config.py` |
| Autoryzacja per zasób + tenant (3) | `account_id` w każdym zapytaniu, cudzy zasób = 404 (nie 403), test strażniczy | `tests/test_design_rules.py` |
| UUID zamiast sekwencji (11) | id zasobów to UUID | modele |
| Walidacja wejścia (11) | Pydantic na każdym endpointcie, hasło min. 10 znaków | routery |
| Tokeny akcji z maila | w bazie tylko SHA-256, jednorazowe, TTL, GET bez mutacji / POST decyduje | `action_tokens.py`, `api/actions.py` |
| Scraper poza requestem (1,12) | osobny proces (scheduler), nigdy w ścieżce użytkownika | `scheduler.py` |
| Brak danych kart (10) | kierunek: Stripe, backend zna tylko id/status subskrypcji | `decyzje-przedstartowe.md` §1 |
| Sekrety poza repo (15) | `.env` niewersjonowany; brak sekretów w logach | `.gitignore`, przegląd logów |
| Monitoring błędów (19) | Sentry opcjonalne (DSN z env) | `hardening.py:init_sentry` |
| Zasady „Vibe Coding" (25,26) | fail fast, bez fallbacków, najmniejsza zmiana, dowód przed zmianą, decyzje produktowe tylko founder | `CLAUDE.md` całość |

## B. Realne luki — z terminem domknięcia

**Przed pilotem (tanie, robimy zaraz):**
1. **Backup bazy z testem odtworzenia** (16) — najcenniejszy zasób
   (`price_observations`) bez kopii; „backup bez testu odtworzenia nie jest
   backupem" — przyjęte: procedura = pg_dump nocny + odtworzenie próbne do
   świeżej bazy raz w tygodniu. (Już na liście ryzyk z 2026-07-19.)
2. **Alert jakości danych scrapingu** (19) — w planie na jutro rano.

**Przy przejściu na VPS (deploy checklist):**
3. TLS + **HSTS** (17) — bez sensu na localhost, obowiązkowe za reverse proxy.
4. **CSP** na froncie Next (17).
5. Kontenery **bez roota**, baza niedostępna publicznie (bind na sieć
   wewnętrzną), minimalne uprawnienia (15).
6. **Rozdzielenie kont DB**: aplikacja / migracje / backup (16).
7. **SPF, DKIM, DMARC** dla domeny nadawczej (13) — już na liście ryzyk (e-mail
   deliverability); bez tego raporty tygodniowe lądują w spamie.
8. Reverse proxy z rate limitem na poziomie edge; Cloudflare do rozważenia
   dopiero przy ruchu publicznym (22).

**Przed komercjalizacją (po pilocie):**
9. **Reset hasła** — dziś BRAK ścieżki (jedyny plik z „reset" to rate
   limiter); na pilocie obsługa ręczna (10 znanych osób), publicznie —
   obowiązkowy, z neutralnym komunikatem „jeżeli konto istnieje…" (6).
10. **Rejestracja zwraca 409 email_taken** — enumeracja kont (4/6). Na
    pilocie akceptowalne (rejestracja de facto zaproszeniowa); publicznie —
    neutralna odpowiedź + aktywacja przez e-mail (domyka też pkt 4).
11. **Token w sessionStorage** → HttpOnly Secure Cookie + krótki access
    token z odświeżaniem i „wyloguj wszędzie" (2). Świadomy dług: XSS-owa
    ekspozycja tokenu; mitygacja dziś = React escapuje + zero obcych
    skryptów + token 30 min.
12. **MFA dla kuratora/admina** (2,20) — spec §9 mówi „2FA po MVP"; przy
    komercjalizacji kurator = najcenniejsze konto, MFA obowiązkowe.
13. **Audit log** operacji wrażliwych (24) — logowania, zmiany hasła/e-maila,
    płatności, eksport/usunięcie danych.
14. **Webhooki Stripe**: weryfikacja podpisu + idempotencja (10) — częścią
    wdrożenia płatności, nie osobnym projektem.
15. Eksport danych i usunięcie konta na żądanie (9) — wymagane też przez
    RODO (§9 specu); potwierdzić w przeglądzie prawnym.

## C. Świadomie przedwczesne (§11: bez infry na zapas)

- **Redis, kolejki, workery, DLQ** (1,12,13,14,21) — pilot działa na jednej
  maszynie; decyzja udokumentowana w `hardening.py` (docstring). Wchodzą
  przy zmierzonym problemie skali, nie wcześniej.
- **SMS i WhatsApp** (14) — nie ma ich w produkcie ani w specu MVP; sekcja
  checklisty bezprzedmiotowa do czasu decyzji produktowej.
- **CAPTCHA, fingerprinting, detekcja botów** (4,8) — brak publicznego
  ruchu; rate limit per IP wystarcza na pilota.
- **WAF/Cloudflare** (22) — rozważyć przy publicznym starcie; uwaga na
  konflikt interesów: sami scrapujemy, więc „automatyczne blokowanie botów"
  u nas musi przepuszczać nasze własne healthchecki.
- **Szyfrowanie e-maili/telefonów w bazie** (9) — dane osobowe ograniczone
  do e-mail + nazwa obiektu (§9); szyfrowanie at rest zapewni managed
  Postgres na produkcji; szyfrowanie per kolumna = koszt bez wyraźnego
  zysku na tym etapie. Do potwierdzenia w przeglądzie prawnym (RODO).
- **Osobne logowanie panelu administracyjnego** (20) — kurator to rola
  w tej samej aplikacji (decyzja architektoniczna specu); wzmocnienie
  przez MFA (pkt B12) zamiast osobnego systemu.

## Zasada ogólna

Checklista potwierdza kierunek repo: żaden punkt „A" nie wymagał poprawki
po audycie, luki „B" mają naturalne miejsce w harmonogramie (VPS /
komercjalizacja), a sekcja „C" to dokładnie te rzeczy, przed którymi §11
broni projekt. Największa wartość z listy: pkt 16 („backup bez testu
odtworzenia nie jest backupem") — przyjęty do procedury backupów.
