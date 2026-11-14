#!/usr/bin/env python3
"""REMURA Track B: disposable CVD shard resource and failure-mode probe.

Synthetic-only GitHub runner/local temp filesystem; NOT Oracle or REMURA LIVE.
Uses the real private shard/backup prototypes with reduced row cap and absent
source documents (missing slots remain UNKNOWN). Creates no network requests,
alerts, orders, secrets or persistent exported research artefacts.
"""
from __future__ import annotations

from datetime import timedelta
import json
import os
from pathlib import Path
import resource
import sqlite3
import sys
import tempfile
import threading
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"tests"))

from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_shard_backup as backup
from scripts import shark_cvd_storage_gate as storage
from test_shark_cvd_scan_coverage import DAY, KEY, stamp

SCHEMA="remura-track-b-private-cvd-shard-resource-probe-v1"


def _rss_kib():
    try:
        with open("/proc/self/status",encoding="ascii") as stream:
            for row in stream:
                if row.startswith("VmRSS:"):
                    return int(row.split()[1])
    except (OSError,ValueError,IndexError):
        pass
    return None


def _files_bytes(folder):
    return sum(p.stat().st_size for p in folder.iterdir()
               if p.is_file() and not p.is_symlink())


def _timed(fn):
    wall=time.perf_counter()
    cpu=time.process_time()
    value=fn()
    return value,{
        "wallMs":round(1000*(time.perf_counter()-wall),3),
        "cpuMs":round(1000*(time.process_time()-cpu),3),
    }


def _attempt(folder,index):
    at=DAY+timedelta(hours=5,minutes=15*index)
    return shards.record(folder,symbol="EURUSD",
                         slot_closed_at=stamp(at),
                         source_document=None,secret=KEY,
                         clock=at+timedelta(minutes=1))


def run():
    with tempfile.TemporaryDirectory(prefix="remura-shard-resource-only-") as temp:
        parent=Path(temp)
        source=parent/"source"
        dest=parent/"backup"
        restored=parent/"restore"
        source.mkdir(mode=0o700)
        # Synthetic stand-in for periodic price ingest, on an independent
        # WAL-backed SQLite. It is deliberately NOT the LIVE price collector.
        price_db=parent/"synthetic-price-collector.sqlite3"
        with sqlite3.connect(price_db) as price:
            price.execute("PRAGMA journal_mode=WAL")
            price.execute("CREATE TABLE heartbeat(sequence INTEGER PRIMARY KEY)")
        price_stop=threading.Event()
        price_stats={"writes":0,"errors":0,"maxCommitMs":0.0}

        def price_loop():
            try:
                with sqlite3.connect(price_db,timeout=0.1) as db:
                    while not price_stop.is_set():
                        begin=time.perf_counter()
                        db.execute("INSERT INTO heartbeat DEFAULT VALUES")
                        db.commit()
                        price_stats["writes"]+=1
                        price_stats["maxCommitMs"]=max(price_stats["maxCommitMs"],
                            (time.perf_counter()-begin)*1000)
                        price_stop.wait(0.02)
            except (sqlite3.Error,OSError):
                price_stats["errors"]+=1

        price_thread=threading.Thread(target=price_loop,daemon=True)
        price_thread.start()
        peak={"rssKiB":0,"walBytes":0,"priceWalBytes":0,
              "journalBytes":0,"totalScratchBytes":0}
        stopped=threading.Event()

        def sample():
            while not stopped.is_set():
                rss=_rss_kib()
                if rss is not None:
                    peak["rssKiB"]=max(peak["rssKiB"],rss)
                peak["walBytes"]=max(peak["walBytes"],sum(
                    p.stat().st_size for p in source.glob("*.sqlite3-wal")
                    if p.is_file()))
                wal=Path(str(price_db)+"-wal")
                if wal.is_file():
                    peak["priceWalBytes"]=max(peak["priceWalBytes"],wal.stat().st_size)
                peak["journalBytes"]=max(peak["journalBytes"],sum(
                    p.stat().st_size for p in parent.rglob("*.sqlite3-journal")
                    if p.is_file()))
                peak["totalScratchBytes"]=max(peak["totalScratchBytes"],sum(
                    p.stat().st_size for p in parent.rglob("*")
                    if p.is_file()))
                stopped.wait(0.005)

        observer=threading.Thread(target=sample,daemon=True)
        observer.start()
        try:
            with patch.object(shards,"PER_SHARD",2):
                _,write_stats=_timed(lambda:[_attempt(source,i) for i in range(5)])
                before=shards.verify(source)
                if before["totalObservedAttempts"]!=5 or before["segments"]!=3:
                    raise ValueError("synthetic_shard_population_failed")
                snapshot,snapshot_stats=_timed(
                    lambda:backup.create_snapshot(source,dest))
                restored_report,restore_stats=_timed(
                    lambda:backup.restore_snapshot(dest,restored))
                if (snapshot["observedAttempts"]!=5
                        or restored_report["observedAttempts"]!=5
                        or shards.verify(source)!=before
                        or shards.verify(restored)!=before):
                    raise ValueError("synthetic_restore_consistency_failed")

                # A *real second SQLite writer* holds the active segment;
                # the attempted scanner must propagate SQLITE_BUSY, never
                # suppress it as a missing data observation.
                busy_db=sqlite3.connect(source/shards._name(3),timeout=0.1)
                try:
                    busy_db.execute("BEGIN IMMEDIATE")
                    try:
                        _attempt(source,5)
                    except sqlite3.OperationalError as exc:
                        if "locked" not in str(exc).lower():
                            raise
                        contention="SQLITE_BUSY_PROPAGATED"
                    else:
                        raise ValueError("concurrent_writer_was_not_blocked")
                finally:
                    busy_db.rollback()
                    busy_db.close()
                if shards.verify(source)!=before:
                    raise ValueError("contention_changed_private_scan_ledger")

                # Deterministic no-space injection, no actual disk filling.
                # Source and sealed evidence must remain unchanged.
                fake=type("SyntheticDisk",(object,),{
                    "total":8*1024**3,"free":1024})()
                with patch.object(storage.shutil,"disk_usage",return_value=fake):
                    try:
                        _attempt(source,5)
                    except ValueError as exc:
                        if str(exc)!="cvd_storage_capacity_preflight_failed":
                            raise
                        insufficient="REJECTED_BEFORE_WRITE"
                    else:
                        raise ValueError("simulated_disk_full_not_blocked")
                if shards.verify(source)!=before:
                    raise ValueError("disk_full_changed_private_scan_ledger")

                # Simulated worker termination exactly between the new shard
                # publication and its first scan INSERT; no slot invented.
                crashed=parent/"interrupted-shard"
                crashed.mkdir(mode=0o700)
                _attempt(crashed,0)
                _attempt(crashed,1)
                with patch.object(shards.scan,"record",side_effect=SystemExit(
                        "synthetic_worker_interrupted")):
                    try:
                        _attempt(crashed,2)
                    except SystemExit:
                        pass
                    else:
                        raise ValueError("synthetic_worker_crash_missing")
                crash_report=shards.verify(crashed)
                if (crash_report["totalObservedAttempts"]!=2
                        or crash_report["segments"]!=2
                        or not crash_report["missingCalendarSlotsRemainUnknown"]):
                    raise ValueError("synthetic_crash_fabricated_attempts")

                journal_modes=set()
                for item in source.glob("scan-*.sqlite3"):
                    with sqlite3.connect(item) as db:
                        journal_modes.add(db.execute("PRAGMA journal_mode").fetchone()[0])
                if journal_modes!={"delete"}:
                    raise ValueError("unexpected_shard_journal_mode")

                source_bytes=_files_bytes(source)
                snapshot_bytes=_files_bytes(dest)
                restored_bytes=_files_bytes(restored)
                envelope=storage.assess(parent,
                        [p for p in source.iterdir() if p.name!=".cvd-shards.lock"],
                        copies=2,max_shard_file_bytes=shards.MAX_SHARD_FILE_BYTES)
        finally:
            stopped.set()
            price_stop.set()
            observer.join(timeout=2)
            price_thread.join(timeout=2)

        if price_thread.is_alive() or price_stats["errors"] or price_stats["writes"]<2:
            raise ValueError("synthetic_price_heartbeat_incomplete")
        with sqlite3.connect(price_db) as check:
            if check.execute("SELECT count(*) FROM heartbeat").fetchone()[0]!=price_stats["writes"]:
                raise ValueError("synthetic_price_heartbeat_inconsistent")

        result={
            "schema":SCHEMA,
            "scope":"DISPOSABLE_SYNTHETIC_ONLY",
            "originalObservedAttempts":5,
            "segments":3,
            "write":write_stats,
            "backup":snapshot_stats,
            "restore":restore_stats,
            "processPeakRssMiB":round(resource.getrusage(
                resource.RUSAGE_SELF).ru_maxrss/1024,2),
            "sampledPeakRssMiB":round(peak["rssKiB"]/1024,2),
            "sampledPeakWalBytes":peak["walBytes"],
            "sampledPeakSyntheticPriceWalBytes":peak["priceWalBytes"],
            "syntheticPriceHeartbeatWrites":price_stats["writes"],
            "syntheticPriceMaxCommitMs":round(price_stats["maxCommitMs"],3),
            "syntheticPriceWriteErrors":price_stats["errors"],
            "syntheticPriceCollectorConcurrentLoad":True,
            "sampledPeakJournalBytes":peak["journalBytes"],
            "sampledPeakScratchBytes":peak["totalScratchBytes"],
            "sampledPeaksAreGuaranteed":False,
            "journalMode":"delete",
            "sourceDirectoryBytes":source_bytes,
            "backupDirectoryBytes":snapshot_bytes,
            "restoredDirectoryBytes":restored_bytes,
            "coexistingBytes":source_bytes+snapshot_bytes+restored_bytes,
            "twoCopyEnvelopeRequiredFreeBytes":envelope["requiredFreeBytes"],
            "twoCopyEnvelopeObservedFreeBytes":envelope["observedFreeBytes"],
            "syntheticWriterContention":contention,
            "simulatedDiskFull":insufficient,
            "syntheticCrashAfterNewShard":"UNKNOWN_PRESERVED_NO_FABRICATED_ATTEMPT",
            "sqliteBackupRestoreIntegrity":"PASS",
            "actualPowerLossRecoveryVerified":False,
            "realPriceCollectorConcurrentLoadMeasured":False,
            "oracleMemoryMeasured":False,
            "oracleFreeVolumeEligibilityVerified":False,
            "oracleBillingVerified":False,
            "hmacKeysIncludedInBackup":False,
            "brokerCallsAdded":0,
            "liveRecorderEnabled":False,
            "realTradingEdgeEstablished":False,
            "deployAuthorized":False,
        }
    print("REMURA_TRACK_B_SHARD_RESOURCES="+json.dumps(
        result,sort_keys=True,separators=(",",":")))
    return result


if __name__=="__main__":
    if len(sys.argv)!=1:
        raise SystemExit("usage: python scripts/shark_cvd_shard_resource_probe.py")
    run()
