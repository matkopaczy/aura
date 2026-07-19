"""Testy strażnicze zasad §6.2 — łamiesz zasadę, test czerwienieje.

Tabele danych rynkowych (wspólne dla tenantów) są jawnie wyliczone;
każda nowa tabela bez account_id musi tu zostać świadomie dopisana.
"""

from sqlalchemy import DateTime, Numeric

from app.models import Base

MARKET_DATA_TABLES = {
    "markets",
    "events",
    "competitor_listings",
    "price_observations",
    "waitlist_entries",  # leady sprzed rejestracji — dane globalne, per e-mail+rynek
    "floor_signals",  # sygnał "minimum rynku" ze źródeł bezdatowych — dane rynkowe
    "market_supply",  # migawki podaży rynku (A5) — liczba ofert, dane rynkowe
}

TENANT_TABLES = {
    "accounts",  # korzeń tenancy — sam nie ma account_id
}


def test_every_business_table_has_account_id():
    for table in Base.metadata.tables.values():
        if table.name in MARKET_DATA_TABLES or table.name in TENANT_TABLES:
            continue
        assert "account_id" in table.columns, (
            f"Tabela biznesowa '{table.name}' nie ma account_id (§6.2 pkt 1). "
            "Jeśli to dane rynkowe, dopisz ją świadomie do MARKET_DATA_TABLES."
        )


def test_all_datetimes_are_timezone_aware():
    for table in Base.metadata.tables.values():
        for column in table.columns:
            if isinstance(column.type, DateTime):
                assert column.type.timezone, (
                    f"{table.name}.{column.name} to naiwny DateTime — wymagane UTC/timestamptz "
                    "(§6.2 pkt 4)."
                )


def test_every_money_column_has_currency_code_sibling():
    money_columns = {"price", "recommended_price", "previous_price", "base_price",
                     "min_price", "max_price", "price_per_property", "revenue_delta"}
    for table in Base.metadata.tables.values():
        has_money = any(
            c.name in money_columns and isinstance(c.type, Numeric) for c in table.columns
        )
        if has_money:
            assert "currency_code" in table.columns, (
                f"Tabela '{table.name}' przechowuje kwoty bez kodu waluty (§6.2 pkt 3)."
            )
