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


@lru_cache
def get_settings() -> Settings:
    return Settings()
