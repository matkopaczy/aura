from decimal import Decimal
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Konfiguracja aplikacji z zmiennych środowiskowych.

    Brak wartości domyślnych dla sekretów i bazy — aplikacja nie wystartuje
    bez kompletnej konfiguracji (fail fast, §11).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    database_url: str
    secret_key: str
    access_token_minutes: int = 30
    cors_origins: list[str] = ["http://localhost:3000"]
    dashboard_url: str = "http://localhost:3000"
    # E-mail (§8.2). Brak smtp_host = wysyłka niemożliwa; joby mailowe padają głośno.
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_user: str | None = None
    smtp_password: str | None = None
    email_from: str = "Aura <no-reply@localhost>"
    # Abonament (§5, §12 pkt 4): 30 dni triału bez karty, cena do walidacji w pilocie.
    trial_days: int = 30
    default_price_per_property: Decimal = Decimal("49")
    billing_currency: str = "PLN"
    # Monitoring błędów (§6.1): brak DSN = Sentry wyłączony, bez infry na zapas (§11).
    sentry_dsn: str | None = None


@lru_cache
def get_settings() -> Settings:
    return Settings()
