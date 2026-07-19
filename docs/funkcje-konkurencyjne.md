# Funkcje pod przewagę konkurencyjną — propozycje (2026-07-19)

Materiał do decyzji foundera. Zasada nadrzędna z recenzji: **nie wygramy
algorytmem** (PriceLabs/Beyond/Wheelhouse są rozwinięte). Wygrywamy tym,
czego oni nie mają lokalnie: polski język, lokalne eventy, wyjaśnienia
„dlaczego", sprzedaż 1:1 — oraz, docelowo, danymi wynikowymi i integracjami
z polskimi systemami. Każda funkcja niżej ma pogłębiać te przewagi, nie
gonić konkurencję cecha-w-cechę.

Filtr §11: preferuję funkcje, które **uwidaczniają dane, które już liczymy**
(eventy z odległością, presja dostępności, tempo rezerwacji, noce-sieroty,
mediany, sygnał floor) — koszt mały, ryzyko małe.

---

## Poziom 1 — tanie, unikalne, można zrobić przed/na pilocie

Wszystkie trzy używają danych, które silnik JUŻ ma. To najlepszy stosunek
wartość/koszt i realny wyróżnik w rozmowie sprzedażowej.

**1.1. Minimalna długość pobytu na gorące noce (MinLOS).**
Na noc z silnym eventem lub wysoką presją dostępności rekomendujemy nie tylko
cenę, ale i „ustaw min. 2 noce" — żeby pojedyncza droga noc nie blokowała
weekendu i nie tworzyła nocy-sieroty. Mamy już eventy z siłą wpływu, presję
i detekcję sierot. To parytet z PriceLabs, ale podany po polsku z wyjaśnieniem.
Koszt: nowy czynnik/pole w silniku + szablon. Ryzyko: małe.

**1.2. Ratunek last-minute.**
Największa realna strata gospodarza to pusta noc dziś/jutro. Dla niesprzedanych
nocy w oknie 0–7 dni (z iCal wiemy, że wolne) przy niskiej presji dajemy
agresywniejszą, wyraźnie oznaczoną rekomendację „obniż, by ratować noc".
Mamy presję + tempo + dostępność. To emocjonalnie mocne i unikalne w podaniu.
Koszt: tryb czynnika zależny od bliskości daty. Ryzyko: małe (pilnować dolnej
granicy min_price — już egzekwowana).

**1.3. Kalendarz popytu (heatmapa 60 dni) w panelu.**
Wizualna mapa „gorących" dni: kolor = złożona presja (event + dostępność +
tempo + weekend/sezon). Gospodarz jednym rzutem oka widzi, gdzie podnieść.
Liczby już mamy — to wyłącznie wizualizacja. Silny efekt „aha" na
onboardingu. Koszt: komponent front + endpoint agregujący istniejące dane.

---

## Poziom 2 — duży wpływ, wymaga decyzji lub większej pracy

**2.1. Automatyczny zapis cen (write-back) — STRATEGICZNY MOAT.**
Recenzent: to jednocześnie największe tarcie i najtrwalsza przewaga. §7.2
stawia go pierwszym po pilocie. Rekonesans (2026-07-19): IdoBooking ma API
dla systemów RMS ze sterowaniem cenami — piszemy do jednego channel managera,
on dystrybuuje na Booking/Airbnb/Expedia. Zdejmuje z gospodarza krok
„przepisz cenę ręcznie" (dziś 5 kroków tarcia) i domyka licznik wyniku
(wiemy, że cena realnie weszła). Warunek: piloci używający wspieranego CM
(stąd pytanie w onboardingu). Koszt: 2–4 tyg. + zależność od API. Kiedy:
po pilocie. To uzasadnia wyższy pakiet cenowo.

**2.2. Raport i alerty przez WhatsApp/SMS.**
Polscy gospodarze żyją na telefonie i WhatsAppie, nie w skrzynce e-mail.
Tygodniowy raport z akceptacją jednym tapnięciem + pilne alerty przez WhatsApp
mogą wielokrotnie podnieść zaangażowanie — to przewaga „lokalna", której
globalni gracze nie dopieszczają. ALE: dochodzi infrastruktura (kolejka, DLQ,
monitoring kosztów — sekcja 14 checklisty bezpieczeństwa), akceptacja Meta
Business i koszt za wiadomość. §11: budować dopiero, gdy pilot potwierdzi, że
e-mail ma słabą otwieralność. Decyzja foundera: czy testujemy na pilocie
choćby SMS-owy alert o gotowym raporcie.

**2.3. Import rezerwacji z ceną (CSV/API).**
Decyzja już zapadła (TAK, przed komercjalizacją). Domyka lukę atrybucji
(recenzent pkt 3) i zasila przyszły ML. Do czasu integracji z CM — prosty
import CSV z panelu OTA gospodarza. Koszt: mały (parser + mapowanie na
rekomendacje). Wartość: licznik wyniku przestaje być „szacowany".

---

## Poziom 3 — do rozważenia później (nie na teraz)

- **Airbnb jako drugie źródło danych** — duży udział w STR, ale scraping
  trudniejszy i bardziej wrażliwy (§6.4). Rozważyć, gdy pilot potwierdzi
  wartość, ostrożnie prawnie.
- **Sezonowe podsumowanie „Twój miesiąc vs rynek"** — e-mail retencyjny,
  buduje nawyk logowania (kryterium sukcesu §10). Tanie, gdy mamy dane.
- **Prognoza popytu (ML, LightGBM)** — §7.2, dopiero przy kilkunastu
  obiektach i kilku miesiącach danych (właśnie się gromadzą). Nie teraz.
- **Rekomendacje pakietów weekendowych / długości pobytu** — rozszerzenie 1.1.

---

## Rekomendacja

Na najbliższe tygodnie (przed i w trakcie pilotu): **Poziom 1 w całości** —
tani, unikalny, gotowy do pokazania gospodarzom, wzmacnia narrację „widzimy
lokalny rynek lepiej niż ktokolwiek". To realna odpowiedź na „5/10 za
wyróżnienie" z recenzji.

Strategicznie po pilocie: **2.1 write-back (IdoBooking)** jako moat +
**2.3 import rezerwacji** jako fundament pod dowód wyniku i ML.

Do świadomej decyzji foundera: **2.2 WhatsApp** — jedyna z listy, która
dokłada infrastrukturę; wartość realna dla rynku PL, ale nie budujemy jej
„na zapas" bez sygnału z pilotu.

Poziom 1 nie wymaga żadnych nowych decyzji produktowych (ceny, rynki,
konkurencja) — mogę zacząć od 1.3 (kalendarz popytu) albo 1.1 (MinLOS) na
Twój sygnał.
