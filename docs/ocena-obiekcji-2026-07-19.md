# Ocena obiekcji zewnętrznej recenzji (2026-07-19)

Recenzja od praktyka przekazana przez założyciela. Poniżej ocena każdego
zarzutu wobec faktycznego stanu repo (nie specu z pamięci) + co z tego
proponuję wdrożyć. Decyzje produktowe — pola na końcu.

## Zarzuty ODRZUCONE z dowodem w kodzie

**4b. „Link z maila nie może zmieniać stanu przez GET"** — już tak jest:
`api/actions.py` GET zwraca wyłącznie stronę potwierdzenia (docstring:
„bez mutacji, odporna na prefetch skanerów poczty"), mutacja wyłącznie
po jawnym POST z przycisku. Zarzut trafny co do zasady, nietrafny co do nas.

**2b. „Liczone dla różnych scenariuszy"** — scraper od początku odpytuje
identyczny scenariusz: 2 dorosłych, 0 dzieci, 1 pokój, 1 noc, desktop,
locale pl-PL, bez logowania (= bez cen Genius), ceny całkowite z karty
wyników. Metodologia jest spójna; słabość dotyczy tylko NAZWY (patrz 2a).

**9. „KSeF i płatności to dwa oddzielne problemy"** — dokładnie tak zaprojektowano
rekomendację w `decyzje-przedstartowe.md`: Stripe = pobieranie płatności,
Fakturownia = faktury + KSeF. Zbieżność z recenzentem, nie korekta.

**6. „Zakres nie mieści się w 8–10 tygodni"** — empirycznie nieaktualne:
funkcje sprintów 0–5 są zbudowane (historia gita 16–18.07). Trafne jądro
zarzutu: *stabilność i wiarygodność danych* to osobna praca — i ona właśnie
trwa (fail-fast bazy, autostart, alert jakości danych po nocnym przebiegu).

## Zarzuty TRAFNE — tanie korekty uczciwości (do OK założyciela)

**2a. „Obłożenie" to za mocne słowo.** Racja: brak w wynikach ≠ rezerwacja
(min. pobyt, zamknięty przyjazd, blokada właściciela, inny kanał). Nasza
heurystyka „nieobecny przy skanie wyczerpującym = niedostępny" mierzy
*presję dostępności*, nie obłożenie. Propozycja: w całym UI i raportach
przemianować na **„presja dostępności rynku"** (klucze w `pl.json`,
bez zmian w silniku — czynnik i tak nazywa się occupancy_pressure).

**3. Licznik wyniku — częściowo trafne, najważniejszy punkt recenzji.**
Stan faktyczny (lepszy niż recenzent zakłada): liczymy TYLKO rekomendacje
zaakceptowane, których termin realnie SPRZEDAŁ SIĘ wg iCal; delta tylko
dodatnia; wariant konserwatywny dodatkowo tnie do cen ≥ mediana konkurencji;
UI już mówi „dodatkowy przychód z zaakceptowanych podwyżek", nie „zarobiliśmy
Ci X". Luka realna: nie wiemy, czy gospodarz FAKTYCZNIE przepisał cenę do
Bookingu. Propozycje:
  a) etykieta „**szacowany** dodatkowy przychód…" + zdanie o założeniu
     („przy założeniu, że zaakceptowana cena została ustawiona") — 15 minut;
  b) na pilocie weryfikacja ręczna w rozmowach co 2 tyg. (już w playbooku);
  c) **import CSV rezerwacji z ceną** jako funkcja przed komercjalizacją —
     domyka lukę i zasila przyszły ML (§7.2) — decyzja niżej.
Konsekwencja dla gwarancji zwrotu: do czasu (c) gwarancja opiera się na
liczniku z założeniem (a) — świadomie zaakceptować albo przesunąć gwarancję
do momentu wdrożenia importu.

**8. Porównanie z operatorem.** Landing (`sell1`) mówi „49 zł/mies. zamiast
20% przychodu" — recenzent słusznie: operator robi więcej niż pricing.
Propozycja kopii: „Profesjonalne wsparcie cenowe za ułamek prowizji
operatora — bez oddawania obsługi obiektu". Jedna linia w `pl.json`.

## Zarzuty TRAFNE — strategiczne (decyzje założyciela)

**1. Scraping = ryzyko egzystencjalne.** Zgoda; pokrywa się z naszą analizą
ryzyk (alert jakości, dywersyfikacja źródeł, warianty 5a/5b, prawnik).
Nowe z recenzji: sprawdzić z prawnikiem także ścieżkę **Demand API /
Managed Affiliate Partner** Bookingu — dołączone do briefu kancelarii.

**4a + 5. Write-back do channel managera = jednocześnie największe tarcie
i najtrwalszy moat.** Spec §7.2 już stawia go PIERWSZY po pilocie; recenzent
przesunąłby go DO pilota. Argument za: domyka licznik (3c), zdejmuje tarcie,
uzasadnia cenę 89–129 zł (7). Argument przeciw: §11 — pilot ma zweryfikować,
czy rekomendacje w ogóle są trafne, zanim zbudujemy integrację; 2–4 tyg.
pracy + zależność od zewnętrznego API. Rozsądny środek: **pilot bez
write-backu, ale rekonesans API polskich channel managerów (IdoBooking,
Hotres, YieldPlanet…) już teraz**, żeby decyzja po pilocie była natychmiast
wykonalna.

**7. Cena.** Dodano wariant do materiału decyzyjnego: testować 49 zł
(doradztwo) vs 89–129 zł (z write-backiem, gdy będzie). Zbieżne z pkt 4a.

**Zmiany zakresu MVP proponowane przez recenzenta** (tylko Poznań, jeden typ
obiektu, 30 dni, bez raportów publicznych/płatności/gwarancji w pilocie):
częściowo już tak jest (pilot startuje w Poznaniu wg playbooka; e-mail
skupia się na 14 dniach), częściowo sprzeczne z podjętymi decyzjami
założyciela (29 rynków, raporty SEO jako lejek — koszt utrzymania ~0 po
zbudowaniu). Nie ma potrzeby wyłączać istniejących funkcji; jest potrzeba
NIE budować nowych szerokości przed pilotem.

**5b. Eventy jako moat.** Zgoda z recenzentem: to przewaga jakościowa,
nie strukturalna. Strukturalna = dane wynikowe (rekomendacja → cena →
rezerwacja) + integracje PL. Wniosek spójny z 3c i 4a.

## Pola decyzji (rozstrzygnięte 2026-07-19)

- [x] 2a: przemianowanie „obłożenie" → „presja dostępności rynku" — WDROŻONE
      (etykiety metryk = „presja dostępności"; wyjaśnienia rekomendacji
      i maile = prosty język: „wolnych ofert w okolicy ubywa")
- [x] 3a: etykieta „szacowany" + zdanie o założeniu — WDROŻONE (dashboard + mail)
- [x] 3c: import CSV rezerwacji — TAK, przed komercjalizacją (backlog)
- [x] 8: nowa kopia landing „sell1" — WDROŻONE
- [x] 4a: rekonesans API polskich channel managerów — TAK (wyniki niżej)
- [x] 7: wariant 89–129 przy write-backu — NIE (obowiązuje siatka 29/59/119)
- [x] 1: Demand API w briefie prawnym — TAK (dopisane do decyzje-przedstartowe §4)

## Rekonesans API channel managerów (4a) — 2026-07-19

Cel: sprawdzić, czy write-back cen (§7.2, najtrwalszy moat wg recenzenta) ma
gotową drogę techniczną w polskim ekosystemie, zanim po pilocie zdecydujemy
o budowie. To rekonesans, nie zobowiązanie.

**Kluczowe ustalenie — IdoBooking:** wprost otworzył API dla systemów
Revenue Management — „pełna kontrola nad restrykcjami pobytu, dostępnością
sprzedaży oraz elastyczne zarządzanie CENAMI we własnych integracjach"
(changelog IdoBooking). To dokładnie interfejs, którego potrzebuje write-back
Aury: ustawiamy rekomendowaną cenę, ich channel manager rozsyła ją na
Booking/Airbnb/Expedia. Dodatkowo ich CM wystawia podgląd cen z OTA —
potencjalnie alternatywne źródło danych o cenach (do zbadania: czy tylko
własne oferty klienta, czy też konkurencja).

**Krajobraz** (do pogłębienia przed samą budową): główni gracze PL to
IdoBooking, Hotres, YieldPlanet, Profitroom, Roomadmin. YieldPlanet
historycznie ma program partnerski dla RMS (do potwierdzenia u nich).
Hotres — CM głównie przez panel; API do zweryfikowania bezpośrednio.

**Wniosek dla strategii:** istnieje co najmniej jedna realna droga (IdoBooking)
do write-backu bez budowania własnych integracji z każdym OTA osobno — piszemy
do jednego CM, on robi dystrybucję. To obniża koszt moatu z „integracja z
każdym portalem" do „integracja z 1-2 polskimi CM". Rekomendacja: po pilocie
zacząć od IdoBooking (API dla RMS potwierdzone), pod warunkiem że wśród
pilotów są jego użytkownicy — inaczej najpierw zmierzyć, z jakiego CM
korzystają realni gospodarze (pytanie do onboarding-gospodarza w playbooku).

Źródła: [changelog API IdoBooking (RMS/ceny)](https://www.idobooking.com/changelog/nowe-mozliwosci-api-idobooking-automatyzuj-zarzadzanie-warunkami-pobytu-sterujac-restrykcjami-dostepnoscia-sprzedazy-i-cenami-we-wlasnych-integracjach/),
[Channel Manager IdoBooking](https://www.idobooking.com/en/features/channel-manager/),
[Hotres CM](https://hotres.pl/channel-manager).
