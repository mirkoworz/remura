#!/usr/bin/env python3
"""REMURA Track C4b(e): offline comparisons of already-redacted historic VPS runs.

Caller supplies strictly bounded metadata and metrics that were manually
read from *existing* private GitHub workflow logs. There is NO GitHub fetch,
server read, network, filesystem, broker, process creation or deploy here.
The input and its origin cannot be authenticated by this parser; 'success'
and 256 retained batch rows never prove 8 slots, per-symbol commits, costs,
backup integrity, source freshness or readiness for C5.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

MODE = "OFFLINE_C4BE_HISTORIC_THREE_RUN_COMPARISON_ONLY"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
MAX_RUNS = 8
MAX_RETAINED_ROWS = 256
MAX_BATCH_SYMBOLS = 8
MAX_DURATION_MS = 7_200_000
MAX_TIME_GAP = timedelta(minutes=30)
FIELDS = {"runId", "jobId", "jobConclusion", "sampleAtUtc",
          "ramUsedPercent", "diskUsedPercent", "backupStatus",
          "timingState", "timingRows", "timingPlanned",
          "timingSaved", "timingMedianMs", "timingMaximumMs",
          "lastIngestUtc"}


def _clock(value):
    if type(value) is not str or not 20 <= len(value) <= 35:
        raise ValueError("strict_utc_timestamp_required")
    if not (value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("strict_utc_timestamp_required")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    if t.utcoffset() != timedelta(0):
        raise ValueError("strict_utc_timestamp_required")
    return t.astimezone(timezone.utc)


def _integer(x, *, minimum, maximum):
    if type(x) is not int or x < minimum or x > maximum:
        raise ValueError("bounded_integer_required")
    return x


def _percent(x):
    if type(x) not in (int, float) or not math.isfinite(x) or x < 0 or x > 100:
        raise ValueError("bounded_percent_required")
    return round(x, 2)


def _one(r, now):
    if type(r) is not dict or set(r) != FIELDS:
        raise ValueError("strict_redacted_summary_fields_required")
    rid = _integer(r["runId"], minimum=1, maximum=2**63 - 1)
    jid = _integer(r["jobId"], minimum=1, maximum=2**63 - 1)
    if r["jobConclusion"] != "success":
        raise ValueError("job_did_not_succeed")
    at, ingest = _clock(r["sampleAtUtc"]), _clock(r["lastIngestUtc"])
    if at > now or ingest > at or at - ingest > MAX_TIME_GAP:
        raise ValueError("future_or_noncomparable_ingest_clock")
    ram, disk = _percent(r["ramUsedPercent"]), _percent(r["diskUsedPercent"])
    if r["backupStatus"] != "NON_VERIFICATO_DA_QUESTO_TEST":
        raise ValueError("backup_status_is_not_a_certificate")
    if r["timingState"] != "PRONTA":
        raise ValueError("timing_not_ready_as_reported")
    n = _integer(r["timingRows"], minimum=1, maximum=MAX_RETAINED_ROWS)
    planned = _integer(r["timingPlanned"], minimum=1,
                       maximum=MAX_RETAINED_ROWS * MAX_BATCH_SYMBOLS)
    saved = _integer(r["timingSaved"], minimum=0, maximum=planned)
    if planned < n or planned > n * MAX_BATCH_SYMBOLS:
        raise ValueError("inconsistent_bounded_batch_counters")
    median = _integer(r["timingMedianMs"], minimum=0, maximum=MAX_DURATION_MS)
    max_ms = _integer(r["timingMaximumMs"], minimum=median,
                      maximum=MAX_DURATION_MS)
    return {"run": rid, "job": jid, "at": at, "ram": ram, "disk": disk,
            "rows": n, "planned": planned, "saved": saved,
            "median": median, "max": max_ms, "ingest": ingest}


def summarize(submitted, *, observed_at_utc, mode=None):
    """Return historical trend only; fail closed, do not echo original payload."""
    if mode != MODE:
        raise ValueError("explicit_offline_c4be_mode_required")
    now = _clock(observed_at_utc)
    if type(submitted) not in (tuple, list) or len(submitted) > MAX_RUNS:
        raise ValueError("bounded_historical_records_required")
    if not submitted:
        return _result("UNKNOWN_NO_HISTORICAL_RUNS")
    rows = []
    try:
        rows = [_one(r, now) for r in submitted]
        if len({r["run"] for r in rows}) != len(rows) or \
                len({r["job"] for r in rows}) != len(rows):
            raise ValueError("duplicate_job_or_run")
        if any(a["at"] >= b["at"] for a, b in zip(rows, rows[1:])):
            raise ValueError("non_monotonic_original_runs")
    except (ValueError, TypeError, OverflowError, KeyError):
        return _result("UNKNOWN_INVALID_OR_CONFLICTING_HISTORICAL_RUNS")
    return _result(
        "HISTORICAL_UNATTESTED_COMPARISON_ONLY",
        runs=len(rows),
        first=rows[0]["at"].isoformat(),
        latest=rows[-1]["at"].isoformat(),
        max_ram=max(r["ram"] for r in rows),
        max_disk=max(r["disk"] for r in rows),
        min_ram=min(r["ram"] for r in rows),
        min_disk=min(r["disk"] for r in rows),
        last_row_count=rows[-1]["rows"],
        window_at_cap=any(r["rows"] == MAX_RETAINED_ROWS for r in rows),
        last_saved=rows[-1]["saved"],
        last_planned=rows[-1]["planned"],
        max_median_ms=max(r["median"] for r in rows),
        max_reported_duration_ms=max(r["max"] for r in rows),
        last_age_seconds=int((now - rows[-1]["at"]).total_seconds()),
    )


def _result(state, *, runs=0, first=None, latest=None,
            max_ram=None, max_disk=None, min_ram=None, min_disk=None,
            last_row_count=None, window_at_cap=None,
            last_saved=None, last_planned=None,
            max_median_ms=None, max_reported_duration_ms=None,
            last_age_seconds=None):
    return {
        "schema": "remura-c4be-existing-runs-v1", "state": state,
        "historicalSuccessfulRunsCompared": runs,
        "earliestSampleAtUtc": first, "latestSampleAtUtc": latest,
        "historicalMaximumRamUsedPct": max_ram,
        "historicalMaximumDiskUsedPct": max_disk,
        "historicalMinimumRamUsedPct": min_ram,
        "historicalMinimumDiskUsedPct": min_disk,
        "latestRetainedBatchRows": last_row_count,
        "anyRetainedWindowAtCap256": window_at_cap,
        "latestPlannedSymbolsInRetainedRows": last_planned,
        "latestSavedSymbolsInRetainedRows": last_saved,
        "historicalMaxMedianIngestReturnMs": max_median_ms,
        "historicalMaxReportedIngestReturnMs": max_reported_duration_ms,
        "lastLogAgeSeconds": last_age_seconds,
        "completeBatchScheduleVerified": False,
        "eightDistinctBatchSlotsVerified": False,
        "perSymbolCommitProven": False,
        "currentVpsCapacityVerified": False,
        "currentSqliteWalInventoryVerified": False,
        "offhostBackupRestoreVerified": False,
        "billFreeVerified": False,
        "sourceAuthenticityVerified": False,
        "operationalDecision": NO_GO,
        "newProviderCalls": 0, "newVpsRequests": 0,
    }
