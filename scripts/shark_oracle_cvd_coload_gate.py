#!/usr/bin/env python3
"""REMURA Track B: isolated one-shot CVD co-load gate on a future Linux lab.

NOT a LIVE runner or launcher. Explicit --run only from a trusted checkout
under /tmp, non-root, guarded by shark_oracle_staging_gate.guard_host().
Rehearses existing OFFLINE synthetic price_store.ingest + 2 CVD pilot test
in a disposable subprocess, never touches /opt/remura, OCI APIs, broker,
collector, actual prices, orders, timers, notifications or services.

Host sampled RSS, host memory and child CPU snapshots are NOT proof of 1/8 Oracle CPU entitlement,
unsampled peaks, hypervisor throttle, cross-DB atomicity or zero billing.
This is an engineering experiment, never authority to enable LIVE research.
"""
from __future__ import annotations

import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import shark_oracle_staging_gate as safety
SCHEMA = "remura-track-b-oracle-isolated-cvd-coload-v1"
PREFIX = "REMURA_B_ORACLE_CVD_COLOAD="
CHILD_PREFIX = "REMURA_B_CVD_COLOAD_SYNTHETIC="
MAX_WALL = 45
MAX_REPORT_BYTES = 8192
MAX_CHILD_RSS_MIB = 128
MIN_AVAILABLE_MEMORY_MIB = 192
MIN_TMP_FREE_MIB = 256


def _number(value, minimum=0, maximum=10000):
    return (type(value) in (int, float) and math.isfinite(value)
            and minimum <= value <= maximum)


def _parse_child(stdout):
    """Only allow redacted, internally consistent synthetic benchmark facts."""
    if not isinstance(stdout, str) or len(stdout) > MAX_REPORT_BYTES:
        raise ValueError("synthetic_report_absent_or_unbounded")
    reports = [x[len(CHILD_PREFIX):] for x in stdout.splitlines()
               if x.startswith(CHILD_PREFIX)]
    if len(reports) != 1:
        raise ValueError("synthetic_report_missing_or_duplicated")
    try:
        report = json.loads(reports[0])
    except (ValueError, UnicodeError) as exc:
        raise ValueError("synthetic_report_invalid") from exc
    flags = {
        "schema": "remura-synthetic-dual-db-coload-v1",
        "status": "GITHUB_SYNTHETIC_ONLY_ORACLE_NO_GO",
        "priceMarketsIngested": 34,
        "cvdPilotScans": 2,
        "cvdMarketsNotCovered": 32,
        "syntheticRestoreBothSqlites": True,
        "crossDatabaseAtomicSnapshot": False,
        "realOracleCpuQuotaMeasured": False,
        "realOracleP95P99LockMeasured": False,
        "actualCollectorBrokerRequestsMade": 0,
        "liveIngestInterferenceCertified": False,
        "releaseAuthorized": False,
        "tradingEdgeProven": False,
    }
    if not isinstance(report, dict) or any(
            type(report.get(key)) is not type(value)
            or report[key] != value for key, value in flags.items()):
        raise ValueError("unexpected_synthetic_claims")
    for key in ("jointProcessCpuSeconds", "jointProcessWallSeconds",
                "rssBeforeMiB", "rssAfterMiB"):
        if not _number(report.get(key), 0, 1000):
            raise ValueError("invalid_synthetic_resource_metric")
    if not 0 < report["jointProcessWallSeconds"] <= MAX_WALL:
        raise ValueError("synthetic_worker_wall_time_unacceptable")
    if report["rssAfterMiB"] > MAX_CHILD_RSS_MIB:
        raise ValueError("synthetic_worker_rss_not_safe_for_small_vm")
    return report


def _command():
    """Exact no-network unit suite with both SQLite files under /tmp."""
    return [sys.executable, "-B", "-m", "unittest", "discover",
            "-s", "tests", "-p", "test_shark_cvd_coload_rehearsal.py", "-v"]


def run():
    # Root, /opt/remura, non-/tmp, insufficient memory/disk => no subprocess.
    safety.guard_host()
    # A /tmp checkout on the LIVE Oracle host is still unsafe: reject any
    # production footprint BEFORE launching the synthetic workload.
    if (os.path.lexists("/opt/remura") or
            os.path.lexists("/etc/systemd/system/remura-private.service")):
        raise RuntimeError("live_host_footprint_forbidden")
    if os.environ.get("REMURA_ISOLATED_ORACLE_LAB") != "I_CONFIRM_NO_LIVE":
        raise RuntimeError("explicit_isolated_lab_attestation_required")
    start_free = safety.shutil.disk_usage("/tmp").free
    before_memory = safety.mem_available_kib()
    command = _command()
    child = subprocess.Popen(
        command, cwd=ROOT, stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        env={"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": str(ROOT),
             "LC_ALL": "C", "PATH": "/usr/bin:/bin"},
    )
    rss_max = None
    io_write_max = None
    mem_min = before_memory
    began = time.monotonic()
    try:
        while child.poll() is None:
            if time.monotonic() - began > MAX_WALL:
                raise RuntimeError("oracle_lab_synthetic_time_budget_exceeded")
            rss = safety.rss_kib(child.pid)
            if rss is not None:
                rss_max = rss if rss_max is None else max(rss, rss_max)
            io = safety.proc_io_bytes(child.pid)
            if io is not None:
                io_write_max = io[1] if io_write_max is None else max(io[1], io_write_max)
            available = safety.mem_available_kib()
            if available is not None:
                mem_min = available if mem_min is None else min(mem_min, available)
            time.sleep(0.01)
        stdout, _stderr = child.communicate(timeout=3)
    finally:
        if child.poll() is None:
            child.kill()
            child.communicate(timeout=3)
    if child.returncode != 0:
        # Do NOT echo stderr or any private source, host path or env.
        raise RuntimeError("oracle_lab_synthetic_suite_failed")
    result = _parse_child(stdout)
    if rss_max is None or rss_max/1024 > MAX_CHILD_RSS_MIB:
        raise RuntimeError("oracle_lab_synthetic_rss_unobserved_or_over_budget")
    if mem_min is None or mem_min/1024 < MIN_AVAILABLE_MEMORY_MIB:
        raise RuntimeError("oracle_lab_host_memory_insufficient")
    end_free = safety.shutil.disk_usage("/tmp").free
    if min(start_free, end_free) < MIN_TMP_FREE_MIB * 1024**2:
        raise RuntimeError("oracle_lab_staging_disk_insufficient")
    output = {
        "schema": SCHEMA,
        "status": "ISOLATED_SYNTHETIC_HOST_REHEARSAL_REVIEW_ONLY",
        "originalCollectorDataUsed": False,
        "marketDataSynthetic": True,
        "priceMarkets": 34, "cvdPilotMarkets": 2,
        "cvdMarketsOutsidePilot": 32,
        "sameOriginalHmacTestPass": True,
        "privateTwoSqliteRestoreTestPass": True,
        "crossDatabaseAtomicCommit": False,
        "measuredSampledChildPeakRssMiB": round(rss_max/1024, 2),
        "measuredSampledChildWriteMiB": (
            round(io_write_max/1048576, 3) if io_write_max is not None else None),
        "measuredMinHostAvailableMiB": round(mem_min/1024, 2),
        "measuredChildCpuSeconds": result["jointProcessCpuSeconds"],
        "measuredChildConcurrentWallSeconds": result["jointProcessWallSeconds"],
        "peakRSSBetweenSamplesMissedPossible": True,
        "oracleHypervisorCpuThrottlingMeasured": False,
        "actualCollectorCoexistenceMeasured": False,
        "actualOracleBillingCertified": False,
        "newBrokerCalls": 0,
        "productionDatabaseOrServiceTouched": False,
        "cvdEnabledOnLive": False,
        "releaseAuthorized": False,
        "institutionalEdgeEstablished": False,
    }
    print(PREFIX + json.dumps(output, sort_keys=True, separators=(",", ":")))


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args == ["--self-check"]:
        sample = {
            "schema":"remura-synthetic-dual-db-coload-v1",
            "status":"GITHUB_SYNTHETIC_ONLY_ORACLE_NO_GO",
            "priceMarketsIngested":34, "cvdPilotScans":2,
            "cvdMarketsNotCovered":32,"syntheticRestoreBothSqlites":True,
            "crossDatabaseAtomicSnapshot":False,
            "realOracleCpuQuotaMeasured":False,
            "realOracleP95P99LockMeasured":False,
            "actualCollectorBrokerRequestsMade":0,
            "liveIngestInterferenceCertified":False,"releaseAuthorized":False,
            "tradingEdgeProven":False,
            "jointProcessCpuSeconds":0.1,"jointProcessWallSeconds":0.2,
            "rssBeforeMiB":35.0,"rssAfterMiB":36.0,
        }
        assert _parse_child(CHILD_PREFIX + json.dumps(sample)) == sample
        print("REMURA_B_ORACLE_CVD_COLOAD_SELF_CHECK=PASS")
        return 0
    if args == ["--run"]:
        run()
        return 0
    print("usage: python -B scripts/shark_oracle_cvd_coload_gate.py --self-check|--run")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
