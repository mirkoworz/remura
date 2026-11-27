#!/usr/bin/env python3
"""REMURA v1.65: wholly synthetic, offline release transaction rehearsal.

NO LIVE entrypoint. The only CLI action creates a throwaway local laboratory:
fake EURUSD/XAUUSD SQLite in WAL, consistent SQLite API backup, isolated restore
and integrity check, simulated 14-file release+rollback, and simulated updater
state invariance. Does not install/inspect a VPS, authenticate, call providers,
touch real SQLite, run systemctl, or configure a collector.

Never interpret this result as proof of an off-host backup or authorization.
"""
from __future__ import annotations

import argparse
from contextlib import closing
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

SCHEMA = "remura-v165-synthetic-release-lab-v1"
MODE = "OFFLINE_V165_SYNTHETIC_TRANSACTION_ONLY"
NO_GO = "NO_GO_RELEASE_AND_PROSPECTIVE_COLLECTION"
EXPECTED_FILES = frozenset((
    "index.html", "asset.html", "mercati.html", "forex.html",
    "catalogo.html", "statistica-squali.html", "stato-prezzi.html",
    "fonti.html", "impostazioni.html", "nav.js", "sw.js",
    "scripts/private_server.py", "scripts/storage_inventory_v165.py",
    "scripts/storage_cache_v165.py",
))
FAULTS = frozenset((
    "after_backup", "corrupt_snapshot", "after_stage",
    "mid_replace", "after_replace", "after_mock_reconcile",
))
RECORDS = (("EURUSD", 101), ("XAUUSD", 202))
UPDATER_STATE = b'{"installedSha":"FICTIONAL_V164","enabled":false}\n'
MAX_SYNTHETIC_DB_BYTES = 4 * 1024 * 1024


class LabRejection(ValueError):
    """Only a synthetic failure; NEVER a production rollback outcome."""


def require(ok, reason):
    if not ok:
        raise LabRejection("STOP_" + reason)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def synthetic_files():
    """No repository file, secret or business data is copied into the lab."""
    return {name: ("FICTIONAL_OLD_V164_" + name + "\n").encode("ascii")
            for name in sorted(EXPECTED_FILES)}


def validate_file_set(before, staged):
    require(type(before) is dict and type(staged) is dict
            and set(before) == EXPECTED_FILES
            and set(staged) == EXPECTED_FILES, "FILE_ALLOWLIST")
    for name in EXPECTED_FILES:
        require(type(before[name]) is bytes and type(staged[name]) is bytes
                and 0 < len(before[name]) <= 100_000
                and 0 < len(staged[name]) <= 100_000,
                "BOUNDED_FAKE_FILES")
    return True


def staged_files(before):
    require(type(before) is dict and set(before) == EXPECTED_FILES,
            "FILE_ALLOWLIST")
    # Validate types/limits BEFORE calling bytes.replace: reject malformed input
    # with a deterministic no-go instead of raising an unexpected exception.
    validate_file_set(before, before)
    result = {name: before[name].replace(b"V164", b"V165") for name in before}
    validate_file_set(before, result)
    require(all(result[name] != before[name] for name in before),
            "UNCHANGED_STAGE")
    return result


def _fake_db(path):
    db = sqlite3.connect(path)
    try:
        require(db.execute("PRAGMA journal_mode=WAL").fetchone()[0].lower()
                == "wal", "WAL_NOT_ENABLED")
        db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY, fictional INTEGER)")
        db.execute("CREATE TABLE status(key TEXT PRIMARY KEY, value TEXT)")
        db.executemany("INSERT INTO prices VALUES (?,?)", RECORDS)
        db.execute("INSERT INTO status VALUES ('source','FICTIONAL_ONLY')")
        db.commit()
        require(db.execute("SELECT COUNT(*) FROM prices").fetchone()[0] == 2,
                "FICTIONAL_ROWS_MISSING")
        # Leave the live-simulated connection open while the snapshot is taken:
        # any pending WAL content must be included in sqlite3.backup().
        return db
    except BaseException:
        db.close()
        raise


def _consistent_backup(source, destination):
    """Use SQLite's backup API, never copy the SQLite file under WAL."""
    with closing(sqlite3.connect(destination)) as target:
        source.backup(target, pages=32, sleep=0.01)
        require(target.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "BACKUP_INTEGRITY")


def _validate_db(path):
    with closing(sqlite3.connect(path.as_uri() + "?mode=ro", uri=True)) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "RESTORE_INTEGRITY")
        rows=tuple(db.execute("SELECT symbol,fictional FROM prices ORDER BY symbol"))
        status=db.execute("SELECT value FROM status WHERE key='source'").fetchone()
        require(rows == tuple(sorted(RECORDS))
                and status == ("FICTIONAL_ONLY",), "RESTORED_ROWS_CHANGED")
        return len(rows)


def isolated_restore(snapshot, restored, expected_digest):
    """Restore in another temporary directory on SAME runner, not off-host."""
    require(snapshot.is_file() and not snapshot.is_symlink(),
            "SNAPSHOT_MISSING")
    require(sha(snapshot.read_bytes()) == expected_digest,
            "SNAPSHOT_DIGEST_CHANGED")
    with closing(sqlite3.connect(snapshot.as_uri() + "?mode=ro", uri=True)) as src:
        with closing(sqlite3.connect(restored)) as dest:
            src.backup(dest, pages=32, sleep=0.01)
    require(_validate_db(restored) == 2, "RESTORE_COUNTS_WRONG")
    return True


def simulate(*, mode=None, fault=None, before=None):
    """Entirely temp-only, with deliberately injected failures and rollback.

    A returned 'rollback' means restoration of fictional byte arrays only.
    The updater marker is never changed, even on successful mock application.
    """
    require(mode == MODE, "OFFLINE_MODE_REQUIRED")
    require(fault is None or fault in FAULTS, "UNKNOWN_FAULT")
    originals = synthetic_files() if before is None else before
    staged = staged_files(originals)
    validate_file_set(originals, staged)
    report = {
        "schema": SCHEMA,
        "state": "OFFLINE_SYNTHETIC_ONLY",
        "syntheticSqliteWalBackupRestored": False,
        "syntheticIntegrityAndRowsVerified": False,
        "syntheticFileRollbackVerified": False,
        "syntheticUpdaterStateUnchanged": False,
        "syntheticFaultDetected": False,
        "localTemporaryDirectoriesOnly": True,
        "realVpsContacted": False,
        "realDatabaseRead": False,
        "realBackupCreated": False,
        "realRestoreVerified": False,
        "realFilesInstalled": False,
        "realAutoupdaterChanged": False,
        "offhostBackupVerified": False,
        "oracleBillingVerified": False,
        "releaseAuthorized": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
    }
    with tempfile.TemporaryDirectory(prefix="remura-v165-lab-") as tmp:
        base=Path(tmp)
        database=base/"original-fake.sqlite3"
        backup_dir=base/"mock-backup"
        recovery_dir=base/"mock-recovery"
        backup_dir.mkdir()
        recovery_dir.mkdir()
        snapshot=backup_dir/"snapshot-fake.sqlite3"
        restored=recovery_dir/"restored-fake.sqlite3"
        # This mock 'installed' directory exists only on the CI runner.
        installed=dict(originals)
        original_digests={k: sha(v) for k,v in originals.items()}
        updater_state=UPDATER_STATE
        restored_file_state=False
        try:
            with closing(_fake_db(database)) as db:
                _consistent_backup(db, snapshot)
                require(snapshot.stat().st_size <= MAX_SYNTHETIC_DB_BYTES,
                        "SYNTHETIC_DB_TOO_LARGE")
                checkpoint_digest=sha(snapshot.read_bytes())
                if fault == "corrupt_snapshot":
                    with snapshot.open("r+b") as fp:
                        fp.seek(64)
                        b=fp.read(1)
                        require(bool(b), "SYNTHETIC_SNAPSHOT_TOO_SMALL")
                        fp.seek(64)
                        fp.write(bytes((b[0] ^ 0x80,)))
                if fault == "after_backup":
                    raise LabRejection("STOP_INJECTED_AFTER_BACKUP")
                isolated_restore(snapshot, restored, checkpoint_digest)
                report["syntheticSqliteWalBackupRestored"]=True
                report["syntheticIntegrityAndRowsVerified"]=True

            if fault == "after_stage":
                raise LabRejection("STOP_INJECTED_AFTER_STAGE")
            for index,name in enumerate(sorted(EXPECTED_FILES)):
                installed[name] = staged[name]
                if fault == "mid_replace" and index == 4:
                    raise LabRejection("STOP_INJECTED_MID_REPLACE")
            require(set(installed) == EXPECTED_FILES, "MOCK_FILE_SET")
            require(all(installed[k] == staged[k] for k in EXPECTED_FILES),
                    "MOCK_FILE_COMMIT")
            if fault == "after_replace":
                raise LabRejection("STOP_INJECTED_AFTER_REPLACE")
            # No autoupdater write is performed. The marker is hypothetical,
            # and would need its own pinned reconciler in a future LIVE release.
            require(updater_state == UPDATER_STATE, "UPDATER_WAS_CHANGED")
            if fault == "after_mock_reconcile":
                raise LabRejection("STOP_INJECTED_AFTER_MOCK_RECONCILE")
        except (LabRejection, sqlite3.Error, OSError) as exc:
            report["state"]="SYNTHETIC_FAILURE_REJECTED"
            report["syntheticFaultDetected"]=True
            # Never echo exception text, paths, data or private information.
            if fault is None:
                raise
        finally:
            installed.clear()
            installed.update(originals)
            restored_file_state = (
                set(installed) == EXPECTED_FILES
                and all(sha(installed[k]) == original_digests[k]
                        for k in EXPECTED_FILES)
            )
            report["syntheticFileRollbackVerified"]=restored_file_state
            report["syntheticUpdaterStateUnchanged"]=updater_state == UPDATER_STATE

        require(restored_file_state, "SYNTHETIC_ROLLBACK_FAILED")
        require(report["syntheticUpdaterStateUnchanged"],
                "SYNTHETIC_UPDATER_CHANGED")
        if fault is None:
            require(report["syntheticSqliteWalBackupRestored"]
                    and report["syntheticIntegrityAndRowsVerified"],
                    "MISSING_SYNTHETIC_RESTORE_PROOF")
        else:
            require(report["syntheticFaultDetected"],
                    "FAULT_WAS_NOT_DETECTED")
    return report


def main():
    parser=argparse.ArgumentParser(description="v1.65 synthetic lab ONLY; NO LIVE mode")
    parser.add_argument("--simulate-offline", required=True, action="store_true")
    options=parser.parse_args()
    _=options
    result=simulate(mode=MODE)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
