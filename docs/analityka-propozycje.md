# Analityka dla klienta — co realnie możemy dostarczać (2026-07-19)

Materiał do decyzji foundera. Cel: strona i panel mają być efektywne
(realna wartość) i efektowne (wizualnie), a jednocześnie UCZCIWE — to rdzeń
produktu. Poniżej twardy podział: co możemy policzyć z danych, które mamy,
co wymaga importu rezerwacji, i czego świadomie NIE udajemy.

## Standard konkurencji (rekonesans)

AirDNA (MarketMinder) i PriceLabs (Market Dashboard) pokazują: ADR (średnia
cena za sprzedaną noc), RevPAR (przychód na dostępną noc), obłożenie, lead
time, trend sezonowy, wzrost podaży, comp set, projekcję przychodu
(Rentalizer). **Kluczowe: ADR/RevPAR/obłożenie/projekcje wymagają danych o
rezerwacjach i przychodach.** Scraping ich NIE daje — konkurencja je modeluje
z estymacji obłożenia, co bywa krytykowane za niedokładność.

Wniosek strategiczny: nie udawajmy przychodów rynku. Dostarczamy to, co
możemy ZWERYFIKOWAĆ (ceny ofertowe + presja dostępności, w czasie
rzeczywistym, hiperlokalnie, po polsku, z eventami) — a prawdziwe wyniki
(ADR, RevPAR) liczymy dla obiektu gospodarza z JEGO zaimportowanych
rezerwacji. „Nie zmyślamy Twojego przychodu" to argument zaufania przeciw
modelowanym estymacjom AirDNA.

---

## A. Możemy dostarczyć TERAZ (z danych, które już zbieramy)

Rodzina „ceny ofertowe + presja dostępności". Wszystko liczone dla spójnego
scenariusza (2 os., 1 noc, desktop, PL — bez cen Genius), już egzekwowanego.

**A1. Rozkład cen konkurencji, nie tylko mediana.**
Percentyle P10/P25/P50/P75/P90 per noc — gospodarz widzi nie „mediana 500 zł",
lecz „rynek to 350–780 zł, Ty jesteś w 30. percentylu". Mamy wszystkie
obserwacje; to agregacja. Efektowne jako pasmo (wykres widełkowy) na 60 dni.

**A2. Comp set segmentowy — „obiekty jak Twój".**
Benchmark zawężony do tego samego typu jednostki i pierścienia odległości od
centrum (mamy medianę segmentową i pierścienie). To odpowiednik płatnego
comp setu PriceLabs, u nas automatyczny. „5 podobnych obiektów w promieniu
1 km: mediana 540 zł".

**A3. Trend cen w czasie.**
Codziennie gromadzimy obserwacje — po kilku tygodniach pokazujemy trend
30/60/90 dni per rynek i segment („mediana weekendowa w Zakopanem +12% m/m").
Rośnie z historią, którą już budujemy.

**A4. Tempo zapełniania rynku i lead time.**
Mamy booking pace (zmiana dostępności między przebiegami). Pokazuje, jak
szybko i jak wcześnie rynek się zapełnia na dany termin — „na majówkę rynek
zapełniony już w 60%, rok temu o tej porze 40%".

**A5. Podaż rynku.**
Liczba ofert z nagłówka wyników (mamy — np. Zakopane 581) i jej zmiana w
czasie: sygnał presji konkurencyjnej („+15% ofert m/m — więcej konkurencji").

**A6. Kalendarz popytu (heatmapa 60 dni).**
Kolor = złożona presja (event + dostępność + tempo + weekend/sezon). Jednym
rzutem oka „gdzie podnieść". Czysta wizualizacja istniejących danych.
(Także w `funkcje-konkurencyjne.md` jako 1.3.)

**A7. Spread floor–mediana.**
Sygnał floor (najtańszy dostępny, nocowanie.pl) vs mediana: jak ściśnięty
jest rynek. Wąski spread = mała elastyczność, szeroki = pole do podniesienia.

**A8. Wpływ eventów — historycznie.**
Gdy historia obejmie miniony event, pokażemy jego realny ślad na cenach/
dostępności („podczas ostatniego Open'era ceny +40%, dostępność −70%") —
dowód dla siły rekomendacji, nie założenie.

---

## B. Po imporcie rezerwacji gospodarza (decyzja 3c = TAK) — prawdziwe wyniki

Import CSV/API rezerwacji z ceną odblokowuje analitykę „jak AirDNA", ale
liczoną z PRAWDZIWYCH danych gospodarza, nie modelowaną:

**B1. Twój prawdziwy ADR, obłożenie i RevPAR** — dla obiektu gospodarza,
z jego rezerwacji. To jedyny uczciwy sposób pokazania tych metryk.
**B2. Twój wynik vs rekomendacje — realny, nie szacowany** — domyka lukę
atrybucji (recenzent pkt 3); licznik przestaje być „szacowany".
**B3. Twój przychód m/m i vs poprzedni sezon** — retencja, nawyk logowania.
**B4. Twój ADR vs mediana ofertowa rynku** — jedyne uczciwe zestawienie
Twojego zrealizowanego z ofertowym rynku.

---

## C. Czego świadomie NIE robimy (uczciwość = produkt)

- **Nie szacujemy przychodu/RevPAR/obłożenia RYNKU** z modelu — nie mamy
  rezerwacji konkurencji, a zgadywanie kłóci się z rdzeniem „wiesz dlaczego".
  Mówimy „presja dostępności" (mierzalna), nie „obłożenie rynku" (zmyślone).
- **Nie robimy projekcji przychodu obiektu** (odpowiednik Rentalizera) bez
  danych rezerwacyjnych. Po imporcie B — z danych, nie z modelu.
- Granica publiczny raport (miasto) vs płatny Monitor (Twój obiekt) — bez
  wzbogacania raportów publicznych ponad tę linię (chroni pakiet Monitor).

---

## D. Warstwa „efektowna" (wizualna) — te same dane, lepiej podane

Podnosi atrakcyjność bez nowych danych:
- pasma percentyli (A1) zamiast pojedynczej liczby,
- heatmapa popytu (A6) na landingu i w panelu,
- mapa pierścieni odległości (mamy) jako czytelna grafika miasta,
- oś czasu eventów z siłą wpływu na horyzoncie,
- mapa Polski medianą cen (mamy) — dopięcie presji dostępności, gdy dane
  wyczerpujące (po VPS/stabilnym scrapingu),
- „liczby, które robią wrażenie" na publicznych stronach SEO (podaż, spread,
  trend) — także pod pozycjonowanie.

---

## Rekomendacja

Najtańszy, najbardziej efektowny zestaw na już (z danych, które mamy):
**A1 (rozkład/percentyle) + A6 (heatmapa popytu) + A2 (comp set segmentowy)**
— trzy rzeczy, które od razu robią wrażenie i realnie pomagają, bez nowych
decyzji produktowych i bez danych, których nie mamy.

Strategicznie: **import rezerwacji (B)** to jedyna droga do metryk ADR/RevPAR
uczciwie — i jednocześnie fundament pod dowód wyniku i przyszły ML.

Pozycjonowanie na landingu: „Pokazujemy realny rynek — ceny i presję
dostępności, które sprawdzamy codziennie. Twój prawdziwy przychód liczymy
z Twoich rezerwacji, nie z modelu." To bije w słaby punkt AirDNA (szacunki).
