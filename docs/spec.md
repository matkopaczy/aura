# Specyfikacja produktu i MVP — dynamiczny pricing dla samodzielnych gospodarzy

Wersja: 1.1 (lipiec 2026). Dokument zastępuje v1.0 i wszystkie wcześniejsze materiały. Jest jedynym źródłem prawdy.

## Changelog v1.0 → v1.1

1. **Licznik wyniku w dwóch wariantach** (pełny + konserwatywny) — uczciwa atrybucja od startu. Zmiany: §3.4, §6.3, §8.1.
2. **Akceptacja rekomendacji jednym kliknięciem z maila** (podpisany token) — wchodzi do MVP. Zmiany: §5.2, §8.2, Sprint 4.
3. **Write-back cen przez channel managery przesunięty przed ML** — priorytet #1 fazy 2, nie "po zdobyciu trakcji". Zmiany: §5.3, §7.2, §10.
4. **Publiczne raporty rynkowe per miasto** (content/SEO z danych Monitoringu) — dodane do Sprint 5. Zmiany: §5.2, §10.
5. **Korekta danych o konkurencji:** realny koszt PriceLabs to $25–35/listing/mies. z danymi rynkowymi; PriceLabs też oferuje 30 dni za darmo bez karty — "darmowy miesiąc" jest parytetem, nie wyróżnikiem. Zmiany: §2, §3, §4.
6. **Kolejność argumentów sprzedażowych zmieniona;** gwarancja zwrotu — rekomendacja TAK (decyzja założyciela nadal otwarta formalnie). Zmiany: §4, §12.
7. **KSeF** dodany do kwestii płatności/fakturowania. Zmiany: §12.

---

## 1. Produkt w jednym akapicie

Webowa aplikacja SaaS (B2B), która samodzielnym gospodarzom najmu krótkoterminowego i małych obiektów noclegowych w Polsce mówi, jaką cenę ustawić na każdy dzień i dlaczego — po polsku, z lokalnym kontekstem (długie weekendy, eventy, ceny i obłożenie konkurencji w okolicy). System nie przejmuje rezerwacji i nie konkuruje z OTA: klient końcowy (gość) nadal rezerwuje przez Booking/Airbnb/stronę hotelu. My jesteśmy zapleczem decyzyjnym gospodarza.

**Pozycjonowanie:** wyniki cenowe na poziomie operatora zarządzania najmem, bez oddawania 15–25% prowizji i bez kontraktu.

## 2. Klient docelowy

- Samodzielny gospodarz 1–10 obiektów (apartamenty na wynajem krótkoterminowy, małe pensjonaty, pokoje gościnne) w Polsce.
- Nieanalityczny: nie chce dashboardu z 40 metrykami, chce wiedzieć "co ustawić i dlaczego".
- Alternatywy, które realnie rozważa: (a) Excel/intuicja/darmowy Smart Pricing Airbnb — **główny konkurent to non-consumption**, (b) operator zarządzania najmem za 15–25% przychodu (Renters, Sun & Snow itd.), (c) PriceLabs — $19.99/listing/mies. bazowo, realnie $25–35 z dashboardem rynkowym (~100–140 zł), angielski, złożona konfiguracja.

**Poza zakresem:** sieci hotelowe i enterprise. Kontakt z osobą decyzyjną w Accor wykorzystujemy wyłącznie walidacyjnie (wywiad ekspercki, ewentualnie pojedynczy obiekt franczyzowy jako test w przyszłości, referencja). Żadnych funkcji pod enterprise w MVP.

## 3. Wyróżniki (ranking od najtrwalszego)

1. **Kuratorowana baza lokalnych eventów per miasto** — moduł RDZENIOWY, nie dodatek. Długie weekendy (majówka, Boże Ciało, czerwcówka), ferie zimowe per województwo, juwenalia, festiwale, mecze, targi, koncerty — przypisane do miasta i (gdzie ma sens) dzielnicy, z oceną siły wpływu. To jedyna rzecz trudna do skopiowania przez globalnych graczy: "Hyper Local Pulse" PriceLabs to sygnały popytowe z danych rezerwacyjnych, nie wiedza o polskim kalendarzu.
2. **Prostota jako produkt:** onboarding <5 minut (wklejasz link do swojego ogłoszenia → system znajduje konkurentów → proponuje cenę bazową → ustawiasz tylko cenę minimalną). Opinionated defaults zamiast 30 parametrów. Akceptacja rekomendacji jednym kliknięciem z maila, bez logowania.
3. **Wyjaśnienia po polsku, językiem gospodarza:** "Podnieś cenę 18–19.04 o 90 zł: majówka, w promieniu 2 km wolne 12% mieszkań, jesteś 15% poniżej mediany."
4. **Licznik wyniku (atrybucja) w dwóch wariantach:** pełny ("dodatkowy przychód z zaakceptowanych podwyżek") i konserwatywny — liczący tylko terminy sprzedane przy cenie ≥ mediana konkurencji, czyli takie, gdzie podwyżka nie była "gratisem" rosnącego rynku. Pokazujemy oba. Uczciwość jest częścią pozycjonowania; zawyżony licznik ktoś kiedyś wytknie publicznie.
5. **Cena i rozliczenia po polsku:** PLN, faktura VAT (KSeF — patrz §12), abonament rzędu 39–59 zł/obiekt/mies. (do walidacji w pilocie).

**NIE są wyróżnikami:** zaawansowanie ML (klient kupuje wynik i zaufanie, nie model), sam scraping OTA, język interfejsu w pojedynkę, czatbot "AI Revenue Guru" (wycięte), **30 dni za darmo bez karty** (PriceLabs oferuje to samo — to element oferty, nie przewaga).

## 4. Argumenty sprzedażowe (do landing page'a i rozmów, w tej kolejności)

1. "49 zł/mies. zamiast 20% przychodu. Operator przy 6 000 zł/mies. kosztuje 1 200 zł." — jedyne porównanie o dwa rzędy wielkości; zawsze pierwsze.
2. Gwarancja: jeśli w kwartał zaakceptowane rekomendacje (wg licznika konserwatywnego) nie zarobią więcej niż abonament — zwrot pieniędzy. Rekomendacja: TAK (ryzyko finansowe przy 49 zł/mies. groszowe, usuwa barierę zakupu, nikt na rynku tego nie daje). Formalna decyzja: §12.
3. "Wiesz DLACZEGO taka cena, po polsku. Żadnej czarnej skrzynki."
4. "Konfiguracja w 5 minut — wklejasz link do ogłoszenia." (PriceLabs też twierdzi, że jest prosty; różnicę udowadnia demo, nie hasło.)
5. "Miesiąc za darmo, bez karty." — element oferty, komunikowany, ale nie jako przewaga nad konkurencją.

## 5. Zakres

### 5.1 Dwa poziomy pokrycia miast

- **Monitoring** (od startu: wszystkie miasta wojewódzkie + główne miejscowości turystyczne): scraping cen i dostępności konkurencji, mediana rynku, obłożenie okolicy, pozycja ceny klienta. Nie wymaga kalibracji — działa wszędzie od dnia 1. Pełni też rolę lead magnetu ("zobacz swój rynek za darmo") i buduje listę oczekujących.
- **Rekomendacje** (falami): pełny pricing z eventami, wyjaśnieniami i licznikiem wyniku. **Pierwsza fala: Kraków, Trójmiasto, Poznań** (Poznań = miasto założyciela, spotkania z gospodarzami na żywo). Kolejne miasta co ~miesiąc, priorytet wg listy oczekujących z Monitoringu.

### 5.2 W zakresie MVP

- Scraper cen/dostępności konkurencji (architektura pluginowa per portal; start: Booking.com, docelowo Airbnb, nocowanie.pl)
- Import kalendarza klienta przez iCal (Airbnb/Booking udostępniają linki iCal — legalne, oficjalne, tylko odczyt)
- Baza eventów (kuratorowana ręcznie + półautomatyczne źródła) dla miast pierwszej fali
- Silnik rekomendacji v1 (regułowy — patrz §7)
- Dashboard klienta (patrz §8)
- Raport mailowy tygodniowy + alerty ad hoc, **z akceptacją/odrzuceniem rekomendacji jednym kliknięciem z maila** (podpisany, wygasający token per rekomendacja; bez logowania; patrz §8.2)
- Licznik wyniku / atrybucja — dwa warianty (§3.4)
- **Publiczne raporty rynkowe per miasto** (generowane automatycznie z danych Monitoringu: mediana cen, obłożenie, trend — wersja minimalna dla 3 miast pierwszej fali; content/SEO, karmi lead magnet; globalni gracze nie zrobią tego po polsku)
- Rejestracja, konta, multi-tenant, płatności abonamentowe (Stripe lub Przelewy24 — do decyzji przy wdrożeniu, patrz §12)

### 5.3 Poza zakresem MVP (świadomie)

- Token/blockchain/program lojalnościowy krypto — wycięte z projektu całkowicie
- Natywne aplikacje (Android/Windows/Mac) — tylko web, responsywny; ewentualna cienka aplikacja mobilna/PWA po MVP na istniejącym API
- Automatyczny zapis cen do OTA przez channel managery — **priorytet #1 fazy 2, zaraz po pilocie, PRZED modelami ML.** Uzasadnienie: dopóki klient musi ręcznie przepisywać cenę do extranetu, produkt jest doradcą, nie narzędziem — to główne przewidywane źródło churnu i główna przewaga funkcjonalna PriceLabs. One-tap accept z maila (§5.2) jest tanim mostem do tego czasu.
- Modele ML (LightGBM, elasticity) — faza 2, PO integracji z channel managerami i po zebraniu danych (patrz §7)
- Moduł compliance/regulacyjny — do rozważenia, gdy polskie regulacje najmu krótkoterminowego się skonkretyzują
- Segment hotelowy/enterprise, czatbot, funkcje "AI Guru"

**Zasada nadrzędna:** prostota jest produktem (§3.2). Każdą propozycję nowej funkcji oceniamy najpierw pod kątem: czy nie osłabia wyróżnika nr 2.

## 6. Architektura

### 6.1 Stack (celowo nudny)

- **Baza:** PostgreSQL (managed, region UE). Jedna baza. ŻADNEGO ClickHouse, Kafki, Sparka, Flinka, Feast, Kubeflow, Kubernetesa w MVP.
- **Backend:** Python + FastAPI
- **Scraping:** Playwright (headless), harmonogram: cron / APScheduler. ŻADNEGO Airflow w MVP.
- **Frontend:** Next.js (React), responsywny
- **Cache:** Redis tylko jeśli realnie potrzebny (nie zakładać z góry)
- **Hosting:** jeden dostawca chmury, region UE, początkowo 1–2 maszyny / managed services
- **Monitoring:** logi + prosty uptime/error tracking (np. Sentry); Prometheus/Grafana dopiero przy realnej skali

Ten stack bez zmian architektury obsłuży kilka tysięcy obiektów. Skalowanie = dokładanie maszyn, nie przepisywanie.

### 6.2 Zasady projektowe "global-ready" (obowiązują od pierwszej linii kodu)

1. **Multi-tenant:** każda tabela biznesowa ma `account_id`; każde zapytanie filtruje po nim. Docelowo row-level security w Postgresie.
2. **Rynek jako dane, nie kod:** tabela `markets` (geometria/obszar, waluta, strefa czasowa, język, aktywne źródła danych, poziom pokrycia: monitoring/rekomendacje). Dodanie miasta/kraju = wiersze w bazie + ewentualny adapter scrapera.
3. **Waluty:** kwoty przechowywane z kodem waluty (ISO 4217), bez założenia PLN.
4. **Czas:** wszystko w UTC w bazie; logika "cena na jutro" liczona w strefie czasowej obiektu.
5. **i18n:** wszystkie teksty UI w plikach tłumaczeń od startu (nawet jeśli istnieje tylko pl). Wyjaśnienia rekomendacji generowane z szablonów z parametrami (klucz szablonu + wartości), NIGDY jako sklejane zdania — inaczej nieprzetłumaczalne.
6. **Scraper jako pluginy:** wspólny interfejs `SourceAdapter`, osobne adaptery per portal. Nowy kraj = nowe adaptery + konfiguracja rynku.

### 6.3 Model danych — szkic głównych encji

- `accounts` (klient B2B), `users`, `properties` (obiekt klienta: lokalizacja, typ, pojemność, cena min/max, link iCal, powiązany market)
- `markets` (jw.), `competitor_listings` (obiekty konkurencji zmapowane do marketu), `price_observations` (time series: listing, data pobytu, cena, dostępność, timestamp obserwacji, źródło)
- `events` (market, dzielnica opcjonalnie, daty, kategoria, siła wpływu 0–1, źródło, status kuracji)
- `recommendations` (property, data pobytu, cena proponowana, cena poprzednia, **mediana konkurencji w momencie rekomendacji** (pod licznik konserwatywny — §3.4), uzasadnienie jako klucz szablonu + parametry, status: pending/accepted/rejected/expired, kanał decyzji: dashboard/e-mail, wynik: sprzedane/nie, delta przychodu)
- `action_tokens` (podpisane, wygasające tokeny akceptacji z maila: rekomendacja, akcja, expiry, użyty czy nie)
- `reports_sent`, `subscriptions`/billing

### 6.4 Pozyskiwanie danych — hierarchia i zasady prawne

Kolejność preferencji: (1) iCal od klientów (oficjalne, legalne), (2) dane wprowadzane przez klienta, (3) scraping publicznych cen jako uzupełnienie, (4) w przyszłości: płatne API/partnerstwa (Booking Connectivity, channel managery).

Zasady scrapingu (twarde):
- tylko dane publiczne, bez logowania; zakaz omijania CAPTCHA i zabezpieczeń
- tylko: ceny, dostępność, typ jednostki, rating liczbowy, lokalizacja ogólna, lista udogodnień; ZAKAZ: zdjęcia, opisy, treści opinii, dane osobowe
- rate limit ~1 zapytanie / 2–3 s / domenę, praca nocna, cache, respektowanie robots.txt
- przechowujemy obserwacje i agregaty analityczne, nie kopie listingów
- świadomość: regulaminy OTA zakazują scrapingu; to praktyka tolerowana w branży, nie gwarancja legalności. Produkt nie może wisieć wyłącznie na scrapingu (stąd hierarchia wyżej). Konsultacja prawna przed komercjalizacją — na liście zadań założyciela, nie deva.

## 7. Silnik rekomendacji

### 7.1 v1 (MVP): regułowy, przejrzysty

Wejście per (obiekt, data pobytu): mediana i rozkład cen konkurencji w promieniu/segmencie, obłożenie okolicy (odsetek niedostępnych), dzień tygodnia, sezon, eventy (siła wpływu), pozycja ceny klienta vs mediana, ograniczenia klienta (cena min/max).

Logika: cena bazowa klienta modyfikowana czynnikami (dzień tygodnia, sezon, event, presja obłożenia, pozycja vs mediana), z twardymi ograniczeniami min/max. Każdy czynnik zapisuje swój wkład → z tego generowane wyjaśnienie (top 3 czynniki, szablon + parametry).

Dlaczego reguły, nie ML: (a) brak danych treningowych na starcie — scraping nie daje liczby rezerwacji, a modele elastyczności z wcześniejszych dokumentów wymagały danych, których nie ma; (b) pełna wyjaśnialność; (c) szybkie strojenie per rynek w pilocie.

### 7.2 Faza 2 (po pilocie) — kolejność obowiązująca

1. **Integracja z channel managerami (write-back cen)** — patrz §5.3; przed jakimkolwiek ML.
2. Kolejne miasta w Rekomendacjach (wg listy oczekujących).
3. Prognoza presji popytu (LightGBM) na sygnałach: zmiany dostępności konkurencji w czasie (booking pace rynku), eventy, sezonowość, ewentualnie Google Trends — gdy jest ≥ kilkanaście obiektów i kilka miesięcy danych.
4. Kalibracja siły eventów na obserwowanych reakcjach cen/dostępności rynku.
5. Elasticity — dopiero gdy licznik wyniku zgromadzi wystarczająco par (rekomendacja → rezultat).

## 8. Interfejs klienta

### 8.1 Dashboard (MVP — nic ponad to)

- Kalendarz 60 dni: rekomendacja per dzień, status (do decyzji/zaakceptowana/odrzucona), przyciski akceptuj/odrzuć
- Wykres: cena klienta vs mediana rynku (60 dni)
- Obłożenie okolicy (odsetek zajętych terminów u konkurencji)
- Historia rekomendacji z wynikiem + skumulowany licznik wyniku w dwóch wariantach (§3.4): pełny i konserwatywny, z krótkim wyjaśnieniem różnicy
- Ustawienia: obiekt, cena min/max, iCal, powiadomienia

### 8.2 E-mail

- **Tygodniowy (poniedziałek rano):** najbliższe 14 dni — rekomendacje wymagające decyzji **z przyciskami akceptuj/odrzuć działającymi bezpośrednio z maila** (podpisany token per rekomendacja, wygasa z rekomendacją; potwierdzenie na lekkiej stronie bez logowania); wynik poprzedniego tygodnia; jeden najważniejszy event na horyzoncie. Długość: jeden ekran telefonu. CTA do dashboardu pozostaje dla pozostałych akcji.
- **Alert ad hoc:** tylko zdarzenia pilne (skokowa zmiana cen konkurencji, ogłoszony duży event, nagły spadek dostępności rynku). Też z przyciskiem akceptacji, jeśli alert niesie rekomendację.

## 9. Bezpieczeństwo i RODO (komplet na MVP)

- TLS wszędzie; szyfrowanie bazy at rest (managed Postgres)
- Hasła: argon2/bcrypt; sesje: krótkotrwałe tokeny; 2FA po MVP
- Tokeny akcji z maila (§8.2): podpisane (HMAC lub podpis asymetryczny), jednorazowe, z krótkim TTL, powiązane z konkretną rekomendacją i akcją; nieprzewidywalne; unieważniane po użyciu i po wygaśnięciu rekomendacji
- Izolacja tenantów na poziomie zapytań, docelowo RLS w Postgresie
- Dane osobowe ograniczone do: e-mail, nazwa/adres obiektu. NIE przechowujemy: danych gości, płatności kartowych (obsługuje operator płatności), haseł klientów do OTA (iCal = link tylko do odczytu)
- RODO: polityka prywatności, rejestr przetwarzania, umowa powierzenia dla klientów B2B, eksport i usunięcie konta na żądanie
- Hosting i backupy w regionie UE, backupy szyfrowane; dostęp do produkcji tylko po kluczu; sekrety w zmiennych środowiskowych, nigdy w repo
- SOC 2 itp. — dopiero przy klientach korporacyjnych (poza horyzontem MVP)

## 10. Plan MVP (orientacyjnie 8–10 tygodni, realizacja w Claude Code)

**Sprint 0 (fundament):** repo, CI, środowiska, schemat bazy z zasadami §6.2 (multi-tenant, markets, waluty, UTC, i18n), auth, szkielet FastAPI + Next.js.

**Sprint 1 (dane):** adapter scrapera Booking.com (zgodny z §6.4), tabele obserwacji, harmonogram nocny, mapowanie konkurentów do marketu (geo + segment), import iCal klienta.

**Sprint 2 (eventy + monitoring):** model i panel kuracji bazy eventów, zasilenie dla Krakowa/Trójmiasta/Poznania; widok Monitoringu (mediana, obłożenie okolicy, pozycja ceny) dla wszystkich miast wojewódzkich i turystycznych.

**Sprint 3 (rekomendacje):** silnik regułowy v1 + szablony wyjaśnień + ograniczenia min/max; zapis pełnego stanu rekomendacji (pod atrybucję, wraz z medianą konkurencji — §6.3).

**Sprint 4 (dashboard + e-mail):** kalendarz z akceptacją, wykresy, licznik wyniku (oba warianty); raport tygodniowy + alerty; **one-tap accept z maila (tokeny akcji — §8.2, §9)**; onboarding "wklej link" (<5 min).

**Sprint 5 (produkcja):** płatności, landing z lead magnetem "zobacz swój rynek", **publiczne raporty rynkowe dla 3 miast pierwszej fali (§5.2)**, RODO/dokumenty, monitoring błędów, hardening; pilot: 5–10 gospodarzy (Poznań — spotkania na żywo, Kraków/Trójmiasto — zdalnie).

**Po pilocie (faza 2) — kolejność z §7.2:** channel manager write-back → kolejne miasta → ML.

**Kryteria sukcesu pilota:** ≥70% rekomendacji akceptowanych po 1. miesiącu; klient loguje się/otwiera raport ≥1×/tydz.; **licznik konserwatywny > abonament** dla większości pilotów; NPS-owa rozmowa z każdym pilotem co 2 tyg.

## 11. Zasady realizacji (dla Claude Code)

- Simple beats complex. Jedna ścieżka, bez fallbacków. Fail fast przy niespełnionych warunkach.
- Zmiany chirurgiczne; najpierw dowód (reprodukcja), potem fix przyczyny, nie objawu.
- Bez nadmiarowych runtime-checków — typy (TypeScript na froncie, Pydantic/typing w Pythonie) łapią błędy.
- Każda funkcja: jedna odpowiedzialność.
- Nie dodawać komponentów infrastruktury "na zapas" — Redis, kolejki, feature store wchodzą dopiero, gdy istnieje zmierzony problem, który rozwiązują.

## 12. Kwestie otwarte (decyzje założyciela, nie blokują startu kodu)

1. Nazwa produktu i domena (nazwy z poprzednich materiałów — Aura Synergy itd. — były sprzężone z doktoratem i tokenem; do przemyślenia od zera).
2. Operator płatności: Stripe vs Przelewy24/PayU — kryterium: polska faktura VAT **+ zgodność z KSeF** (od 2026 e-fakturowanie obowiązkowe; zweryfikować z księgową zakres obowiązku dla naszych klientów i dla nas jako wystawcy). "Faktura prosto do KSeF" komunikowana jako element §3.5.
3. Gwarancja zwrotu (§4 pkt 2) — rekomendacja w specu: TAK, liczona na liczniku konserwatywnym; formalna decyzja założyciela przed landingiem.
4. Dokładna cena abonamentu (walidacja w pilocie; punkt startowy 49 zł/obiekt/mies., Monitoring taniej lub darmowy w okresie oczekiwania).
5. Konsultacja prawna: scraping + regulamin + polityka prywatności (przed publicznym startem, nie przed pilotem na zaufanych gospodarzach).
6. Konsultacja z księgową: KSeF (pkt 2).
