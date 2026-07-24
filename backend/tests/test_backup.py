import datetime

from app.backup import backup_filename, prune_old_backups


def test_backup_filename_format():
    now = datetime.datetime(2026, 7, 20, 8, 30, 5, tzinfo=datetime.UTC)
    assert backup_filename(now) == "aura-20260720-083005.dump"


def test_prune_old_backups_removes_only_expired(tmp_path):
    now = datetime.datetime(2026, 7, 20, tzinfo=datetime.UTC)
    fresh = tmp_path / backup_filename(now - datetime.timedelta(days=1))
    stale = tmp_path / backup_filename(now - datetime.timedelta(days=15))
    boundary = tmp_path / backup_filename(now - datetime.timedelta(days=14))
    for f in (fresh, stale, boundary):
        f.write_bytes(b"x")

    removed = prune_old_backups(tmp_path, now, retention_days=14)

    assert stale in removed
    assert fresh not in removed
    assert boundary not in removed  # dokładnie na granicy — jeszcze zostaje
    assert fresh.exists()
    assert not stale.exists()


def test_prune_old_backups_ignores_foreign_files(tmp_path):
    now = datetime.datetime(2026, 7, 20, tzinfo=datetime.UTC)
    foreign = tmp_path / "readme.txt"
    foreign.write_text("nie ruszać")

    removed = prune_old_backups(tmp_path, now, retention_days=14)

    assert removed == []
    assert foreign.exists()
