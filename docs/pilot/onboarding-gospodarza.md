# Onboarding gospodarza (skrypt, cel: <15 min na żywo / zdalnie)

Prowadzi założyciel. Cel: gospodarz wychodzi z działającym kontem, obiektem i
pierwszymi rekomendacjami na ekranie. Onboarding produktowy ma być <5 min (§3 pkt 2) —
reszta czasu to rozmowa i budowanie zaufania.

## Zanim zadzwonisz / spotkasz się

- [ ] Rynek gospodarza ma pokrycie **rekomendacji** (Kraków / Trójmiasto / Poznań).
      Jeśli tylko monitoring — zapisz na listę oczekujących, nie onboarduj jeszcze.
- [ ] Nocny scraping zebrał już dane dla jego rynku (sprawdź: `/api/public/preview/<slug>`
      pokazuje mediany).

## Kroki z gospodarzem

1. **Rejestracja** — `/register`. Nazwa, e-mail, hasło. Triał 30 dni startuje automatycznie,
   bez karty. Podkreśl: „miesiąc za darmo, bez karty" (§4).
2. **Onboarding „wklej link"** — `/onboarding`. Gospodarz wkleja link do swojego ogłoszenia
   na Booking.com.
   - ⚠️ **Znane ograniczenie**: Booking bywa serwuje stronę-wyzwanie (anti-bot) dla stron
     obiektów. Jeśli parsowanie zwróci błąd, **wpisz dane ręcznie**: nazwa, typ, pojemność,
     cena bazowa (z jego dzisiejszej ceny), cena minimalna. To nie blokuje pilotu.
3. **Cena minimalna** — najważniejsze pole. Wyjaśnij: „poniżej tej ceny system nigdy nie
   zejdzie". Ustawcie ją wspólnie, świadomie.
4. **Link iCal (opcjonalnie)** — z panelu Booking/Airbnb gospodarza (tylko odczyt). Bez niego
   licznik wyniku nie wie, czy termin się sprzedał — zachęć do podania, ale nie blokuj.
5. **Pierwsze rekomendacje** — na `/dashboard` kliknij „Odśwież rekomendacje". Przejdźcie
   razem przez 3–4 najbliższe terminy. **Przeczytaj na głos wyjaśnienie** przy weekendzie/evencie
   („podnieś, bo majówka, jesteś X% poniżej mediany") — to moment „aha".
6. **Pokaż licznik wyniku** — wyjaśnij uczciwą atrybucję: liczymy tylko dodatkowy przychód
   z **zaakceptowanych** podwyżek, które **się sprzedały**. Nie obiecujemy cudów.
7. **Raport tygodniowy** — poinformuj: w poniedziałek rano dostanie e-mail z terminami do decyzji.

## Po onboardingu

- [ ] Zapisz w notatkach: ustawiona cena bazowa i minimalna, czy podał iCal, pierwsze wrażenia.
- [ ] Umów rozmowę NPS-ową za 2 tygodnie (skrypt w `playbook.md`).
- [ ] Dopisz gospodarza do arkusza metryk pilotu.

## Czego NIE obiecywać

- Nie mówimy „zarobisz X" — mówimy „pokazujemy, jaką cenę ustawić i dlaczego".
- Nie obiecujemy automatycznego zapisu cen do OTA — w MVP gospodarz zmienia cenę u siebie
  (faza 2). To świadoma decyzja (§5.3).
- Nie obiecujemy Airbnb/innych portali jako źródła — dziś dane z Booking.com.
