#!/usr/bin/env python3
"""Track C4b(j): AES-256-GCM + SQLite WAL recovery rehearsal, FICTIONAL LAB ONLY.

Never accesses LIVE, provider, GitHub API, production paths or secrets. SQLite
snapshot is a bounded synthetic (<1 MiB) test: one-shot AESGCM must NOT be
reused for large production files. "Remote" is merely another directory
on the SAME GitHub Actions runner, not an actual external failure domain.
"""
from __future__ import annotations
from contextlib import closing, contextmanager
import hashlib
import os
from pathlib import Path
import shutil
import sqlite3
import tempfile

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MODE = "OFFLINE_C4BJ_SYNTHETIC_RECOVERY_ONLY"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
SCHEMA = "remura-c4bj-synthetic-recovery-v1"
HEADER = b"REMURA-C4BJ-SYNTHETIC-AES256GCM-V1\n"
AAD = b"remura-c4bj-synthetic-backup-v1"
MAX_SNAPSHOT = 1024 * 1024
MAX_CIPHERTEXT = MAX_SNAPSHOT + len(HEADER) + 12 + 16
FAULTS = frozenset((
    "none", "tamper_ciphertext", "tamper_rehashed_ciphertext", "wrong_key",
    "truncate_ciphertext", "missing_offhost", "malformed_header",
    "header_rehashed", "tamper_digest",
))


def _result(state, *, snapshot=False, encrypted=False, transferred=False,
            source_destroyed=False, integrity=False, counts=False,
            rejected=False):
    return {
        "schema": SCHEMA,
        "state": state,
        "sqliteOnlineBackupRehearsed": snapshot,
        "aes256GcmAuthenticatedEncryptionRehearsed": encrypted,
        "ciphertextCopiedToSeparateLabDirectory": transferred,
        "syntheticSourceDeletedBeforeRestore": source_destroyed,
        "restoredSqliteIntegrityCheck": integrity,
        "restoredSyntheticFixtureVerified": counts,
        "tamperOrWrongKeyRejected": rejected,
        "realOffhostProviderUsed": False,
        "realIndependentFailureDomainVerified": False,
        "realExternalKeyRecoveryVerified": False,
        "realVpsDataAccessed": False,
        "actualEncryptedBackupCreated": False,
        "actualOperationalRestoreVerified": False,
        "productionSizeAndCostAssessed": False,
        "productionEncryptionStreamingSafeVerified": False,
        "operationalDecision": NO_GO,
        "newProviderCalls": 0,
        "newVpsRequests": 0,
    }


def _private_write(path, data):
    with path.open("xb") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(data)


@contextmanager
def _fictional_wal_source(path):
    with closing(sqlite3.connect(path)) as c, c:
        c.execute("PRAGMA journal_mode=WAL")
        c.execute("CREATE TABLE prices(symbol TEXT NOT NULL, tick INTEGER NOT NULL)")
        c.execute("CREATE TABLE status(name TEXT PRIMARY KEY, value TEXT NOT NULL)")
        c.executemany("INSERT INTO prices VALUES (?,?)", [
            ("FAKE_EURUSD", 11), ("FAKE_XAUUSD", 22), ("FAKE_EURUSD", 33)
        ])
        c.execute("INSERT INTO status VALUES ('lab','SYNTHETIC_ONLY')")
        c.commit()
        yield c


def _fixture_verified(path):
    # Restored temporary file is immutable, not the live source.
    with closing(sqlite3.connect(
        path.as_uri() + "?mode=ro&immutable=1", uri=True, timeout=2
    )) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        tables = {r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if tables != {"prices", "status"}:
            return integrity, False
        candles = db.execute(
            "SELECT symbol,tick FROM prices ORDER BY rowid"
        ).fetchall()
        status = db.execute(
            "SELECT value FROM status WHERE name='lab'"
        ).fetchone()
        return integrity, (
            candles == [("FAKE_EURUSD", 11), ("FAKE_XAUUSD", 22),
                        ("FAKE_EURUSD", 33)]
            and status == ("SYNTHETIC_ONLY",)
        )


def _authenticated_decrypt(payload, key, digest):
    # Verify remote SHA256, header AND AES-GCM tag before any restored DB write.
    if type(payload) is not bytes or not 0 < len(payload) <= MAX_CIPHERTEXT:
        raise ValueError("ciphertext_size_bound")
    if hashlib.sha256(payload).digest() != digest:
        raise ValueError("ciphertext_digest_mismatch")
    if not payload.startswith(HEADER):
        raise ValueError("unrecognized_ciphertext_header")
    body = payload[len(HEADER):]
    if len(body) < 28:
        raise ValueError("ciphertext_too_short")
    return AESGCM(key).decrypt(body[:12], body[12:], AAD)


def rehearse(*, mode=None, fault="none"):
    """Entirely synthetic temporary recovery on a single runner."""
    if mode != MODE:
        raise ValueError("explicit_synthetic_lab_mode_required")
    if type(fault) is not str or fault not in FAULTS:
        raise ValueError("unknown_synthetic_fault")
    # No caller-supplied paths: impossible to target /opt/remura or a real DB.
    with tempfile.TemporaryDirectory(prefix="remura-c4bj-") as work:
        base = Path(work)
        source = base / "synthetic-source"
        mock = base / "simulated-offhost-same-runner"
        recovery = base / "isolated-synthetic-restore"
        for directory in (source, mock, recovery):
            directory.mkdir(mode=0o700)
        db = source / "fake.sqlite3"
        snap = source / "backup.sqlite3"
        local_cipher = source / "encrypted.bin"
        remote_cipher = mock / "encrypted.bin"
        restored = recovery / "restored.sqlite3"
        created = encrypted = copied = deleted = False
        try:
            with _fictional_wal_source(db) as live:
                wal = source / (db.name + "-wal")
                if not wal.is_file() or wal.stat().st_size == 0:
                    return _result("FAILED_SYNTHETIC_WAL_TEST_FIXTURE")
                with closing(sqlite3.connect(snap)) as dst, dst:
                    live.backup(dst, pages=32, sleep=0.01)
                created = True
            integrity, content = _fixture_verified(snap)
            if not (integrity and content):
                return _result("FAILED_SQLITE_SYNTHETIC_SNAPSHOT", snapshot=True)
            original = snap.read_bytes()
            if not 0 < len(original) <= MAX_SNAPSHOT:
                return _result("FAILED_SNAPSHOT_SIZE_BOUND", snapshot=True)
            key = AESGCM.generate_key(bit_length=256)  # stays in RAM on runner
            nonce = os.urandom(12)  # random nonce with fresh ephemeral key
            cipher = HEADER + nonce + AESGCM(key).encrypt(nonce, original, AAD)
            if len(cipher) > MAX_CIPHERTEXT:
                return _result("FAILED_CIPHERTEXT_SIZE_BOUND", snapshot=True)
            _private_write(local_cipher, cipher)
            encrypted = True
            digest = hashlib.sha256(cipher).digest()
            shutil.copyfile(local_cipher, remote_cipher)
            os.chmod(remote_cipher, 0o600)
            copied = True
            remote = remote_cipher.read_bytes()
            if remote.startswith(b"SQLite format 3") or remote == original:
                return _result("FAILED_REMOTE_NOT_ENCRYPTED",
                               snapshot=True, encrypted=True, transferred=True)
            # Deletes only its OWN temp source; never touches production.
            shutil.rmtree(source)
            deleted = True
            if fault in ("tamper_ciphertext", "tamper_rehashed_ciphertext"):
                changed = bytearray(remote)
                changed[-1] ^= 1
                remote_cipher.write_bytes(changed)
                if fault == "tamper_rehashed_ciphertext":
                    digest = hashlib.sha256(changed).digest()
            elif fault == "truncate_ciphertext":
                remote_cipher.write_bytes(remote[:-11])
            elif fault in ("malformed_header", "header_rehashed"):
                changed = bytearray(remote)
                changed[0] ^= 1
                remote_cipher.write_bytes(changed)
                if fault == "header_rehashed":
                    digest = hashlib.sha256(changed).digest()
            elif fault == "missing_offhost":
                remote_cipher.unlink()
            elif fault == "tamper_digest":
                digest = bytes(32)
            elif fault == "wrong_key":
                key = AESGCM.generate_key(bit_length=256)
            try:
                if remote_cipher.stat().st_size > MAX_CIPHERTEXT:
                    raise ValueError("remote_size_bound")
                plaintext = _authenticated_decrypt(
                    remote_cipher.read_bytes(), key, digest
                )
                if not 0 < len(plaintext) <= MAX_SNAPSHOT:
                    raise ValueError("restored_size_bound")
                _private_write(restored, plaintext)
                integrity, valid = _fixture_verified(restored)
                if not (integrity and valid):
                    return _result("FAILED_SQLITE_ISOLATED_RESTORE",
                                   snapshot=True, encrypted=True, transferred=True,
                                   source_destroyed=True, integrity=integrity)
                if fault != "none":
                    return _result("FAILED_FAULT_INJECTION_WAS_NOT_REJECTED",
                                   snapshot=True, encrypted=True, transferred=True,
                                   source_destroyed=True, integrity=True, counts=True)
                return _result("SYNTHETIC_AESGCM_RESTORE_REHEARSAL_PASS_ONLY",
                               snapshot=True, encrypted=True, transferred=True,
                               source_destroyed=True, integrity=True, counts=True)
            except (InvalidTag, ValueError, OSError, sqlite3.DatabaseError):
                return _result("SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED",
                               snapshot=created, encrypted=encrypted,
                               transferred=copied, source_destroyed=deleted,
                               rejected=fault != "none")
        except (OSError, ValueError, sqlite3.DatabaseError):
            return _result("FAILED_SYNTHETIC_OFFLINE_REHEARSAL",
                           snapshot=created, encrypted=encrypted,
                           transferred=copied, source_destroyed=deleted)
