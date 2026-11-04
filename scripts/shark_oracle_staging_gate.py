#!/usr/bin/env python3
"""REMURA B-P0: one-shot, synthetic Oracle staging gate; NEVER touches LIVE.

Run only from a disposable checkout beneath /tmp, as a non-root user.
Uses the existing 34 x 4000 M15 synthetic fixture and BOTH actual scanner
entrypoints. No HTTP, broker, VPS service calls, cron, secrets, real market
data, deployments, live SQLite read/write, or persistent artifacts.

Reports sampled (not absolute) WAL/RSS maxima, synthetic writer contention,
per-process CPU and wall time, backup/restore, rollback, and disk headroom.
This does NOT qualify LIVE ingest interference, Oracle billing or an edge.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

SCHEMA = "remura-track-b-oracle-synthetic-stage-v1"
PREFIX = "REMURA_TRACK_B_ORACLE_STAGING="
TABLES = ("squalincome_history", "squalincome_observations",
          "squalincome_events", "squalincome_last_scan")
MIN_FREE_BYTES = 256 * 1024 * 1024
MAX_PROCESS_RSS_MIB = 128
MAX_WRITER_LOCK_MS = 2000
MAX_CPU_RATIO = 6
MAX_WALL_SECONDS = 90


def guard_host():
    location = ROOT.resolve()
    if not location.is_relative_to(Path("/tmp").resolve()):
        raise RuntimeError("staging_checkout_must_be_under_tmp")
    if location.is_relative_to(Path("/opt/remura").resolve()):
        raise RuntimeError("never_execute_from_live_installation")
    if os.geteuid() == 0:
        raise RuntimeError("never_run_oracle_staging_as_root")
    if not Path("/proc/self/status").exists():
        raise RuntimeError("linux_procfs_required")
    if shutil.disk_usage("/tmp").free < MIN_FREE_BYTES:
        raise RuntimeError("insufficient_tmp_disk_headroom")


def rss_kib(pid):
    try:
        with open("/proc/%d/status" % pid, encoding="ascii") as f:
            for line in f:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (FileNotFoundError, PermissionError, ValueError, IndexError):
        pass
    return None


def file_size(path):
    try:
        return Path(path).stat().st_size
    except FileNotFoundError:
        return 0


def proc_io_bytes(pid):
    """Sample process I/O counters from Linux procfs (not an I/O peak)."""
    try:
        with open("/proc/%d/io" % pid, encoding="ascii") as file:
            entries = dict(line.strip().split(": ", 1) for line in file if ": " in line)
        return (int(entries.get("read_bytes", 0)),
                int(entries.get("write_bytes", 0)))
    except (OSError, ValueError, IndexError):
        return None


def mem_available_kib():
    try:
        with open("/proc/meminfo", encoding="ascii") as f:
            for line in f:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1])
    except (OSError, ValueError, IndexError):
        pass
    return None


def run_worker(mode, path):
    if mode not in ("standard", "compact") or path.name not in (
            "legacy.sqlite", "compact.sqlite"):
        raise ValueError("unexpected_synthetic_worker")
    command = [sys.executable, "-B",
               str(ROOT / "scripts" / "shark_resource_probe.py"),
               "--worker", mode, str(path)]
    # Reader and competing writer probe touch ONLY this synthetic DB.
    # BEGIN IMMEDIATE + ROLLBACK does not change PRAGMA data_version.
    process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                               text=True, env={**os.environ,
                                               "PYTHONDONTWRITEBYTECODE": "1"})
    started = time.monotonic()
    rss_max = 0
    wal_max = 0
    mem_min = None
    sampled_read_bytes = sampled_write_bytes = 0
    write_probes = busy = read_failures = 0
    write_max_ms = 0.0
    try:
        while process.poll() is None:
            elapsed = time.monotonic() - started
            if elapsed > MAX_WALL_SECONDS:
                process.kill()
                raise RuntimeError("synthetic_worker_time_limit")
            sample = rss_kib(process.pid)
            if sample is not None:
                rss_max = max(rss_max, sample)
            wal_max = max(wal_max, file_size(str(path) + "-wal"))
            io = proc_io_bytes(process.pid)
            if io is not None:
                sampled_read_bytes = max(sampled_read_bytes, io[0])
                sampled_write_bytes = max(sampled_write_bytes, io[1])
            mem = mem_available_kib()
            if mem is not None:
                mem_min = mem if mem_min is None else min(mem_min, mem)
            if mode == "compact" and write_probes < 100:
                try:
                    t0 = time.perf_counter()
                    probe = sqlite3.connect(path, timeout=0.005)
                    try:
                        probe.execute("BEGIN IMMEDIATE")
                        probe.rollback()
                    finally:
                        probe.close()
                    write_max_ms = max(write_max_ms,
                                       (time.perf_counter() - t0) * 1000)
                except sqlite3.OperationalError as e:
                    if "locked" not in str(e).lower():
                        raise
                    busy += 1
                write_probes += 1
                try:
                    reader = sqlite3.connect(
                        "file:%s?mode=ro" % path, uri=True, timeout=0.005)
                    try:
                        reader.execute("SELECT count(*) FROM prices").fetchone()
                    finally:
                        reader.close()
                except sqlite3.OperationalError:
                    read_failures += 1
            time.sleep(0.01)
        output, _stderr = process.communicate(timeout=5)
    finally:
        if process.poll() is None:
            process.kill()
            process.communicate(timeout=5)
    if process.returncode != 0:
        # Do not emit uncontrolled stderr or any private machine paths.
        raise RuntimeError("synthetic_%s_failed_exit_%d" %
                           (mode, process.returncode))
    from shark_resource_probe import PREFIX as WORKER_PREFIX
    rows = [s[len(WORKER_PREFIX):] for s in output.splitlines()
            if s.startswith(WORKER_PREFIX)]
    if len(rows) != 1:
        raise RuntimeError("synthetic_worker_report_missing")
    report = json.loads(rows[0])
    if report.get("mode") != mode or report.get("newBrokerCalls") != 0:
        raise RuntimeError("synthetic_worker_identity_mismatch")
    return report, {
        "sampledPeakRssMiB": round(rss_max / 1024, 2),
        "sampledMaxWalKiB": round(wal_max / 1024, 2),
        "sampledProcessReadMiB": round(sampled_read_bytes / 1048576, 2),
        "sampledProcessWriteMiB": round(sampled_write_bytes / 1048576, 2),
        "minHostMemAvailableMiB": (
            round(mem_min / 1024, 2) if mem_min is not None else None),
        "syntheticWriterProbes": write_probes,
        "syntheticWriterBusy": busy,
        "syntheticWriterMaxMs": round(write_max_ms, 2),
        "syntheticReaderFailures": read_failures,
        "walTruePeakGuaranteed": False,
        "realIngestInterferenceMeasured": False,
    }


def table_digest(path, table):
    # Read only from temporary synthetic databases.
    with sqlite3.connect(path) as db:
        rows = db.execute("SELECT * FROM " + table +
                          " ORDER BY rowid").fetchall()
        stream = repr(rows).encode("utf-8")
        return (len(rows), hashlib.sha256(stream).hexdigest())


def verify_backup_restore_and_rollback(stage, folder):
    from scripts import shark_price_only_compact as compact
    restored = folder / "restore-test.sqlite"
    with sqlite3.connect(stage) as source, sqlite3.connect(restored) as dest:
        source.backup(dest)
    with sqlite3.connect(stage) as original, sqlite3.connect(restored) as copy:
        if (original.execute("PRAGMA integrity_check").fetchone()[0] != "ok"
                or copy.execute("PRAGMA integrity_check").fetchone()[0] != "ok"):
            raise RuntimeError("synthetic_backup_integrity_failure")
        src = compact.summary(original)
        dst = compact.summary(copy)
        if (src != dst or src.get("fullScanDenominator") != 34
                or src.get("immutableBatches") != 1):
            raise RuntimeError("synthetic_restore_batch_mismatch")
        src_batch = original.execute(
            "SELECT payload_sha256, payload_zlib FROM "
            "research_price_only_batches").fetchone()
        dst_batch = copy.execute(
            "SELECT payload_sha256, payload_zlib FROM "
            "research_price_only_batches").fetchone()
        if src_batch != dst_batch:
            raise RuntimeError("synthetic_restore_payload_mismatch")
        if original.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='trigger' "
            "AND name LIKE 'research_compact_no_%'").fetchone()[0] != 2:
            raise RuntimeError("immutability_trigger_missing")
        if copy.execute(
            "SELECT count(*) FROM sqlite_master WHERE type='trigger' "
            "AND name LIKE 'research_compact_no_%'").fetchone()[0] != 2:
            raise RuntimeError("restored_immutability_trigger_missing")
    for table in TABLES:
        if table_digest(stage, table) != table_digest(restored, table):
            raise RuntimeError("synthetic_restore_legacy_mismatch")
    # Real SQLite rollback, deliberately creates then removes an isolated
    # staging-only marker. Never writes to any LIVE database.
    with sqlite3.connect(restored) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("CREATE TABLE rollback_test_staging_only(v INTEGER)")
        db.execute("INSERT INTO rollback_test_staging_only VALUES(1)")
        db.rollback()
        if db.execute("SELECT count(*) FROM sqlite_master "
                      "WHERE name='rollback_test_staging_only'").fetchone()[0]:
            raise RuntimeError("synthetic_rollback_failed")
    return {"sqliteBackupRestore": "PASS", "sqliteRollback": "PASS",
            "backupMiB": round(file_size(restored) / (1024 * 1024), 3),
            "integrityCheck": "ok", "immutableTriggersPreserved": True}


def run():
    guard_host()
    from shark_resource_probe import fixture, clone
    from test_shark_staging_scan import standard_state
    before_free = shutil.disk_usage("/tmp").free
    with tempfile.TemporaryDirectory(prefix="remura-b-p0-", dir="/tmp") as tmp:
        folder = Path(tmp).resolve()
        if not folder.is_relative_to(Path("/tmp").resolve()):
            raise RuntimeError("scratch_directory_guard_failed")
        seed = folder / "seed.sqlite"
        baseline = folder / "legacy.sqlite"
        compact = folder / "compact.sqlite"
        # Fixed synthetic clock and quotes; NO Oracle production DB opened.
        fixture(seed, with_cot=False, all_priced=True, m15_count=4000)
        clone(seed, baseline)
        clone(seed, compact)
        original, std_probe = run_worker("standard", baseline)
        proposed, cmp_probe = run_worker("compact", compact)
        if standard_state(baseline) != standard_state(compact):
            raise RuntimeError("live_squalincome_behavior_not_equivalent")
        if (proposed.get("sourceDataVersionValidated") is not True
                or proposed.get("sqliteWriterLockMs") is None
                or proposed.get("squalincomeExamined") !=
                original.get("squalincomeExamined")):
            raise RuntimeError("provenance_or_classification_gate_failed")
        if (proposed["processPeakRssMiB"] >= MAX_PROCESS_RSS_MIB
                or proposed["sqliteWriterLockMs"] > MAX_WRITER_LOCK_MS
                or proposed["cpuSeconds"] /
                max(original["cpuSeconds"], 0.001) > MAX_CPU_RATIO):
            raise RuntimeError("oracle_synthetic_resource_budget_exceeded")
        backup = verify_backup_restore_and_rollback(compact, folder)
        usage = sum(file_size(p) for p in folder.iterdir() if p.is_file())
        result = {
            "schema": SCHEMA,
            "status": "ORACLE_SYNTHETIC_GATE_ONLY",
            "markets": 34, "m15BarsPerMarket": 4000,
            "baseline": original, "compact": proposed,
            "baselineProbe": std_probe, "compactProbe": cmp_probe,
            "cpuSecondsRatio": round(proposed["cpuSeconds"] /
                                     max(original["cpuSeconds"], 0.001), 2),
            "backupRestoreRollback": backup,
            "scratchDataMiB": round(usage / (1024 * 1024), 2),
            "tmpFreeBeforeMiB": round(before_free / (1024 * 1024), 1),
            "tmpFreeDuringMiB": round(shutil.disk_usage("/tmp").free /
                                      (1024 * 1024), 1),
            "liveDatabaseOpened": False,
            "liveConfigurationChanged": False,
            "brokerCallsAdded": 0,
            "liveIngestInterferenceVerified": False,
            "oracleBillingVerified": False,
            "githubActionsBillingVerified": False,
            "firestoreBillingVerified": False,
            "realInstitutionalEdgeEstablished": False,
        }
        print(PREFIX + json.dumps(result, sort_keys=True, separators=(",", ":")))
    print("REMURA_TRACK_B_ORACLE_STAGING_COMPLETED=TRUE")


def main():
    if len(sys.argv) == 2 and sys.argv[1] == "--self-check":
        print("REMURA_TRACK_B_ORACLE_STAGING_SELF_CHECK=PASS")
    elif len(sys.argv) == 2 and sys.argv[1] == "--run":
        run()
    else:
        raise SystemExit("usage: python scripts/shark_oracle_staging_gate.py "
                         "--self-check|--run")


if __name__ == "__main__":
    main()
