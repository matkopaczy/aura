# Decyzje przedstartowe (§12 specu) — materiał decyzyjny

Stan na 2026-07-19. Research + rekomendacje przygotowane przez Claude; każda
sekcja kończy się polem **DECYZJA założyciela**, które pozostaje do wypełnienia.
Nic z tego dokumentu nie jest wdrożone bez decyzji.

---

## 1. Operator płatności + KSeF (§12 pkt 2)

### Stan prawny KSeF (zweryfikowany 2026-07-19)

- Od **1.02.2026** KSeF obowiązkowy dla firm >200 mln zł obrotu; od tej daty
  **wszyscy podatnicy muszą umieć ODBIERAĆ faktury w KSeF** — nasi klienci
  (gospodarze z działalnością) już dostają faktury tym kanałem.
- Od **1.04.2026** wystawianie faktur B2B w KSeF obowiązkowe dla ogółu firm.
- Wyjątek: mikrofirmy o sprzedaży B2B ≤ **10 tys. zł brutto/mies.** mają czas
  do **1.01.2027** — ale jednorazowe przekroczenie limitu w miesiącu oznacza
  natychmiastowe i trwałe wejście w obowiązek.

Wniosek dla Aury: na skali pilota (5–10 × 49 zł) mieścimy się w wyjątku, ale
próg 10 tys. zł to ~200 abonentów — przy komercjalizacji przekroczymy go
szybko, więc fakturowanie musi być KSeF-ready od pierwszego płatnego klienta.
Komunikat "faktura prosto do KSeF" (§3.5 specu) przestał być wyróżnikiem —
od kwietnia to standard rynkowy; wyróżnikiem jest co najwyżej "zero papierologii
u Ciebie".

### Opcje

| | A. Stripe Billing + Fakturownia | B. PayU/Przelewy24 + własna logika |
|---|---|---|
| Subskrypcje cykliczne | wbudowane (Stripe Billing) | do zbudowania samodzielnie |
| BLIK | jednorazowy tak; **BLIK Recurring od 2026 przez Stripe** (wdrożenie OpenAI), dostępność dla małych merchantów do potwierdzenia | BLIK Recurring natywnie (PayU) |
| Faktura + KSeF | Fakturownia: natywna integracja ze Stripe (webhook), faktura przy każdej płatności, wysyłka do KSeF wbudowana (token z e-US) | osobna integracja fakturowania do zbudowania |
| Złożoność (§11) | najmniej ruchomych części: zero własnego kodu billingowego | własny scheduler ponowień, obsługa nieudanych płatności, dunning |
| Prowizje | ~1,5% + 1 zł (karty EU); wypłaty PLN | ~1–1,5% (negocjowalne przy wolumenie) |
| Polska faktura VAT | tak — Fakturownia wystawia, my jesteśmy wystawcą | tak, analogicznie przez system księgowy |

### Rekomendacja

**Opcja A: Stripe Billing + Fakturownia.** Zgodna z §11 (jedna ścieżka, zero
własnej infrastruktury billingowej), KSeF od pierwszego dnia, konfiguracja
w godziny zamiast tygodni. Ryzyko BLIK-a mitygowane: na pilocie karta
wystarcza (B2B), a BLIK Recurring w Stripe właśnie wchodzi na rynek — do
weryfikacji u supportu Stripe przed komercjalizacją. Do potwierdzenia
z księgową: kto formalnie wystawia (my przez Fakturownię) i mapowanie
webhooków przy zwrotach.

Źródła: [harmonogram KSeF](https://amavat.pl/terminy-i-obowiazki-zwiazane-z-ksef-aktualny-harmonogram-zmian/),
[limit 10 tys. zł](https://we-tax.pl/ksef-2026-w-praktyce-obowiazki-luty-kwiecien-zwolnienia-scenariusze/),
[BLIK Recurring w Stripe](https://www.cashless.pl/19300-blik-stripe-openai-chatgpt),
[Stripe vs PayU](https://kcmobile.pl/baza-wiedzy/porownania/stripe-vs-payu-w-2026-aktualne-porownanie/),
[integracja Stripe→Fakturownia→KSeF](https://sprytnafirma.pl/podatki-i-ksiegowosc/stripe-faktura-ksef-2026-jak-wystawic),
[API KSeF Fakturowni](https://github.com/fakturownia/API/blob/master/KSeF.md).

**DECYZJA założyciela (2026-07-19): Opcja A — Stripe Billing + Fakturownia.**
Do potwierdzenia z księgową przed pierwszą fakturą: formalny wystawca
i mapowanie zwrotów.

---

## 2. Gwarancja zwrotu (§12 pkt 3, §4 pkt 2)

Spec rekomenduje: TAK, liczona na **liczniku konserwatywnym** (wynik liczony
wyłącznie z rekomendacji ≥ mediany konkurencji — czyli zaniżony na naszą
niekorzyść, nie do podważenia przez klienta).

### Propozycja warunków (do akceptacji lub korekty)

> Jeśli po 3 pełnych miesiącach licznik konserwatywny nie pokaże korzyści
> większej niż suma zapłaconych abonamentów — zwracamy różnicę do wysokości
> abonamentu. Warunek: zaakceptowane ≥ 60% rekomendacji (gwarancja dotyczy
> stosowania produktu, nie samego posiadania konta).

Uzasadnienie progów: 3 miesiące = minimum na sezonowość i atrybucję (licznik
potrzebuje zamkniętych pobytów); 60% akceptacji = kryterium sukcesu pilota
z §10 to 70%, więc próg gwarancji celowo łagodniejszy. Ryzyko finansowe
w pilocie: maks. 10 klientów × 147 zł = 1 470 zł — koszt marketingowo
znikomy wobec siły argumentu "nie ryzykujesz nic".

**DECYZJA założyciela (2026-07-19): NIE.** Konsekwencje: landing i materiały
sprzedażowe nie obiecują zwrotu; argumentem ryzyka pozostaje darmowy pierwszy
miesiąc bez karty. Wątpliwość recenzenta o weryfikowalność licznika przestaje
być blokująca dla oferty.

---

## 3. Cena abonamentu (§12 pkt 4)

Punkt startowy ze specu: **49 zł/obiekt/mies.**, Monitoring taniej lub darmowy.

### DECYZJA założyciela (2026-07-19): trzy pakiety o zróżnicowanej cenie;
**bez pakietu darmowego** — za darmo wyłącznie pierwszy miesiąc.

### Propozycja: siatka trzypakietowa (wersja 2, wszystkie płatne)

Logika: drabinka 29/59/119. Monitor = tani bilet wstępu i monetyzacja rynków
oczekujących; Rekomendacje = produkt dla 90% klientów, zakotwiczony pod
PriceLabs (~80 zł + ~40 zł dashboard, po angielsku); Pro = segment 3–10
obiektów i recepcje, płaci za usługę i czas, nie za algorytm. Rolę lejca po
darmowym pakiecie przejmuje pierwszy miesiąc 0 zł bez karty (w każdym
pakiecie, mechanizm triala już w produkcie) + publiczne raporty SEO.
Kotwica: jedna odzyskana noc (250–500 zł) płaci za 4–8 miesięcy.

| | **MONITOR** | **REKOMENDACJE** ⭐ | **PRO** |
|---|---|---|---|
| Cena | **29 zł**/obiekt/mies. (290 zł/rok) | **59 zł**/obiekt/mies. (590 zł/rok) | **119 zł**/obiekt/mies. (1190 zł/rok) |
| Dla kogo | zaczynający; rynki w poziomie monitoring | samodzielny gospodarz 1–5 obiektów | gospodarze 3–10 obiektów, obiekty z recepcją |
| Zawartość | pozycja Twojej ceny vs mediana (codziennie), presja dostępności, kalendarz eventów z siłą wpływu, raport tygodniowy, alerty o skokach cen | wszystko z MONITORA + rekomendacja ceny na każdą noc (60 dni) z wyjaśnieniem po polsku, akceptacja 1 kliknięciem z maila, licznik wyniku, iCal | wszystko z REKOMENDACJI + konta zespołowe (właściciel/recepcja), wsparcie <24 h rob., kwartalny przegląd cen 1:1, lokalny event na życzenie w 48 h, auto-zapis cen w cenie gdy zadebiutuje |
| Start | 1. miesiąc 0 zł, bez karty | 1. miesiąc 0 zł, bez karty | 1. miesiąc 0 zł, bez karty |
| Rabat | od 5. obiektu −30% | od 5. obiektu −30% | od 5. obiektu −30% |

Uzasadnienia liczb: 59 = pod PriceLabs, nad nieopłacalnym 49 (krytyka
recenzenta), roczne 590 daje psychologiczne „~49/mies."; 119 = koszyk
usługowy z rzeczy istniejących (role, kuracja eventów) + founder-time;
29 = impulsowy próg wejścia, musi być wyraźnie bogatszy od darmowych
publicznych raportów (personalizacja: TWÓJ obiekt na tle rynku, alerty).
Napięcie do pilnowania: granica publiczny raport (miasto, bez
personalizacji) vs Monitor (obiekt) — nie wzbogacać raportów publicznych
ponad tę granicę. Spec §5.1 („Monitoring taniej lub darmowy w okresie
oczekiwania") jest spełniony wariantem „taniej". Piloci poza cennikiem:
Rekomendacje 0 zł na 3 mies. w zamian za rozmowy co 2 tyg. (§10).

Do wdrożenia po akceptacji: `default_price_per_property` 49 → 59, struktura
pakietów w billingu, cennik na landingu.

**AKCEPTACJA siatki 29/59/119 przez założyciela:** ………

---

## 4. Konsultacja prawna (§12 pkt 5) — briefing dla kancelarii

Zakres do wyceny u prawnika (przed publicznym startem; pilot na zaufanych
gospodarzach może biec równolegle — tak stanowi spec):

1. **Scraping (§6.4)** — ocena naszych praktyk: tylko publiczne wyniki
   wyszukiwania; respektujemy robots.txt (jedyny parser, UA z kontaktem);
   zero obchodzenia anty-botów (challenge = odstępujemy); odstępy 2,5 s,
   praca nocna; przechowujemy wyłącznie ceny/dostępność/typ/rating/lokalizację
   ogólną (bez zdjęć, opisów, opinii); pytania: baza danych sui generis
   (dyrektywa 96/9/WE), nieuczciwa konkurencja, naruszenie ToS Booking jako
   ryzyko kontraktowe vs deliktowe.
2. **Regulamin B2B** — ograniczenie odpowiedzialności (rekomendacje cenowe
   to sugestie, decyzja i skutek po stronie gospodarza!), SLA "best effort",
   gwarancja zwrotu z pkt 2 jako załącznik.
3. **RODO** — mamy: politykę prywatności, rejestr przetwarzania, umowę
   powierzenia (commit 682d010); do przeglądu prawnika + DPIA-light dla
   scrapingu (dane obiektów, nie osób — do potwierdzenia).
4. **Publiczne raporty rynkowe (§5.2)** — publikacja median/obłożenia
   per miasto: czy agregaty z danych konkurencji są bezpieczne publicznie.

Szacunek rynkowy: 3–6 tys. zł za pakiet (kancelaria butikowa e-commerce/IT).

**DECYZJA założyciela (2026-07-19): odroczone** — wracamy przed publicznym
startem; pilot na zaufanych gospodarzach biegnie bez konsultacji (zgodnie
ze specem).

---

## 5. Hosting produkcyjny (poza §12, ale blokuje niezawodność)

Dziś całość działa na laptopie developerskim: uśpiona/wyłączona maszyna
o 03:00 = noc bez danych (patrz autostart AuraDev — łata, nie rozwiązanie).
Spec §9 i tak wymaga hostingu UE na produkcję.

Propozycja na pilota: **1 VPS w UE** (Hetzner Falkenstein / OVH PL,
4 vCPU / 8 GB — Playwright potrzebuje zapasu RAM), ~30–40 zł/mies.
Docker Compose: Postgres + backend + scheduler + front; backupy bazy
codzienne, szyfrowane (§9). Bez Kubernetesa, bez managed-czegokolwiek (§11).
Migracja: seed + `pg_dump` z dev; pół dnia pracy z weryfikacją.

**Niuans scrapingowy (2026-07-19, z analizy ryzyk)**: adresy IP centrów
danych są przez portale flagowane częściej niż łącza domowe — przeniesienie
scrapera na VPS może zwiększyć ryzyko blokady IP (rotacja proxy wykluczona,
§6.4). Dwa warianty do wyboru:

- **5a. Wszystko na VPS** — najprościej (jedna maszyna, §11); ryzyko blokady
  akceptujemy i monitorujemy (alert jakości danych); w razie blokady scraper
  wraca na łącze rezydencjalne (wariant 5b) w jeden wieczór.
- **5b. Hybryda** — VPS: baza + API + front + eventy; scraper cen zostaje na
  maszynie z łączem domowym i pisze do bazy na VPS. Mniejsze ryzyko blokady,
  ale scraping dalej zależy od włączonego laptopa (słabość tylko częściowo
  zdjęta) i dochodzi tunel/VPN do bazy.

Rekomendacja: zacząć od **5a** (prostota, pełna niezawodność nocy) z jasnym
planem odwrotu do 5b przy pierwszych oznakach blokady — przejście jest tanie
w obie strony, a alert jakości danych wykryje problem pierwszej nocy.

**DECYZJA założyciela (2026-07-19): wariant 5b — hybryda.** VPS: baza + API +
front + joby nie-scrapingowe (iCal, atrybucja, raporty, kontrola jakości,
eventy); scraper cen zostaje na maszynie z łączem domowym i pisze do bazy na
VPS (tunel WireGuard albo SSH). Incydenty z 17–19.07 (Docker, MSIX, antywirus)
potwierdzają pilność. Dostawca i termin — do domówienia przy planie wdrożenia.

Szkic podziału schedulera (do zaprojektowania przed wdrożeniem): dwa procesy
z rozłącznymi zestawami jobów — „scheduler-scraper" (laptop: scraping 03:00 +
floor) i „scheduler-core" (VPS: cała reszta); wspólna baza na VPS; kontrola
jakości danych działa na VPS i pilnuje laptopa niejako z zewnątrz (spadek
wolumenu = alert, także gdy laptop po prostu nie wstał).

---

## Kolejność sugerowana

1. VPS (pkt 5) — odblokowuje niezawodny nocny scraping niezależnie od laptopa.
2. Stripe + Fakturownia sandbox (pkt 1) — bez ryzyka, faktury testowe w DEMO KSeF.
3. Gwarancja + cena (pkt 2–3) — potrzebne dopiero na landing przy komercjalizacji.
4. Prawnik (pkt 4) — równolegle, niezależny tor; pilot nie czeka.
