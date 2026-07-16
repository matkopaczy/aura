# Analiza dopasowania: czy budujemy narzędzie dla właścicieli i pracowników?

Kontekst: docelowi użytkownicy wg założyciela — właściciele hoteli, pensjonatów,
mieszkań na wynajem krótkoterminowy, **pracownicy recepcji** mający problem z ceną,
oraz właściciele Airbnb bez czasu (często kilka obiektów). Docelowo: integracja z
najważniejszymi systemami rezerwacyjnymi w hotelarstwie.

Punkt odniesienia: spec §2 — cel to "samodzielny gospodarz 1–10 obiektów,
nieanalityczny", a POZA zakresem: "sieci hotelowe i enterprise".

## Werdykt per segment

| Segment | Dopasowanie | Uzasadnienie |
|---|---|---|
| Właściciel apartamentów/Airbnb, kilka obiektów, bez czasu | ✅ Pełne | To persona-cel. Zbudowane: multi-obiekt (selektor na dashboardzie), opinionated defaults, onboarding <5 min, raport tygodniowy (nie trzeba się logować), 1 klik akceptuj/odrzuć, wyjaśnienia po polsku, licznik wyniku. |
| Mały pensjonat / pokoje gościnne | ✅ Dobre | PropertyType GUESTHOUSE/ROOM; jedna cena/obiekt działa dla małego pensjonatu. Spec wprost wymienia "małe pensjonaty". |
| Pracownik recepcji | 🟡 Częściowe | Konta są multi-user (users dzielą account_id) — właściciel + recepcja mogą mieć loginy na jednym koncie JUŻ. Brakuje ROZRÓŻNIENIA RÓL. |
| Właściciel hotelu (wielopokojowego) | 🔴 Luka | Model to jedna cena/obiekt. Prawdziwy hotel ma typy pokoi po różnych cenach — tego nie wyrazimy. To też rozszerzenie §2 (hotele były poza zakresem). |

## Dwie świadome luki do decyzji

### 1. Role użytkowników (recepcja vs właściciel) — łatwe, strukturalnie gotowe

Dziś każdy user na koncie ma pełny dostęp. Dla pensjonatu/hotelu chcemy zwykle:
- **właściciel**: widzi rozliczenia + licznik wyniku, ustawia cenę min/max (guardrails);
- **recepcja**: tylko akceptuje/odrzuca dzienne rekomendacje.

Model już wspiera wielu userów na koncie — brakuje kolumny `role` + bramek w API.
Mała, dobrze odgraniczona funkcja. Rekomendacja: dodać, gdy pierwszy pilot
pensjonat/hotel tego zażąda.

### 2. Ceny per typ pokoju — realna praca, i strategiczna decyzja o "hotelach"

Model rekomendacji: jedna cena bazowa → jedna rekomendacja / obiekt / dzień.
Hotel z pokojami Standard/Superior/Suite po różnych cenach tego nie wyrazi
("podnieś Superior, zostaw Standard"). To wymaga poziomu PONIŻEJ Property
(RoomType/Unit) z ceną i rekomendacją per typ — rozszerzenie modelu danych, nie tweak.

Dodatkowo: "hotele" to rozszerzenie §2 (świadomie wycięte). Hotelarze częściej są
"analityczni" (myślą RevPAR/ADR/obłożenie) — czyli bliżej użytkownika, którego
produkt CELOWO unika. Nasza przewaga (opinionated, prosty język, dla nieanalityka)
jest najsilniejsza dla samodzielnego gospodarza, słabsza dla hotelarza chcącego pokręteł.

**Rekomendacja (§11 — najpierw zmierzony problem):** pilot trzymamy na personie-celu
(apartamenty/pensjonaty). Wielopokojowe hotele = fast-follow TYLKO jeśli popyt z pilotu
tam pociągnie. Nie budować modelu per-typ-pokoju na zapas.

## Integracja z systemami rezerwacyjnymi — kierunek zgodny

Spec §5.3 już to planuje: "Automatyczny zapis cen do OTA/channel managerów — faza 2".
MVP świadomie trzyma człowieka w pętli (rekomendacja → gospodarz sam zmienia cenę).

**Zasada projektowa:** integrować na warstwie CHANNEL MANAGERA (jedna integracja →
wiele OTA), nie per-OTA. Wychodzący "apply price" adapter jest lustrem wejściowego
SourceAdapter/FloorAdapter — architektura już to wspiera.

Kandydaci do zbadania (wymaga weryfikacji — connectivity/API, koszt, pokrycie PL):
- Hotele PL: YieldPlanet, Profitroom, SiteMinder, Cloudbeds.
- Apartamenty/Airbnb: Rentals United, Guesty, Smoobu/Hospitable.
- Bezpośrednio: Booking.com Connectivity (oficjalne API — omija kruchość scrapingu §6.4).

## Podsumowanie

Kierunek jest właściwy, a zbudowany produkt trafia w bullseye: właściciel wielu
obiektów, bez czasu, nieanalityczny. Dwie świadome decyzje przed nami: role
(łatwe) i czy wchodzić w wielopokojowe hotele (realna praca + rozszerzenie zakresu §2).
Integracja z channel managerami to faza 2 — architektura jest na nią gotowa.
