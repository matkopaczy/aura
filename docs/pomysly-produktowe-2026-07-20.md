# Pomysły produktowe do decyzji foundera (2026-07-20)

Dwie propozycje z rozmowy + szczera ocena (Claude). Decyzje należą do foundera;
poniżej trade-offy, nie rekomendacja wiążąca.

## 1. Monitoring pokoi jednoosobowych

**Pomysł:** dodać segment pokoi 1-osobowych — „łatwo śledzić, różnorodny zakres
usługi".

**Stan techniczny:** mamy `PropertyType.ROOM` i mapowanie `unit_category`
(„pokój" → ROOM). ALE scraper pyta o 2 osoby (`group_adults=2`); pokoje
1-osobowe to osobne wyszukiwanie (`group_adults=1`).

**Trade-off:**
- (+) realne rozszerzenie oferty; sensowne dla rynków biznesowych (Warszawa,
  Katowice, Wrocław), gdzie pobyt 1-osobowy służbowy jest częsty.
- (−) **nowy wymiar skanu ≈ 2× więcej zapytań do Bookinga** (§6.4 — ryzyko
  prawne rośnie z obciążeniem). To najpoważniejszy koszt.
- (?) **dopasowanie klienta**: nasz target to samodzielni gospodarze najmu
  krótkoterminowego (głównie mieszkania). Pokoje 1-osobowe to raczej
  pensjonaty/hostele/wynajem pod biznes — być może INNY segment klienta.

**Rekomendacja warunkowa:** jeśli wchodzić, to **punktowo** dla rynków
biznesowych, nie uniwersalnie; najpierw potwierdzić, że mamy tam klientów
tego typu (pytanie do pilota). Nie na najbliższy sprint.

## 2. Heatmapa natężenia rezerwacji per obiekt (styl Uber)

**Pomysł:** mapa (Google Maps lub odpowiednik) z „czerwonymi strefami"
natężenia zainteresowania zakwaterowaniem po kodach pocztowych — wizualny
„bajer" dla właścicieli/recepcji, jak heatmapa popytu u kierowcy Ubera.

**Dlaczego dosłowna wersja jest niewykonalna UCZCIWIE (3 twarde bariery):**
1. **Nie mamy i nie wolno nam zbierać tych danych.** §6.4 pozwala przechowywać
   tylko „lokalizację ogólną" — mamy `distance_center_km` (odległość od
   centrum), NIE współrzędne ani kody pocztowe konkurencji. Precyzja
   pocztowa jest poza tym, co zbieramy i wolno zbierać.
2. **Uber pokazuje realny popyt (zamówienia).** My nie obserwujemy rezerwacji
   konkurencji — tylko dostępność (proxy) i ceny ofertowe. „Czerwona strefa =
   dużo rezerwacji" byłaby ZMYŚLONA — dokładnie modelowany-szacunek, za który
   krytykujemy AirDNA. To zabija nasz wyróżnik (uczciwość).
3. Google Maps = nowa zależność + klucz API + koszt per wyświetlenie (§11).

**Uczciwa wersja tego samego „bajeru" — z danych, które MAMY:**
- Mapa **najbliższej okolicy obiektu** (mamy `property.lat/lng` +
  `distance_center_km` konkurentów) kolorowana **presją dostępności** w
  pierścieniach wokół obiektu: im czerwieniej, tym mniej wolnych ofert
  konkurencji = wyższy popyt tu i teraz. To honest odpowiednik heatmapy Ubera —
  realne napięcie podaży, nie zmyślony popyt.
- Biblioteka: **Leaflet + OpenStreetMap** (bez klucza, bez kosztu, §11), nie
  Google Maps.
- Warstwa czasowa: suwak dnia → presja per pierścień per data (mamy
  `market_series` z occupancy per date; pierścienie już liczy `occupancy_by_ring`).

**Rekomendacja:** NIE budować wersji „popyt per kod pocztowy" (dane + uczciwość +
§6.4). Rozważyć wersję pierścieniową na Leaflecie jako „wow" wizualny —
zbudowaną na tym, co widzimy i wolno pokazać. To rozszerzenie istniejących
pierścieni odległości o warstwę mapową.

**Pole decyzji foundera:**
- [ ] Pokoje 1-osobowe: TAK punktowo (które rynki?) / NIE / później
- [ ] Heatmapa: wersja pierścieniowa Leaflet (uczciwa) / odłożyć / rezygnacja
