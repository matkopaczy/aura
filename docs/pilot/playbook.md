# Playbook pilotu — Aura (nazwa robocza)

Cel pilotu: zweryfikować, że gospodarze **akceptują rekomendacje** i że **licznik
wyniku przewyższa abonament** — zanim zbudujemy automatyczne płatności i kolejne
źródła danych. Pilot to walidacja wartości i ceny (§10, §12 pkt 4), nie test skali.

## Kogo zapraszamy (5–10 gospodarzy)

- **Poznań (3–5)** — spotkania na żywo, miasto założyciela. Priorytet.
- **Kraków / Trójmiasto (2–5)** — zdalnie (te rynki mają pełne pokrycie rekomendacji).
- Profil: 1–10 obiektów, najem krótkoterminowy / mały pensjonat, dziś ustala ceny
  intuicją lub Excelem. Unikać gospodarzy już korzystających z PriceLabs (inny typ
  rozmowy — walidacja różnicy, nie wartości podstawowej).

## Oś czasu (8 tygodni pilotu)

| Tydzień | Co się dzieje |
|---|---|
| 0 | Onboarding każdego gospodarza (skrypt: `onboarding-gospodarza.md`). Uruchomienie triału 30 dni. |
| 1–2 | Gospodarz podejmuje decyzje w panelu; codzienna obserwacja akceptacji. Pierwsza rozmowa NPS-owa. |
| 3–4 | Pierwsze terminy „po rekomendacji" zaczynają się sprzedawać → licznik wyniku rośnie. Druga rozmowa. |
| 5–6 | Weryfikacja: czy licznik > abonament. Trzecia rozmowa. Zbieranie próśb o funkcje. |
| 7–8 | Decyzja o cenie (§12 pkt 4), rozmowa o przejściu na płatny abonament (ManualProvider → faktura VAT). |

## Kryteria sukcesu (z §10)

- **≥70% rekomendacji akceptowanych** po 1. miesiącu (mierzalne: `status=accepted` / wszystkie).
- Gospodarz **loguje się / otwiera raport ≥1×/tydz.** (mierzalne: `reports_sent` + logi logowań).
- **Licznik wyniku > abonament** dla większości pilotów (endpoint `/api/recommendations/attribution`).
- Rozmowa NPS-owa z każdym pilotem **co 2 tygodnie** (skrypt niżej).

## Metryki do śledzenia (zapytania na produkcyjnej bazie)

```sql
-- Wskaźnik akceptacji per obiekt (ostatnie 30 dni)
SELECT p.name,
       count(*) FILTER (WHERE r.status = 'ACCEPTED')::float
         / NULLIF(count(*) FILTER (WHERE r.status IN ('ACCEPTED','REJECTED')), 0) AS akceptacja
FROM recommendations r JOIN properties p ON p.id = r.property_id
WHERE r.created_at > now() - interval '30 days'
GROUP BY p.name;

-- Dodatkowy przychód ze sprzedanych, zaakceptowanych podwyżek per konto
SELECT account_id, sum(revenue_delta) FILTER (WHERE outcome_sold AND revenue_delta > 0) AS dodatkowy_przychod
FROM recommendations WHERE status = 'ACCEPTED' GROUP BY account_id;

-- Aktywność: kiedy ostatnio wysłano raport
SELECT account_id, max(sent_at) FROM reports_sent GROUP BY account_id;
```

## Skrypt rozmowy NPS-owej (co 2 tyg., 15 min)

1. Czy w tym tygodniu zmieniłeś którąś cenę na podstawie naszej rekomendacji? Dlaczego tak/nie?
2. Która rekomendacja była dla Ciebie **oczywiście trafna**? Która **budziła wątpliwość**?
3. Czy wyjaśnienie („dlaczego taka cena") było zrozumiałe? Czego zabrakło?
4. Gdybyś miał dziś zapłacić 49 zł/mies. za ten obiekt — zapłaciłbyś? Ile byłoby uczciwie?
5. Czego najbardziej brakuje, żeby to było „must-have"?
6. (0–10) Jak prawdopodobne, że polecisz to innemu gospodarzowi?

Odpowiedzi zapisujemy per gospodarz — to jest realny materiał do decyzji o cenie i roadmapie.

## Po pilocie — bramka do dalszych inwestycji

Automatyczne płatności (Stripe/P24), kolejne źródła scrapingu i modele ML (§7.2)
budujemy **dopiero gdy pilot potwierdzi wartość** — zgodnie z §11 (bez infry na zapas).
Dane z licznika wyniku (pary rekomendacja→rezultat) są paliwem do modeli v2.
