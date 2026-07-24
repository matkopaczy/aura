# Strategia i rynek — analiza 13 pytań (2026-07-20)

Materiał badawczo-strategiczny do decyzji foundera. Część odpowiedzi ma źródła
z researchu na żywo (linki), część to synteza ze stanu kodu/specu, część to
jawnie oznaczona opinia. Nic stąd nie jest wdrożone automatycznie — to input
do decyzji.

---

## 1. Jakie skille i pluginy (Claude Code) są tu przydatne?

Z dostępnych w tej sesji, realnie pasujące do etapu projektu:

- **`dataviz`** — do stylizacji wykresów w panelu (heatmapa popytu, wodospad
  czynników, wykresy median) — już częściowo stosowane intuicyjnie, warto
  formalnie wczytać przy kolejnych wizualizacjach.
- **`searchfit-seo` (seo-audit, keyword-clustering, content-strategy)** —
  bezpośrednio przydatne: publiczne raporty rynkowe (`/rynek/[slug]`) to
  strony SEO, a nie mają jeszcze systematycznej strategii słów kluczowych.
- **`security-review`** — do przeglądu przed komercjalizacją (uzupełnienie
  ręcznego audytu z 19.07).
- **`code-review`** — do PR-i po zakończeniu pilota, gdy zacznie się szybszy
  cykl zmian.
- **`artifact-design`** — jeśli materiały sprzedażowe/prezentacje dla pilotów
  mają powstawać jako strony (np. one-pager dla inwestora czy partnera).

Nieprzydatne na tym etapie: `aws-*` (brak infrastruktury AWS), `code-modernization:*`
(to nie legacy rewrite), `mcp-server-dev:*` (nie budujemy MCP).

**Pluginy zewnętrzne (Slack, HubSpot, Linear itd.)** — żaden nie jest
podłączony w tej sesji; jeśli chcesz śledzić leady/pilotów w CRM, to osobna
decyzja (np. Notion/Airtable na start — nie budować własnego przed potrzebą, §11).

---

## 2. W jakich krajach największe zapotrzebowanie?

**Rynek europejski rośnie**: 11,9% CAGR 2026–2033, Europa ma 21% udziału
globalnego rynku; Q1 2026 — 144,3 mln noclegów w UE, +9,7% r/r
([Grand View Research](https://www.grandviewresearch.com/industry-analysis/short-term-vacation-rental-market-report),
[StayFi](https://stayfi.com/vrm-insider/2026/04/20/vacation-rental-statistics/)).

**Najsilniejsze/najszybciej rosnące rynki STR w Europie**: Hiszpania (Madryt:
17 235 ofert, 83% obłożenie, 119 €/dobę), Portugalia (Lizbona/Porto/Algarve —
turyści + cyfrowi nomadzi), Grecja (awans na 6. miejsce w Europie), Włochy
(oficjalnie "rynek mniej dojrzały" wg Airbnb — czyli przestrzeń do wzrostu)
([Airbtics](https://airbtics.com/fastest-growing-airbnb-markets-europe/),
[Travel And Tour World](https://www.travelandtourworld.com/news/article/germany-joins-france-united-states-italy-and-more-as-greece-surpasses-records-ranking-sixth-in-europe-for-airbnb-rentals-with-explosive-growth-by-2026/)).

**Polska — najważniejsze odkrycie tego researchu**: od **20 maja 2026**
obowiązuje **CWTON** (Centralny Wykaz Turystycznych Obiektów Noclegowych) —
obowiązkowa rejestracja, numer w ogłoszeniu, kary do **50 tys. zł**, gminy
mogą wprowadzać limity dni najmu (60–90 dni/rok)
([lukaszoles.pl](https://lukaszoles.pl/najem-krotkoterminowy-rejestr-2026/),
[Strefa Biznesu](https://strefabiznesu.pl/wynajem-krotkoterminowy-w-polsce-w-swietle-regulacji-str-short-term-rental-nowe-obowiazki-i-zasady-rejestracji/ar/c3p2-29009003)).

**Wniosek strategiczny:** to jest **katalizator rynkowy, nie zagrożenie**.
Profesjonalizacja rynku (rejestr, kary, limity dni) = gospodarze muszą
maksymalizować przychód z KAŻDEJ dostępnej nocy, bo dni są teraz reglamentowane
gminami. To wzmacnia, nie osłabia, wartość dynamicznego pricingu — i to
argument sprzedażowy: "gmina ograniczyła Ci liczbę nocy, więc każda musi być
wyceniona optymalnie". Do wykorzystania w komunikacji marketingowej.

Poza Polską: ekspansja geograficzna (§7.2, "kolejne miasta") ma dziś sens
wyłącznie w Polsce — scraper, i18n (`pl.json`), eventy (MEN, lokalne kalendarze)
są głęboko spolonizowane. Wejście zagraniczne to osobny, duży projekt
(re-lokalizacja + nowe źródła eventów + inny prawny grunt scrapingu), nie
rozszerzenie.

---

## 3. Kanały sprzedaży

Z analizy segmentu i specu (§10 — pilot Poznań/Kraków/Trójmiasto, rozmowy 1:1):

1. **Bezpośrednie dotarcie do gospodarzy** — grupy FB/Discord dla hostów STR
   w Polsce (istnieją, aktywne), fora typu "Airbnb Polska hosts".
2. **Partnerstwo z PSWK** (Polskie Stowarzyszenie Wynajmu Krótkoterminowego,
   [pswk.pl](https://pswk.pl/)) — realna organizacja, członkowie zarządzają
   >10 000 obiektów, aktywna w konsultacjach regulacyjnych (m.in. Zakopane).
   To najbardziej naturalny partner na start — patrz pkt 11.
3. **Integracja/rekomendacja przez polskie channel managery** (IdoBooking,
   Hotres) — już zidentyfikowane w rekonesansie 19.07 jako droga do
   write-backu; to też kanał dystrybucji (oni polecają nas swoim klientom).
4. **SEO organiczne** — publiczne raporty rynkowe (`/rynek/[slug]`) już
   generują ruch pod frazy "ceny noclegów [miasto]"; to tani, składający się
   kanał (koszt krańcowy ~0 po zbudowaniu).
5. **Content marketing wokół CWTON/regulacji 2026** — gospodarze aktywnie
   szukają teraz informacji o nowych obowiązkach; poradnik "Co CWTON oznacza
   dla Twoich cen" to trafny lead magnet, zbieżny z landing (§4).
6. **Konferencje branżowe** — PSWK bierze udział w konsultacjach i wydarzeniach
   (Zakopane); to miejsce na obecność, nie tylko dystrybucję cyfrową.

Kanały odradzane na tym etapie: płatne reklamy (Google/FB Ads) — przedwczesne
przed potwierdzeniem konwersji z pilota; własna aplikacja mobilna jako kanał —
nie ma jej i nie powinno być teraz (§11).

---

## 4. Na co najczęściej narzekają klienci podobnych aplikacji

Z realnych recenzji (Capterra) i analiz porównawczych narzędzi (PriceLabs,
Wheelhouse, Beyond Pricing) — to jest złoto dla pozycjonowania, bo pokazuje
DOKŁADNIE gdzie konkurencja zawodzi:

1. **Opóźnienie wykrywania eventów.** "Narzędzia wykrywają eventy rynkowe
   przez agregatory trzecich stron z opóźnieniem — zanim podniosą ceny,
   okno wczesnych rezerwacji już się zamknęło"
   ([West Coast Home Stays](https://www.westcoasthomestays.com/post/dynamic-pricing-vacation-rentals-what-tools-get-wrong)).
   **To dokładnie nasza przewaga** — kuracja eventów z lokalnych, oficjalnych
   źródeł (MEN, kalendarze aren) daje wyprzedzenie, nie reakcję z opóźnieniem.
2. **Bierni użytkownicy przegrywają z aktywnymi.** Obiekty, które biją rynek,
   mają ludzi weryfikujących rekomendacje na żywo, łapiących eventy pominięte
   przez algorytm, nadpisujących nietrafione rabaty last-minute
   ([tamże](https://www.westcoasthomestays.com/post/dynamic-pricing-vacation-rentals-what-tools-get-wrong)).
   To potwierdza słuszność naszego modelu "sugestia + wyjaśnienie + Twoja
   decyzja", nie czarną skrzynkę z automatycznym zapisem bez kontroli.
3. **Interfejs z krzywą uczenia** (PriceLabs) — mimo wysokiej oceny (4,9),
   najczęstsza skarga to złożoność. Nasz prosty model 3-4 czynników +
   wyjaśnienie po polsku jest przewagą, nie brakiem funkcji.
4. **Płacisz za funkcje osobno** (PriceLabs) — user "chciałby więcej
   all-inclusive zamiast dopłat za funkcje". Nasza płaska cena pakietowa
   (29/59/119) jest prostsza.
5. **Za mało konfiguracji** (Wheelhouse, Beyond) w rynkach z małym comp setem
   — w rzadszych lokalizacjach model domyślnie zaniża rekomendacje. Nasze
   pierścienie odległości + segment-fallback (§ segment_medians) już to
   adresują.
6. **Model 1% przychodu jest drogi dla dużych obiektów** (Beyond Pricing) —
   nasza cena per-obiekt jest przewidywalna, rośnie liniowo, nie z przychodem.

---

## 5. Co jest najcenniejsze / czego klienci najbardziej potrzebują

Synteza pkt 4 + spec: **zaufanie do liczby + zrozumienie DLACZEGO + szybkość
działania bez utraty kontroli**. Konkretnie, w kolejności wagi:

1. **Wyjaśnienie decyzji** (wodospad czynników, top-3 w rekomendacji) — to
   rdzeń różnicujący, bo konkurencja tego nie ma w tej formie.
2. **Lokalny kontekst bez opóźnienia** (eventy z wyprzedzeniem, nie z lagiem).
3. **Prosta, przewidywalna cena** i brak ukrytych dopłat.
4. **Kontrola** — klik akceptuj/odrzuć, nie automat bez nadzoru (na razie —
   patrz pkt 13 o automatyzacji).
5. **Dowód, nie obietnica** — licznik wyniku z REALNEJ ceny sprzedaży (B3),
   nie modelowany szacunek jak AirDNA.

---

## 6. Panel właściciela vs recepcji — kompletna lista uprawnień

Zweryfikowane bezpośrednio w kodzie (`app/auth/deps.py`, `app/api/*.py`,
`frontend/src/components/TeamSection.tsx`).

### Właściciel (`OwnerUser` — pełny dostęp)

| Może | Endpoint/dowód |
|---|---|
| Dodawać/edytować/usuwać obiekty | `properties.py: create_property, update_property` (OwnerUser) |
| Ustawiać cenę min/max/bazową | jw. |
| Importować rezerwacje CSV | `properties.py: import_property_bookings` (OwnerUser) |
| Zarządzać zespołem (dodaj/usuń recepcję) | `account.py: create_reception, delete_reception` (OwnerUser) |
| Widzieć/zarządzać subskrypcją | `billing.py: get_subscription, cancel_subscription` (OwnerUser) |
| Eksportować/usuwać dane konta (RODO) | `account.py: export_account, delete_account` (OwnerUser) |
| Akceptować/odrzucać rekomendacje | `recommendations.py: decide` (CurrentUser — też recepcja) |
| Widzieć monitoring, wyniki, wykresy | CurrentUser — też recepcja |

### Recepcja (`CurrentUser`, rola `RECEPTION` — dostęp operacyjny)

**Może:**
- Logować się, widzieć `/dashboard` — kalendarz rekomendacji, wodospad czynników,
  monitoring rynku, kartę "Twoje prawdziwe wyniki" (ADR/RevPAR).
- **Akceptować/odrzucać** dzienne rekomendacje cenowe (`decide` — bez
  ograniczenia roli).
- Przeglądać wydarzenia rynkowe, pierścienie presji dostępności.

**NIE może** (wymuszone na backendzie, nie tylko ukryte w UI):
- Zmieniać ceny minimalnej/maksymalnej/bazowej obiektu.
- Dodawać/usuwać obiekty.
- Importować rezerwacji CSV.
- Widzieć/zmieniać rozliczenia i subskrypcję.
- Dodawać/usuwać innych członków zespołu.
- Eksportować lub usuwać dane konta.

Frontend to tylko warstwa UX (`settings/page.tsx`: `if (me?.role !== "owner")
return` — chowa formularz), ale **prawdziwa bramka jest w API** (§ "nigdy nie
ufaj samej warstwie frontowej" — zgodnie z checklistą bezpieczeństwa z 19.07).

**Ocena:** podział jest trafny biznesowo — recepcja robi to, co robi na co
dzień (reaguje na rekomendacje), nie dotyka strategii cenowej ani pieniędzy
konta. Jedna literówka w dokumentacji: CLAUDE.md mówi "recepcja nie widzi
rozliczeń" — potwierdzone w kodzie.

---

## 7. Hasło marketingowo-sprzedażowe

Obecne z landingu: *"Ceny na poziomie operatora. Bez oddawania prowizji."*
— mocne, ale generyczne (mogłoby być każdego konkurenta).

Propozycje, zakorzenione w tym, co realnie odróżnia produkt (pkt 4–5) i w
momencie regulacyjnym (pkt 2):

- **"Wiesz, ile. Wiesz, dlaczego."** — najkrótsze, wprost o wyjaśnialności
  (nasz jedyny prawdziwy dyferencjator wobec PriceLabs/Wheelhouse).
- **"Twój rynek. Twoja decyzja. Nasze dane."** — podkreśla kontrolę + dowód.
- **"Ceny, które nadążają za Twoim miastem — nie za algorytmem z Kalifornii."**
  — gra na lokalności i braku amerykańskich narzędzi z opóźnionymi eventami.
- Kontekst CWTON: **"Mniej nocy do wynajęcia? Tym bardziej policz każdą."**
  — do kampanii wiosna/lato 2026, gdy limity dni wchodzą w życie.

**Rekomendacja:** trzymać "Wiesz DLACZEGO" jako motyw przewodni we wszystkich
materiałach — to jedyne zdanie, którego konkurencja nie może po prostu
skopiować, bo u nich wyjaśnienie faktycznie jest słabsze (pkt 4).

---

## 8. Co musi być widoczne na pierwszy rzut oka (reklama + strona główna)

Test "5 sekund" — użytkownik musi wyjść z landing page wiedząc:

1. **Co to robi**: "mówimy, jaką cenę ustawić na każdą noc" (już jest, dobrze).
2. **Dla kogo**: "samodzielny gospodarz w Polsce" — dziś domyślne, ale nie
   powiedziane wprost. Dodać explicite ("Dla gospodarzy 1–10 obiektów, którzy
   sami zarządzają cenami") — odsiewa niepasujących leadów (agencje 50+
   obiektów, hotele) zanim zmarnują czas na demo.
3. **Jak to działa**: 3 kroki (wklej link → zobacz rekomendację → akceptuj
   jednym kliknięciem) — już jest w onboardingu, warto na landing.
4. **Dlaczego mi ufać**: dowód (licznik wyniku z realnych sprzedaży, nie
   model) + "pierwszy miesiąc gratis, bez karty" — usuwa ryzyko wypróbowania.
5. **Cena bez owijania** — 3 pakiety widoczne od razu, nie "skontaktuj się
   z działem sprzedaży" (to złość B2C-B2B hybrydy naszego segmentu — mały
   gospodarz nie ma czasu na rozmowy handlowe).

Rzecz do dodania, brakująca dziś: **wizualny dowód** (zrzut wodospadu
czynników albo heatmapy popytu) na landingu — dziś jest tylko tekst
argumentów. Ludzie ufają temu, co widzą, nie temu, co czytają.

---

## 9. Co jeszcze podpatrzeć u konkurencji

Z researchu (pkt 4) + wcześniejszego rekonesansu (19.07):

- **Comp set jako produkt sam w sobie** (PriceLabs Market Dashboard) —
  mamy już A2 (comp set segmentowy), ale PriceLabs sprzedaje sam dostęp do
  rynkowego dashboardu jako osobny, tańszy produkt. Nasz pakiet Monitor (29 zł)
  już to realizuje — potwierdzenie, że kierunek cenowy z 19.07 był trafny.
- **Reguły niestandardowe** (PriceLabs "surgical rule-writing") — możliwość
  ręcznego nadpisania czynnika dla konkretnej daty/eventu. To rozszerzenie
  silnika, nie coś do zrobienia teraz, ale warte zanotowania jako Faza 2.
- **Integracja z 150+ PMS** (PriceLabs) — nieosiągalne teraz, ale kierunek
  potwierdza priorytet z 19.07 (write-back przez IdoBooking jako pierwszy krok,
  nie ambicja integrować się z każdym).
- **Rentalizer / projekcja przychodu przy zakupie obiektu** (AirDNA) — to
  osobny produkt (inwestycyjny, nie operacyjny); świadomie NIE robimy tego
  bez danych rezerwacyjnych rynku (uczciwość, patrz `analityka-propozycje.md`).

---

## 10. Realne innowacje — czego nikt (PL/zagranica) nie ma

Szczera kalibracja: większość "innowacji" w tej kategorii to kombinacja
rzeczy, które są technicznie proste, ale nikt ich nie złożył w tym kształcie
— bo wymagają lokalnego kontekstu, którego globalne narzędzia nie mają.

**Realne, uczciwe, wykonalne:**

1. **Wyjaśnienie ceny jako produkt, nie dodatek** (wodospad czynników — już
   zrobiony 20.07) — konkurencja pokazuje listę czynników tekstem, nikt nie
   pokazuje multiplikatywnej dekompozycji wizualnie z uzgodnieniem do
   prawdziwej ceny. To małe, ale realne pierwszeństwo.
2. **Cena skorelowana z regulacją CWTON** — narzędzie mogłoby (po ustaleniu
   z gospodarzem limitu dni z gminy) priorytetyzować, KTÓRE dni z puli
   dozwolonych wynająć drożej, żeby zmaksymalizować przychód przy ograniczonej
   liczbie nocy. **Nikt tego nie ma, bo nikt poza Polską (i kilkoma krajami UE
   od maja 2026) nie ma tego typu limitów.** To prawdziwie unikalna cecha
   rynkowa — ale wymaga danych o limicie dni per gmina, których dziś nie
   zbieramy. Warta rozważenia jako projekt po pilocie.
3. **Sygnał floor z niezależnego źródła** (nocowanie.pl) obok głównego —
   nikt inny nie krzyżuje dwóch niezależnych źródeł cen dla jednego rynku
   (zwykle jedno źródło = jeden model). To już mamy (FloorSignal), warto to
   świadomie komunikować jako metodologiczną przewagę ("dwa źródła, nie jedno").
4. **Prawdziwy ADR/RevPAR z importu, nie modelu** (B2, zrobione) — opisane
   już w `analityka-propozycje.md`; to bije competition wprost.

**Czego NIE robić pod hasłem "innowacja"** (ryzyko zaufania i/lub §6.4):
- Heatmapa popytu per kod pocztowy z Google Maps — omówione 20.07, niewykonalne
  uczciwie.
- "AI" jako marketingowy frazes bez pokrycia — silnik jest regułowy (§7.1),
  celowo, bo to daje wyjaśnialność. Nazywanie tego "AI" byłoby nieuczciwe i
  zderzyłoby się z pkt 13 (zaufanie).

---

## 11. Z jakimi firmami warto rozpocząć współpracę

1. **PSWK (Polskie Stowarzyszenie Wynajmu Krótkoterminowego)** — najsilniejszy
   kandydat. Realna organizacja, >10 000 obiektów u członków, aktywna w
   regulacjach (naturalny sojusznik w komunikacji o CWTON). Współpraca:
   webinar/artykuł o wpływie CWTON na pricing, potencjalna zniżka dla członków.
2. **Polskie channel managery** (IdoBooking, Hotres) — już zidentyfikowane
   19.07 jako droga techniczna do write-backu; jednocześnie kanał poleceń.
   Zacząć od rozmowy handlowej, nie tylko integracji API.
3. **Blogi/influencerzy branży STR w Polsce** (np. kanały YouTube/blogi o
   "zarabianiu na Airbnb w Polsce") — tańszy i bardziej wiarygodny kanał niż
   płatne reklamy na tym etapie.
4. **Kancelarie specjalizujące się w STR** (te same, które doradzają w
   sprawie CWTON) — wymiana poleceń: my polecamy klientom kancelarię przy
   pytaniach prawnych, oni polecają nas przy pytaniach o ceny.

**Nieoczywisty, ale wart rozważenia**: dostawcy sprzątania/zarządzania kluczami
dla STR (np. platformy do koordynacji sprzątaczek) — komplementarne narzędzie,
ten sam klient, zero konkurencji.

---

## 12. Czego brakuje do "gotowego produktu" (przy pozytywnym pilocie)

Z przeglądu stanu repo + DoD + decyzji z 19–20.07:

**Blokujące komercjalizację (must-have):**
- Płatności: wdrożenie Stripe Billing + Fakturownia (zdecydowane 19.07,
  niewdrożone).
- Reset hasła (dziś brak — z audytu bezpieczeństwa 19.07, akceptowalne na
  pilocie 10 osób, NIE publicznie).
- VPS/hosting produkcyjny (wariant 5b zdecydowany, plan gotowy, niewdrożony).
- Konsultacja prawna scrapingu + regulamin B2B (odroczone do przed publicznym
  startem — teraz jest ten moment, jeśli pilot pozytywny).
- MFA dla kuratora/admina, audit log (z audytu bezpieczeństwa, przed
  komercjalizacją).

**Wzmacniające ofertę (should-have, nie blokują startu):**
- Write-back cen przez IdoBooking (domyka tarcie z §7.2, uzasadnia wyższe
  pakiety).
- Backupy z testem odtworzenia (zdecydowane, niewdrożone — wciąż wisi z 19.07).
- SPF/DKIM/DMARC dla domeny nadawczej (żeby raporty nie lądowały w spamie).

**Nie blokuje**, ale naturalne po pilocie:
- Kolejne rynki `coverage=recommendations` (dziś 29 rynków monitoring, część
  ma pełne rekomendacje — sprawdzić, czy pilot chce więcej miast).
- A3/A8 (trend cen, historyczny ślad eventów) — odblokują się same z czasem.

**Rekomendacja kolejności:** VPS → płatności → prawnik/regulamin → reset
hasła i MFA → backupy → write-back. To sekwencja "najpierw działa niezawodnie
i legalnie, potem rozliczamy pieniądze, potem wzmacniamy produkt".

---

## 13. Jak komunikować "predykcję" bez utraty zaufania

To najbardziej strategiczne pytanie z listy i zasługuje na precyzję.

**Kluczowe rozróżnienie, którego trzeba trzymać się żelazno w komunikacji:**
dzisiejszy silnik **NIE jest predykcją** — jest regułowy, deterministyczny,
w 100% wyjaśnialny (§7.1, świadoma decyzja: "pełna wyjaśnialność" jako powód
wyboru reguł nad ML). To ogromna przewaga komunikacyjna, jeśli się jej
nie zaciemni marketingowym słowem "AI" czy "predykcja".

**Jeśli/gdy w Fazie 2 (§7.2) wejdzie prognoza popytu (LightGBM)** — dopiero
wtedy pojawia się realne ryzyko zaufania z pytania. Rekomendowane podejście
komunikacyjne (oparte o to, co pokazał research pkt 4 — użytkownicy ufają
narzędziom, które dają im kontrolę i wyjaśnienie, nie czarną skrzynkę):

1. **Nigdy nie zastępuj wyjaśnienia predykcją — dodawaj ją jako JEDEN
   dodatkowy czynnik z własnym wierszem w wodospadzie**, nie ukrywaj w
   ogólnej liczbie. "Model przewiduje wzrost popytu +8% na tę datę (na
   podstawie tempa rezerwacji w regionie)" — nazwany, umiejscowiony,
   z surowym sygnałem źródłowym widocznym.
2. **Wprowadzaj stopniowo i jawnie oznaczone jako "beta"/"nowe"** — dokładnie
   jak w B2 ("liczone z realnych sprzedaży, nie z modelu") — ten sam wzorzec
   uczciwości, odwrócony: gdy faktycznie użyjemy modelu, powiedz to wprost,
   nie chowaj.
3. **Pokaż historyczną trafność, gdy będzie dostępna** (A3/A8 dają fundament:
   "w ostatnich 3 miesiącach nasze przewidywania eventów trafiały z
   dokładnością X%") — dowód, nie deklaracja.
4. **Zostaw człowieka przy sterze dłużej niż konkurencja** — automatyczny
   zapis cen (write-back) wprowadzać jako OPCJĘ do włączenia, z domyślnym
   "pokaż i czekaj na klik" nawet po dodaniu predykcji. Kontrola jest tym,
   czego zgodnie z pkt 4 najbardziej brakuje użytkownikom konkurencji.
5. **Język**: "przewidujemy" nie "wiemy"; "sygnał" nie "fakt"; unikać słowa
   "AI" (marketingowo puste, prawnie i etycznie ryzykowne przy niedotrzymanej
   obietnicy) — mówić konkretnie "model tempa rezerwacji", "wzorzec sezonowy".

**Największe ryzyko do uniknięcia**: nie wprowadzać predykcji, dopóki nie ma
się danych do jej zweryfikowania (§11 — nie zgadujemy). Recenzja z 19.07 już
to potwierdziła dla eventu "ferie" (dodane tylko tam, gdzie kierunek wpływu
jest pewny) — ta sama dyscyplina musi obowiązywać dla przyszłego ML.

---

## Podsumowanie priorytetów

Z tych 13 punktów, trzy rzeczy mają natychmiastową, tanią wartość i nie
wymagają nowych decyzji produktowych:
1. Kontakt z **PSWK** (pkt 3, 11) — jeden e-mail, potencjalnie duży zwrot.
2. **Content o CWTON** jako lead magnet (pkt 2, 3, 7) — regulacja już weszła
   w życie, gospodarze aktywnie szukają informacji teraz.
3. **Dowód wizualny na landingu** (pkt 8) — zrzut wodospadu/heatmapy, mamy
   już gotowe komponenty, tylko trzeba je pokazać na stronie głównej.

Reszta (kraje zagraniczne, innowacja z limitami CWTON, automatyzacja/predykcja)
to decyzje na po pilocie — świadomie odłożone, nie zapomniane.
