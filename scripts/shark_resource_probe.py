#!/usr/bin/env python3
"""REMURA Track B disposable GitHub-runner RSS/WAL/SQLite lock budget.

SYNTHETIC TEST TOOL ONLY. Never opens production data. Parent constructs
34 markets x 4000 closed M15 bars and H1/H4 from the existing test fixture,
then starts two CLEAN Python subprocesses on separate SQLite copies.
No network, cTrader GET, secrets, orders, alerts, scheduled work, or VPS.

The runner's resident memory, time, disk and SQLite lock time are NOT
measurements or cost assurances for the 0.93 GiB Oracle Always Free machine.
"""
from __future__ import annotations

from datetime import timedelta
import json
import os
from pathlib import Path
import resource
import sqlite3
import subprocess
import sys
import tempfile
import time
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
# Running as 'python scripts/foo.py' does not reliably include the repo root
# for the 'from scripts import ...' research namespace used by existing tests.
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/"scripts"))
sys.path.insert(0,str(ROOT/"tests"))

import signals_monitor as live
from scripts import shark_cot_asof_witness as witness
from test_shark_staging_scan import fixture, clone, NOW

SCHEMA="remura-track-b-offline-rss-budget-v1"
PREFIX="REMURA_TRACK_B_RSS_WAL_PROBE="


def _vm_rss_kib():
    # Linux procfs is available on the GitHub-hosted Ubuntu test runner.
    try:
        with open("/proc/self/status",encoding="ascii") as file:
            for line in file:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except (OSError,ValueError,IndexError):
        pass
    return None


def _file_bytes(path):
    try:
        return os.stat(path).st_size
    except FileNotFoundError:
        return 0


def worker(mode,path):
    if mode not in ("standard","compact"):
        raise ValueError("only_synthetic_modes")
    database=Path(path).resolve()
    if database.name not in ("legacy.sqlite","compact.sqlite"):
        raise ValueError("unexpected_synthetic_database")
    rss_before=_vm_rss_kib()
    t0=time.perf_counter()
    cpu0=time.process_time()
    if mode=="compact":
        with patch.object(witness,"_clock",return_value=NOW+timedelta(seconds=2)):
            result=live.scan_once_with_compact_price_only_research(database,NOW)
    else:
        result=live.scan_once(database,NOW)
    elapsed=time.perf_counter()-t0
    cpu=time.process_time()-cpu0
    rss_after=_vm_rss_kib()
    maxrss=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    with sqlite3.connect(database) as db:
        page_count=db.execute("PRAGMA page_count").fetchone()[0]
        page_size=db.execute("PRAGMA page_size").fetchone()[0]
        mode_actual=db.execute("PRAGMA journal_mode").fetchone()[0]
        if mode=="compact":
            from scripts import shark_price_only_compact as compact
            summary=compact.summary(db)
            if summary["fullScanDenominator"]!=34:
                raise ValueError("compacted_full_denominator_missing")
    report={
        "schema":SCHEMA,"mode":mode,
        "markets":34,"m15BarsPerMarket":4000,
        "elapsedSeconds":round(elapsed,3),
        "cpuSeconds":round(cpu,3),
        "rssBeforeMiB":round(rss_before/1024,2) if rss_before is not None else None,
        "rssAfterMiB":round(rss_after/1024,2) if rss_after is not None else None,
        "processPeakRssMiB":round(maxrss/1024,2),
        "dbAllocatedMiB":round(page_count*page_size/1048576,3),
        "sqliteJournalMode":mode_actual,
        "walFileBytesAfter":_file_bytes(str(database)+"-wal"),
        "shmFileBytesAfter":_file_bytes(str(database)+"-shm"),
        "sqliteWriterLockMs":(result.get("priceOnlyResearch",{})
                              .get("sqliteWriterLockMs")),
        "squalincomeExamined":result["examined"],
        "newBrokerCalls":0,
        "rssMeasuredOnOracle":False,
        "oracleBillingVerified":False,
        "returnsOrEdgeProven":False,
    }
    if mode=="compact" and (report["sqliteWriterLockMs"] is None
                            or report["sqliteWriterLockMs"]<=0):
        raise ValueError("missing_lock_measurement")
    if (report["processPeakRssMiB"]>=850 or
            elapsed>=60 or mode_actual.lower()!="wal"):
        raise ValueError("runner_budget_gate_exceeded")
    print(PREFIX+json.dumps(report,sort_keys=True,separators=(",",":")))


def parent():
    with tempfile.TemporaryDirectory(prefix="remura-research-rss-") as folder:
        root=Path(folder)
        seed=root/"seed.sqlite"
        fixture(seed,with_cot=False,all_priced=True,m15_count=4000)
        for mode in ("standard","compact"):
            filename=root/("legacy.sqlite" if mode=="standard" else "compact.sqlite")
            clone(seed,filename)
            done=subprocess.run([sys.executable,str(Path(__file__).resolve()),
                                 "--worker",mode,str(filename)],
                                cwd=str(ROOT),capture_output=True,text=True,
                                timeout=95,check=False)
            if done.returncode:
                # Do not echo private or uncontrolled runner output.
                raise RuntimeError("synthetic_resource_probe_failed_"+mode+
                                   "_exit_"+str(done.returncode))
            matching=[line for line in done.stdout.splitlines()
                      if line.startswith(PREFIX)]
            if len(matching)!=1:
                raise RuntimeError("synthetic_resource_probe_output_missing_"+mode)
            parsed=json.loads(matching[0][len(PREFIX):])
            if parsed.get("mode")!=mode or parsed.get("markets")!=34:
                raise ValueError("synthetic_probe_identity_mismatch")
            print(matching[0])
    print("REMURA_TRACK_B_RSS_WAL_PROBE_COMPLETED=TRUE")


if __name__=="__main__":
    if len(sys.argv)==1:
        parent()
    elif len(sys.argv)==4 and sys.argv[1]=="--worker":
        worker(sys.argv[2],sys.argv[3])
    else:
        raise SystemExit("usage: python scripts/shark_resource_probe.py")
