"""Backup bazy z testem odtworzenia (§9): "backup bez testu odtworzenia to nie
backup" — pg_dump sam w sobie niczego nie dowodzi.

pg_dump/pg_restore przez `docker exec aura-db-1` — Postgres (dev i na razie
produkcja) żyje w kontenerze, backend jest procesem natywnym obok niego, więc
to najprostsza ścieżka bez montowania socketu Dockera do żadnego kontenera
(§11 — bez infrastruktury "na zapas", i bez rozszerzania powierzchni ataku).
Przy przejściu na VPS (docker-compose) do przemyślenia: albo ten sam wzorzec
(backend ma dostęp do docker CLI hosta), albo pg_dump w obrazie backendu +
połączenie TCP do bazy — patrz `wdrozenie-vps-5b.md`.
"""

import datetime
import logging
import os
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)

BACKUP_RETENTION_DAYS = 14
CONTAINER = "aura-db-1"
DB_USER = "aura"
DB_NAME = "aura"
TEST_DB_NAME = "aura_restore_test"
# Tabela referencyjna do sanity-check odtworzenia — najcenniejszy,
# nieodtwarzalny zasób projektu (historii cen konkurencji nie da się doscrapować).
SANITY_TABLE = "price_observations"
SANITY_MIN_ROWS = 1000  # poniżej tego progu odtworzenie uznajemy za podejrzane

_FILENAME_FORMAT = "aura-%Y%m%d-%H%M%S.dump"


def backup_dir() -> Path:
    base = Path(os.environ.get("LOCALAPPDATA", ".")) / "aura" / "backups"
    base.mkdir(parents=True, exist_ok=True)
    return base


def backup_filename(now: datetime.datetime) -> str:
    return now.strftime(_FILENAME_FORMAT)


def prune_old_backups(
    directory: Path, now: datetime.datetime, retention_days: int = BACKUP_RETENTION_DAYS
) -> list[Path]:
    """Usuwa kopie starsze niż retention_days. Zwraca listę usuniętych plików."""
    # Nazwy plików są naiwne (zawsze UTC, konwencja backup_filename) — porównanie
    # wymaga zdjęcia tzinfo z `now`, inaczej TypeError (naive vs aware).
    cutoff = (now - datetime.timedelta(days=retention_days)).replace(tzinfo=None)
    removed = []
    for f in sorted(directory.glob("aura-*.dump")):
        try:
            stamp = datetime.datetime.strptime(f.name, _FILENAME_FORMAT)
        except ValueError:
            continue  # plik spoza konwencji nazw — nie ruszamy
        if stamp < cutoff:
            f.unlink()
            removed.append(f)
    return removed


def create_backup(now: datetime.datetime | None = None) -> Path:
    """Zrzut bazy przez pg_dump (format custom, -Fc) do pliku lokalnego."""
    now = now or datetime.datetime.now(datetime.UTC)
    out = backup_dir() / backup_filename(now)
    with open(out, "wb") as f:
        result = subprocess.run(
            ["docker", "exec", CONTAINER, "pg_dump", "-U", DB_USER, "-Fc", DB_NAME],
            stdout=f,
            stderr=subprocess.PIPE,
            timeout=300,
        )
    if result.returncode != 0:
        out.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump nieudany: {result.stderr.decode(errors='replace')}")
    size = out.stat().st_size
    if size == 0:
        out.unlink()
        raise RuntimeError("pg_dump zwrócił pusty plik")
    logger.info("backup utworzony: %s (%d bajtów)", out, size)
    return out


def _psql(*args: str, stdin=None, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["docker", "exec", *(["-i"] if stdin is not None else []), CONTAINER, "psql",
         "-U", DB_USER, *args],
        stdin=stdin, capture_output=True, timeout=60, check=check,
    )


def test_restore(backup_path: Path) -> int:
    """Odtwarza backup do świeżej, tymczasowej bazy i sprawdza liczbę wierszy
    w tabeli referencyjnej. Zwraca liczbę wierszy; rzuca RuntimeError przy
    niepowodzeniu. Baza testowa jest sprzątana zawsze, nawet przy błędzie."""
    try:
        _psql("-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {TEST_DB_NAME}")
        _psql("-d", "postgres", "-c", f"CREATE DATABASE {TEST_DB_NAME}")
        with open(backup_path, "rb") as f:
            # pg_restore bywa niezerowy przy nieszkodliwych ostrzeżeniach (np.
            # brak roli właściciela) — o powodzeniu decyduje realna liczba
            # wierszy niżej, nie kod wyjścia pg_restore.
            subprocess.run(
                ["docker", "exec", "-i", CONTAINER, "pg_restore", "-U", DB_USER,
                 "-d", TEST_DB_NAME, "--no-owner"],
                stdin=f, capture_output=True, timeout=300,
            )
        count_result = _psql(
            "-d", TEST_DB_NAME, "-t", "-c", f"SELECT count(*) FROM {SANITY_TABLE}"
        )
        count = int(count_result.stdout.decode().strip())
    finally:
        _psql("-d", "postgres", "-c", f"DROP DATABASE IF EXISTS {TEST_DB_NAME}", check=False)

    if count < SANITY_MIN_ROWS:
        raise RuntimeError(
            f"Test odtworzenia: {SANITY_TABLE} ma tylko {count} wierszy "
            f"(oczekiwano >= {SANITY_MIN_ROWS}) — backup podejrzany."
        )
    logger.info("test odtworzenia OK: %s ma %d wierszy", SANITY_TABLE, count)
    return count
