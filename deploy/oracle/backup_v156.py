#!/usr/bin/env python3
"""Backup SQLite coerente, con prova di ripristino isolata, per release REMURA v1.56.

--check: nessuna scrittura, verifica base esistente e spazio minimo.
--backup: snapshot SQLite tramite API backup (compatibile con WAL) + restore-test
          in una directory privata temporanea; NON installa nulla.
Non invoca cTrader, systemctl, la rete, i segreti o il sistema di trading.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import stat
import tempfile

APP = Path("/opt/remura")
PRIVATE = APP / "private"
SOURCE = PRIVATE / "remura-prices.sqlite3"
BACKUPS = PRIVATE / "predeploy-backups"
MIN_MARGIN = 20 * 1024 * 1024


def require(ok, reason):
    if not ok:
        raise RuntimeError("STOP_" + reason)


def plain_directory(path):
    require(path.is_dir() and not path.is_symlink(), "DIRECTORY_INVALID")
    require(stat.S_ISDIR(path.lstat().st_mode), "DIRECTORY_TYPE")


def validate_source():
    plain_directory(PRIVATE)
    require(SOURCE.is_file() and not SOURCE.is_symlink(), "SOURCE_MISSING_OR_LINK")
    require(stat.S_ISREG(SOURCE.lstat().st_mode), "SOURCE_NOT_REGULAR")
    size = SOURCE.stat().st_size
    require(0 < size <= 8 * 1024**3, "SOURCE_SIZE")
    # A complete backup and a separate restore both need disk space.
    free = shutil.disk_usage(PRIVATE).free
    require(free > 3 * size + MIN_MARGIN, "DISK_SPACE")
    with sqlite3.connect(SOURCE.as_uri() + "?mode=ro", uri=True, timeout=15) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SOURCE_INTEGRITY")
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require({"prices", "status"} <= names, "SOURCE_SCHEMA")
        counts = tuple(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                       for table in ("prices", "status"))
    return size, counts


def inspect(path):
    require(path.is_file() and not path.is_symlink(), "SNAPSHOT_MISSING")
    with sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=15) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SNAPSHOT_INTEGRITY")
        names = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require({"prices", "status"} <= names, "SNAPSHOT_SCHEMA")
        counts = tuple(db.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
                       for table in ("prices", "status"))
        return counts


def snapshot(path):
    # sqlite3.backup() obtains a consistent snapshot of an actively used WAL DB.
    with sqlite3.connect(SOURCE.as_uri() + "?mode=ro", uri=True, timeout=30) as src:
        with sqlite3.connect(path, timeout=30) as dst:
            src.backup(dst, pages=128, sleep=0.1)
    os.chmod(path, 0o600)


def restore_test(snapshot_path, expected):
    # Restores only to a disposable DB; never writes to SOURCE.
    with tempfile.TemporaryDirectory(prefix="restore-test-v156-", dir=BACKUPS) as work:
        target = Path(work) / "restored.sqlite3"
        with sqlite3.connect(snapshot_path.as_uri() + "?mode=ro", uri=True) as src:
            with sqlite3.connect(target) as dst:
                src.backup(dst, pages=128, sleep=0.1)
        require(inspect(target) == expected, "RESTORE_TEST_COUNTS")


def create_backup():
    os.umask(0o077)
    size, _ = validate_source()
    if not BACKUPS.exists():
        BACKUPS.mkdir(mode=0o700)
    plain_directory(BACKUPS)
    # Do not use a predictable filename or overwrite an existing backup.
    temp = Path(tempfile.mkdtemp(prefix="candidate-v156-", dir=BACKUPS))
    try:
        temp.chmod(0o700)
        image = temp / "remura-prices.sqlite3"
        snapshot(image)
        verified = inspect(image)
        restore_test(image, verified)
        digest = hashlib.sha256(image.read_bytes()).hexdigest()
        (temp / "manifest.txt").write_text("remura-v156-sqlite\nsha256=" + digest
                                           + "\nsource_bytes=" + str(size) + "\n", encoding="ascii")
        os.chmod(temp / "manifest.txt", 0o600)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        # The random suffix avoids accidental collisions within the same second.
        dest = BACKUPS / ("backup-v156-" + stamp + "-" + temp.name.rsplit("-", 1)[-1])
        require(not dest.exists(), "BACKUP_EXISTS")
        temp.rename(dest)
        return ("BACKUP_SQLITE=VERIFICATO", "RESTORE_TEST=OK", "BACKUP_DIR=PRIVATA",
                "FONTE_SQLITE_INVARIATA=SI", "NESSUN_DEPLOY=SI")
    finally:
        if temp.exists():
            shutil.rmtree(temp)


def main():
    p = argparse.ArgumentParser(description="REMURA SQLite pre-release guard")
    choice = p.add_mutually_exclusive_group(required=True)
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--backup", action="store_true")
    args = p.parse_args()
    try:
        if args.check:
            validate_source()
            print("PREFLIGHT_SQLITE=OK")
            print("NESSUNA_SCRITTURA=SI")
        else:
            for line in create_backup():
                print(line)
    except (RuntimeError, OSError, sqlite3.Error) as exc:
        # No exception payload or path printed (avoid leaking private structure).
        message = str(exc)
        print("PREFLIGHT_SQLITE=STOP")
        print("MOTIVO=" + message if message.startswith("STOP_") else "MOTIVO=IO_OR_SQLITE_ERROR")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
