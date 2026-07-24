# Stan projektu i roadmapa — 2026-07-20

Pełny przegląd: co jest gotowe, co brakuje do zamknięcia pilota, co brakuje
do pełnego produktu komercyjnego. Zweryfikowane wobec `docs/spec.md` (jedyne
źródło prawdy) i faktycznego stanu repo, nie z pamięci.

---

## 1. Co jest zrobione — rdzeń produktu (Sprinty 0–5, spec §10)

Wszystkie sprinty MVP ze specu są zaimplementowane i mają testy:

- **Fundament**: monorepo, schemat bazy (multi-tenant, §6.2), auth (JWT,
  argon2id), CI, role właściciel/recepcja.
- **Dane**: adapter Booking.com (§6.4-zgodny — robots.txt, rate limit, UA
  z kontaktem), harmonogram nocny, import iCal (tylko odczyt).
- **Eventy + monitoring**: panel kuracji, mediana rynku, presja dostępności,
  pierścienie odległości, mapa Polski.
- **Silnik rekomendacji v1**: regułowy, wyjaśnialny (7 czynników), z twardymi
  ograniczeniami min/max.
- **Dashboard + e-mail**: kalendarz, licznik wyniku (2 warianty), raport
  tygodniowy, one-tap accept z maila (token SHA-256, GET bez mutacji).
- **Produkcja (częściowo)**: RODO (eksport/usunięcie konta), publiczne raporty
  SEO dla miast, onboarding "wklej link".

## 2. Co jest zrobione — ta sesja (19–20.07.2026)

**Niezawodność:**
- Naprawa krytycznego bloku scrapingu (SSLKEYLOGFILE wstrzykiwany przez AV).
- Alert jakości danych (wykrywanie cichej degradacji scrapera).
- Hardening bazy (`connect_timeout`, `pool_pre_ping`), `start-dev.ps1` +
  autostart Harmonogramu zadań.

**Analityka (6 z 8 zaplanowanych funkcji A):**
- A1 rozkład cen (percentyle/widełki), A2 comp set segmentowy, A4 tempo
  rynku, A5 podaż rynku (nowy model + migracja + scraper), A6 heatmapa
  popytu, A7 spread floor–mediana.
- A3 (trend cen) i A8 (historyczny ślad eventów) świadomie odłożone —
  wymagają tygodni historii, nie pracy.

**Moduł B — import rezerwacji (kompletny, B1→B2→B3):**
- Model `Booking` + import CSV, prawdziwe ADR/RevPAR/obłożenie z rzeczywistych
  sprzedaży (nie modelowane jak AirDNA), licznik wyniku przełączony na
  rzeczywistą cenę sprzedaży zamiast szacunku — **domyka zarzut recenzenta
  "szacowany"**.

**Pokoje 1-osobowe (kompletne, fundament + powierzchnia):**
- Osobny lekki przebieg scrapera (tygodniowo, §6.4-świadomy — nie podwaja
  obciążenia), segmentacja `guests` we wszystkich zapytaniach agregujących,
  przełącznik w panelu monitoringu.

**Wizualizacja i pozycjonowanie:**
- Wykres wodospadowy czynników ceny (panel + landing) — nasz najmocniejszy,
  uczciwy dowód "wiesz DLACZEGO".
- Kopia landingu, cennik 3 pakiety (29/59/119 zł), audyt bezpieczeństwa,
  analiza konkurencji i rynku (13 pytań), szkice materiałów marketingowych.

---

## 3. Do zamknięcia PILOTA (małe, znane, w większości niekodowe)

To rzeczy, które NIE blokują startu pilota na zaufanych gospodarzach (spec:
konsultacja prawna i pełny hosting mogą czekać), ale powinny być zamknięte
zanim pilot faktycznie ruszy:

| Zadanie | Status | Koszt |
|---|---|---|
| Backup bazy z testem odtworzenia | ⏳ zdecydowane, niewdrożone | ~1h |
| `ADMIN_ALERT_EMAIL` w `.env` | ⏳ czeka na Twój adres | 2 min |
| Ranna kontrola pierwszego pełnego przebiegu z pokojami 1-os. (śr. 4:00) | ⏳ czeka na środę | 10 min |
| Reset hasła — obsługa ręczna dla 10 znanych pilotów | ✅ akceptowalne bez zmian kodu | — |
| Rejestracja pilotów wg `docs/pilot/playbook.md` | nie rozpoczęte | zależne od Ciebie |

**To jest realnie krótka lista** — kod pod pilota jest gotowy od strony
produktowej. Największe ryzyko dla pilota to wciąż infrastrukturalne (patrz
pkt 5) — laptop dev jako jedyny host.

---

## 4. Do PEŁNEGO PRODUKTU KOMERCYJNEGO — czego brakuje

Grupowane wg spec §5.2/§12 i decyzji z tej sesji. Kolejność = sugerowany
priorytet, nie sztywny wymóg.

### 4a. Infrastruktura (blokuje niezawodność, nie funkcje)
- **Wdrożenie VPS wariant 5b** (plan gotowy w `wdrozenie-vps-5b.md`,
  niewdrożony) — usuwa zależność od laptopa dev, który padał 6+ razy w tej
  sesji (Docker, MSIX, antywirus, aktualizacje Windows).
- Rozdzielone konta Postgres (app/migracje/backup), CSP na froncie,
  kontenery bez roota — z audytu bezpieczeństwa, naturalnie przy VPS.
- SPF/DKIM/DMARC dla domeny nadawczej (bez tego raporty tygodniowe → spam).

### 4b. Płatności i prawo (blokuje pobieranie pieniędzy)
- **Wdrożenie Stripe Billing + Fakturownia** (zdecydowane 19.07, kod
  niewdrożony) — KSeF obowiązkowy dla B2B od 1.04.2026, więc to nie jest
  opcjonalne dla realnego uruchomienia płatnego.
- **Konsultacja prawna** (§6.4 scraping, regulamin B2B z ograniczeniem
  odpowiedzialności, RODO) — odroczona świadomie do "przed publicznym
  startem"; jeśli pilot wypali, ten moment właśnie nadszedł.
- Cennik/UI checkout na stronie (dziś jest tylko propozycja w dokumentach,
  nie w kodzie frontu).

### 4c. Bezpieczeństwo przy skali (z audytu 19.07, nieblokujące pilota)
- Self-service reset hasła (z neutralnym komunikatem, bez enumeracji kont).
- MFA dla roli kuratora/administratora.
- Audit log operacji wrażliwych (logowania, zmiana hasła, płatności, eksport).
- Webhooki Stripe: weryfikacja podpisu + idempotencja (naturalna część 4b).

### 4d. Głębia produktu (wzmacnia ofertę, nie blokuje)
- **Write-back cen przez IdoBooking** — spec nazywa to "priorytet #1 fazy 2,
  PRZED modelami ML" (§5.3) i "główne przewidywane źródło churnu" dopóki
  brak. Rekonesans API zrobiony (19.07), niewdrożone. To pojedynczy
  najcenniejszy brakujący kawałek dla realnej retencji klienta.
- A3 (trend cen) i A8 (ślad eventów) — odblokują się same z czasem, zero
  dodatkowej pracy.
- Pierścieniowa heatmapa presji (Leaflet/OSM) — "bajer" z listy, nie
  zaczęty.
- Reguły niestandardowe per data/event (z analizy konkurencji, pkt 9) —
  rozszerzenie silnika, Faza 2.

### 4e. Wzrost i partnerstwa (poza kodem)
- Kontakt z PSWK (szkic gotowy — patrz `szkice-marketingowe-2026-07-20.md`).
- Content o CWTON jako lead magnet (szkic gotowy, **wymaga weryfikacji
  prawnej faktów przed publikacją**).
- Rozmowy handlowe z IdoBooking/Hotres — jednocześnie kanał write-backu i
  dystrybucji.

### 4f. Świadomie POZA zakresem (spec §5.3) — z jedną zmianą kontekstu
- Natywne aplikacje mobilne — nadal poza zakresem, tylko web.
- Modele ML/elasticity — nadal Faza 2, PO write-backu, PO zebraniu danych.
- Token/blockchain — wycięte całkowicie, bez zmian.
- **Moduł compliance/regulacyjny — spec mówi "do rozważenia, gdy polskie
  regulacje się skonkretyzują". CWTON (20.05.2026) właśnie to zrobił.**
  To nie jest automatyczny sygnał do budowy (§11 — nie budujemy bez
  zmierzonej potrzeby), ale warunek odroczenia przestał obowiązywać —
  świadoma decyzja founderska, czy i kiedy to otworzyć, nie milczące
  pominięcie.

---

## 5. Największe pojedyncze ryzyko na start komercyjny

Nie techniczne — **infrastrukturalne i prawne jednocześnie**:
1. Cały system wciąż działa na laptopie deweloperskim. VPS jest zaplanowany,
   nie wdrożony. Każdy dzień zwłoki to dzień, w którym awaria maszyny = noc
   bez danych.
2. Płatności i KSeF są zdecydowane, ale niewdrożone — nie da się pobrać
   pierwszej złotówki bez tego kroku.

Rekomendacja kolejności (bez zmian względem wcześniejszej sesji, potwierdzona
tym przeglądem): **VPS → płatności/prawnik → bezpieczeństwo przy skali →
write-back**. Pilot może ruszyć równolegle na dzisiejszej infrastrukturze
(świadome ryzyko, akceptowalne dla 5–10 zaufanych gospodarzy), ale
komercjalizacja — nie.
