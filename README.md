# Aura (nazwa robocza)

Webowa aplikacja SaaS (B2B): dynamiczny pricing dla samodzielnych gospodarzy najmu
krótkoterminowego w Polsce. System mówi gospodarzowi, jaką cenę ustawić na każdy
dzień i dlaczego — po polsku, z lokalnym kontekstem. Nie przejmuje rezerwacji.

Jedyne źródło prawdy o produkcie: specyfikacja v1.0 (lipiec 2026).

## Struktura

- `backend/` — Python + FastAPI, SQLAlchemy, Alembic (PostgreSQL)
- `frontend/` — Next.js (React), i18n przez next-intl
- `docker-compose.yml` — lokalny PostgreSQL 16
- `.github/workflows/ci.yml` — lint, migracje na Postgresie, testy, build frontu

## Uruchomienie lokalne

### Baza

```
docker compose up -d db
```

### Backend

```
cd backend
python -m venv .venv
.venv\Scripts\pip install -e ".[dev]"     # Linux/Mac: .venv/bin/pip
copy .env.example .env                     # i uzupełnij SECRET_KEY
.venv\Scripts\alembic upgrade head
.venv\Scripts\uvicorn app.main:app --reload
```

API: http://localhost:8000/api/health, dokumentacja: http://localhost:8000/docs

Testy: `.venv\Scripts\python -m pytest`

### Frontend

```
cd frontend
npm install
copy .env.example .env.local
npm run dev
```

## Zasady projektowe (§6.2 specyfikacji — niepodważalne)

1. **Multi-tenant**: każda tabela biznesowa ma `account_id`; każde zapytanie filtruje
   po nim (mixin `TenantMixin`, docelowo RLS w Postgresie).
2. **Rynek jako dane, nie kod**: tabela `markets`; nowe miasto/kraj = wiersze w bazie
   + ewentualny adapter scrapera.
3. **Waluty**: kwoty zawsze z kodem ISO 4217, bez założenia PLN.
4. **Czas**: w bazie wyłącznie UTC (`timestamptz`); logika dzienna w strefie obiektu.
5. **i18n**: teksty UI w `frontend/src/messages/`; wyjaśnienia rekomendacji jako
   klucz szablonu + parametry, nigdy sklejane zdania.
6. **Scraper jako pluginy**: interfejs `SourceAdapter`
   (`backend/app/scraping/base.py`), adaptery per portal.

Zasady te są egzekwowane testami strażniczymi w
`backend/tests/test_design_rules.py` — nowa tabela bez `account_id`, naiwny
`DateTime` albo kwota bez waluty wywala testy.

## Zasady realizacji (§11)

Simple beats complex. Jedna ścieżka, bez fallbacków, fail fast. Zmiany
chirurgiczne. Typy zamiast runtime-checków. Żadnej infrastruktury "na zapas"
(Redis, kolejki itd. dopiero przy zmierzonym problemie).
