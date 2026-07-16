from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

_engine = None
_session_factory = None


def get_engine():
    global _engine, _session_factory
    if _engine is None:
        _engine = create_engine(get_settings().database_url)
        _session_factory = sessionmaker(bind=_engine, expire_on_commit=False)
    return _engine


def get_db() -> Iterator[Session]:
    get_engine()
    with _session_factory() as session:
        yield session
