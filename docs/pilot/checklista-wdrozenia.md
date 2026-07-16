# Checklista wdrożenia produkcyjnego (przed pilotem)

Kolejność: infrastruktura → sekrety → dane → weryfikacja → dopiero potem gospodarze.

## Infrastruktura (region UE, §9)

- [ ] Managed PostgreSQL 16 w regionie UE, szyfrowanie at rest, automatyczne backupy (szyfrowane).
- [ ] 1–2 maszyny / usługi zarządzane na backend (FastAPI) + hosting frontu (Next.js).
- [ ] Osobny proces/serwis na scheduler (`python -m app.scheduler`) — scraping nocny,
      raporty, atrybucja. NIE uruchamiać wielu instancji schedulera naraz.
- [ ] Domena + TLS wszędzie (§9). CORS_ORIGINS ustawione na produkcyjny host frontu.

## Sekrety i konfiguracja (§9 — nigdy w repo)

- [ ] `SECRET_KEY` — wygenerowany losowo (`openssl rand -hex 32`), inny niż dev.
- [ ] `DATABASE_URL` — do managed Postgresa.
- [ ] `SMTP_*` — realny dostawca e-mail (raporty i alerty). `EMAIL_FROM` z własnej domeny.
- [ ] `SENTRY_DSN` — projekt Sentry założony, DSN ustawiony (monitoring błędów, §6.1).
- [ ] `DASHBOARD_URL` — produkcyjny URL (linki w e-mailach).
- [ ] `DEFAULT_PRICE_PER_PROPERTY` — cena pilotowa (start 49 zł, §12 pkt 4).

## Baza i dane

- [ ] `alembic upgrade head` na produkcyjnej bazie.
- [ ] `python -m app.seed` — 29 rynków + eventy pierwszej fali.
- [ ] Weryfikacja kuracji eventów: konto kuratora (`users.is_curator = true`), przejście
      przez szkice w `/admin/events` i zatwierdzenie realnych dat 2026/27.
- [ ] Uruchomienie **pierwszego pełnego scrapingu** dla rynków rekomendacji przed onboardingiem
      (żeby mediany były gotowe). Zmierzyć czas — przy 60 datach × 2 strony × rate limit 2,5 s
      to kilkadziesiąt minut per rynek; rozważyć ograniczenie monitoringu do 1 strony/datę.

## Bezpieczeństwo i RODO (§9)

- [ ] Polityka prywatności (`/prywatnosc`) sprawdzona przez założyciela.
- [ ] Rejestr czynności przetwarzania + wzór umowy powierzenia dla klientów B2B (poza kodem —
      lista założyciela).
- [ ] Test RODO: eksport konta (`/api/account/export`) i usunięcie konta działają na produkcji.
- [ ] Dostęp do produkcji tylko po kluczu; brak sekretów w repo (potwierdzone — `.gitignore`).
- [ ] Nagłówki bezpieczeństwa i rate limit na `/auth` aktywne (middleware `hardening.py`).

## Weryfikacja end-to-end (na produkcji, przed pierwszym gospodarzem)

- [ ] Rejestracja → triał 30 dni widoczny na dashboardzie.
- [ ] Podgląd rynku i zapis na listę oczekujących (lead magnet) działają bez logowania.
- [ ] Wygenerowanie rekomendacji dla testowego obiektu → wyjaśnienia po polsku.
- [ ] Raport tygodniowy dociera na realną skrzynkę (nie tylko lokalny SMTP).
- [ ] Sentry odbiera zdarzenie testowe.

## Świadome długi (do decyzji założyciela — §12)

- [ ] Konsultacja prawna scrapingu + regulaminy OTA + polityka prywatności PRZED publicznym
      startem (nie przed pilotem na zaufanych gospodarzach).
- [ ] Operator płatności (Stripe vs P24) — pilot działa na fakturze ręcznej (ManualProvider),
      decyzja i integracja po walidacji ceny.
- [ ] Nazwa i domena produktu.
