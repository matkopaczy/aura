from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        # Fail fast przy martwej bazie (§11): padnięty kontener za proxy portów
        # Dockera przyjmuje TCP, ale handshake Postgresa nigdy nie przychodzi —
        # bez limitu pierwsze zapytanie wisiało w nieskończoność bez błędu
        # (incydent 2026-07-18: scheduler w ciszy na SELECT z markets).
        # Realny czas do błędu: ~10 s (psycopg próbuje localhost po IPv6 i IPv4,
        # 5 s na adres). pool_pre_ping odzyskuje pulę po restarcie bazy bez
        # restartu procesu.
        _engine = create_engine(
            get_settings().database_url,
            pool_pre_ping=True,
            connect_args={"connect_timeout": 5},
        )
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_db() -> Iterator[Session]:
    get_engine()
    with _session_factory() as session:
        yield session
