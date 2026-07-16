# Plan: odległość od miejsca wydarzenia w silniku cen

Status: **DO AKCEPTACJI** (kod dopiero po zatwierdzeniu). Rozszerza §7.1 i rdzeniowy
moduł eventów (§3 pkt 1). Zasada §6.2 pkt 5 (wyjaśnienia z szablonów) obowiązuje.

## Problem

Dziś czynnik eventu w `engine.py` patrzy tylko na to, czy event nakłada się datą,
i używa jego `impact_strength`. Nie uwzględnia, **jak daleko obiekt jest od miejsca
wydarzenia**. Mecz na stadionie winduje ceny obok stadionu, targi — obok terenu
targów, a nie równomiernie w całym mieście. To jest z natury per-miasto.

## Zmiana w danych (`events`)

Dodać dwie kolumny (nullable) — współrzędne miejsca wydarzenia:

- `venue_lat  NUMERIC(9,6) NULL`
- `venue_lng  NUMERIC(9,6) NULL`

**Nullable jest celowe.** Wydarzenia ogólnomiejskie (majówka, długi weekend, sylwester)
nie mają punktowego venue — zostają przy czystym wpływie zależnym tylko od daty
(zachowanie jak dziś). Tylko eventy „punktowe" (mecz, targi, festiwal na terenie)
dostają współrzędne. Migracja Alembic, bez backfillu (stare eventy = ogólnomiejskie).

## Zmiana w silniku (`_event_factor`)

Krzywa zaniku wpływu z odległością obiektu od venue (stałe na górze pliku, jak §7.1):

```
EVENT_VENUE_NEAR_KM = 1.5     # do tej odległości pełny wpływ eventu
EVENT_VENUE_FAR_KM  = 6.0     # od tej odległości tylko resztkowy, ogólnomiejski
EVENT_VENUE_FLOOR   = 0.30    # duży event i tak lekko podnosi cały rynek
```

Współczynnik bliskości `p(d)`:
- `d ≤ NEAR`  → `p = 1.0` (pełny wpływ)
- `NEAR < d < FAR` → liniowo `1.0 → FLOOR`
- `d ≥ FAR`  → `p = FLOOR`
- event bez venue → `p = 1.0` (ogólnomiejski, bez zmian)

Wpływ efektywny = `impact_strength × p(d)`, a mnożnik jak dziś:
`1 + EVENT_IMPACT_WEIGHT × wpływ_efektywny`.

**Wybór eventu przy nakładaniu się kilku:** dziś bierzemy najsilniejszy po
`impact_strength`. Po zmianie bierzemy najsilniejszy po **wpływie efektywnym** —
bo bliski, umiarkowany event (targi 200 m dalej) może znaczyć więcej niż silny, ale
odległy (mecz na drugim końcu miasta). Odległość liczymy istniejącym `haversine_km`
(z `onboarding.py`) — obiekt (lat/lng) → venue.

## Wyjaśnienie (§6.2 pkt 5)

Nowe parametry w `explanation_params` czynnika eventu: `venue_distance_km`.
Szablony w `pl.json` (front) i `app/i18n/pl.json` (mail) dostają wariant:
- z venue: „{name}, {km} km od miejsca wydarzenia"
- bez venue: „{name}" (jak dziś)

Klient zobaczy np. *„Targi Budma, 0,8 km od terenu targów: podnieś cenę"* — to jest
dokładnie lokalny kontekst, o który chodzi.

## Zasilenie (`seed.py`)

Dodać venue do eventów punktowych pierwszej fali (przykłady, do potwierdzenia w kuracji):
- Poznań — MTP (Międzynarodowe Targi Poznańskie) ~52.394, 16.882: PGA, Budma.
- Poznań — Malta (jezioro/teren) dla Malta Festival.
- Trójmiasto — Stadion Gdańsk ~54.395, 18.635 (mecze); Gdynia dla Open'era.
- Kraków — TAURON Arena ~50.068, 20.030 (koncerty/mecze); Stare Miasto dla Wianków/jarmarku.
Długie weekendy i święta — **bez venue** (ogólnomiejskie).

Kurator w `/admin/events` powinien móc ustawić venue — dodać pola lat/lng do formularza
i API kuracji (opcjonalne).

## Testy

- `p(d)` na progach: 0 km, NEAR, między, FAR, poza — wartości zgodne z krzywą.
- Dwa nakładające się eventy: bliski słabszy wygrywa z odległym silniejszym.
- Event bez venue = zachowanie jak dziś (regresja).
- Obiekt daleko od venue silnego eventu → tylko resztkowy wpływ (FLOOR), nie pełny.
- Wyjaśnienie zawiera `venue_distance_km` gdy venue jest.

## Czego plan NIE robi (świadomie, §11)

- Nie modeluje różnych „zasięgów" per typ eventu (stadion vs targi) osobnymi krzywymi —
  jedna krzywa, strojenie przez `impact_strength`. Różnicowanie dopiero, gdy pilot pokaże,
  że to za mało.
- Nie dodaje geokodowania nazw miejsc — venue wpisuje kurator jako współrzędne
  (jedna ścieżka, bez zależności od zewnętrznego API).
