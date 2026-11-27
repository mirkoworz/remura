#!/usr/bin/env python3
"""REMURA C4b(a): offline resource/SQLite evidence evaluation, NOT a VPS check.

Only pre-sanitized snapshots from the existing /private-api/resources schema
are accepted; this module does not fetch/collect, open files, inspect the OS,
store values, or touch credentials. Test fixtures are synthetic, never LIVE.
No supplied snapshot authenticates OCI billing, provider publication, backup
restore, or research process isolation. Output NEVER authorizes research ON.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

MODE = "OFFLINE_C4B_REDACTED_CAPACITY_EVIDENCE_ONLY"
SOURCE_SCHEMA = "remura-resources-v1"
UTC = timezone.utc
MAX_SAMPLES = 8
MAX_AGE = timedelta(minutes=5)
MAX_WINDOW = timedelta(minutes=30)
MAX_BYTES = 2**63 - 1
ALERT_PERCENT = 80
MIN_DISK_HEADROOM_BYTES = 512 * 1024**2
FILE_KEYS = frozenset(("coreDbBytes", "coreWalBytes", "coreShmBytes",
                       "researchDbBytes", "researchWalBytes", "researchShmBytes",
                       "backupBytes"))
FIELDS = frozenset(("schema", "sampledAt", "memory", "cpu", "disk",
                    "uptimeSeconds"))


def _clock(value):
    if type(value) is not str or not 20 <= len(value) <= 35:
        raise ValueError("utc_timestamp_required")
    if not (value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("utc_offset_zero_required")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("utc_offset_zero_required")
    return stamp.astimezone(UTC)


def _integer(value, *, positive=False):
    if type(value) is not int or not (0 < value <= MAX_BYTES if positive
                                      else 0 <= value <= MAX_BYTES):
        raise ValueError("bounded_integer_required")
    return value


def _ratio(n, d):
    return round(n * 100 / d, 2)


def _snapshot(item, now):
    if type(item) is not dict or set(item) != FIELDS or item["schema"] != SOURCE_SCHEMA:
        raise ValueError("sanitized_resource_adapter_required")
    sampled = _clock(item["sampledAt"])
    if sampled > now:
        raise ValueError("future_sample_not_evidence")
    if type(item["memory"]) is not dict or set(item["memory"]) != {
            "total", "used", "swapTotal", "swapUsed"}:
        raise ValueError("invalid_memory_fields")
    if type(item["disk"]) is not dict or set(item["disk"]) != {"total", "used"}:
        raise ValueError("invalid_disk_fields")
    if type(item["cpu"]) is not dict or set(item["cpu"]) != {"logical", "load1"}:
        raise ValueError("invalid_cpu_fields")
    mem, disk, cpu = item["memory"], item["disk"], item["cpu"]
    ram_total = _integer(mem["total"], positive=True)
    ram_used = _integer(mem["used"])
    swap_total = _integer(mem["swapTotal"])
    swap_used = _integer(mem["swapUsed"])
    disk_total = _integer(disk["total"], positive=True)
    disk_used = _integer(disk["used"])
    logical = _integer(cpu["logical"], positive=True)
    uptime = _integer(item["uptimeSeconds"])
    if (ram_used > ram_total or swap_used > swap_total or
            disk_used > disk_total or logical > 256):
        raise ValueError("inconsistent_resource_counters")
    load = cpu["load1"]
    if (type(load) not in (float, int) or not math.isfinite(load)
            or load < 0 or load > 10000):
        raise ValueError("invalid_one_minute_load")
    return {"at": sampled, "uptime": uptime,
            "ramPct": _ratio(ram_used, ram_total),
            "diskPct": _ratio(disk_used, disk_total),
            "diskFreeBytes": disk_total - disk_used,
            "swapUsedBytes": swap_used,
            # Load average / logical CPUs is a LOAD PROXY, not CPU usage %,
            # not OCI OCPU and not a performance guarantee.
            "loadPerLogical": round(load / logical, 3)}


def _files(manifest, now):
    if manifest is None:
        return {"state": "UNKNOWN_NO_SQLITE_WAL_INVENTORY",
                "bytes": None}
    if type(manifest) is not dict or set(manifest) != FILE_KEYS | {"sampledAt"}:
        return {"state": "UNKNOWN_INVALID_SQLITE_WAL_INVENTORY",
                "bytes": None}
    try:
        captured = _clock(manifest["sampledAt"])
        if captured > now or now - captured > MAX_AGE:
            raise ValueError("missing_fresh_manifest")
        values = [_integer(manifest[k]) for k in FILE_KEYS]
        total = sum(values)
        if total > MAX_BYTES:
            raise ValueError("overflow")
    except (ValueError, TypeError, OverflowError):
        return {"state": "UNKNOWN_INVALID_OR_STALE_SQLITE_WAL_INVENTORY",
                "bytes": None}
    return {"state": "SUPPLIED_UNATTESTED_FILE_SIZE_COUNTERS_ONLY",
            "bytes": total}


def evaluate(snapshots, *, observed_at, file_manifest=None, mode=None):
    """Fail closed. No file paths, account IDs, source payloads or orders.

    A good-looking synthetic resource snapshot is NEVER a GO decision.
    Even real samples would not prove backup restore, billing or continuity.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_c4b_mode_required")
    now = _clock(observed_at)
    if type(snapshots) not in (list, tuple) or len(snapshots) > MAX_SAMPLES:
        raise ValueError("bounded_sanitized_samples_only")
    results = []
    invalid = 0
    stale = 0
    for item in snapshots:
        try:
            value = _snapshot(item, now)
            if now - value["at"] > MAX_AGE:
                stale += 1
            else:
                results.append(value)
        except (ValueError, TypeError, KeyError, OverflowError):
            invalid += 1
    # Uptime can be rounded seconds or reboot; negative deltas mean restart.
    monotonic = all(
        a["at"] < b["at"] and 0 <= b["uptime"] - a["uptime"] and
        abs((b["uptime"] - a["uptime"]) - (b["at"] - a["at"]).total_seconds()) <= 60
        for a, b in zip(results, results[1:]))
    if len(results) >= 2 and results[-1]["at"] - results[0]["at"] > MAX_WINDOW:
        monotonic = False
    file_check = _files(file_manifest, now)
    if invalid:
        state = "UNKNOWN_INVALID_SAMPLE"
    elif stale:
        state = "UNKNOWN_STALE_SAMPLE"
    elif not results:
        state = "UNKNOWN_NO_RUNTIME_SAMPLE"
    elif not monotonic:
        state = "UNKNOWN_CLOCK_OR_RESTART"
    elif len(results) < 2:
        state = "SINGLE_SAMPLE_NO_CONTINUITY_PROOF"
    else:
        state = "MULTIPLE_SAMPLES_UNATTESTED_RUNTIME"
    ram = max((r["ramPct"] for r in results), default=None)
    disk = max((r["diskPct"] for r in results), default=None)
    swap = max((r["swapUsedBytes"] for r in results), default=None)
    load = max((r["loadPerLogical"] for r in results), default=None)
    free = min((r["diskFreeBytes"] for r in results), default=None)
    # Tri-state; unknown never maps to the safe state.
    if state.startswith("UNKNOWN"):
        pressure = "UNKNOWN"
    elif (ram >= ALERT_PERCENT or disk >= ALERT_PERCENT or
          free < MIN_DISK_HEADROOM_BYTES or
          load >= 0.8 or swap > 0):
        pressure = "RESEARCH_PRESSURE_ALERT"
    else:
        pressure = "ONLY_SAMPLED_RESOURCE_HEADROOM_NOT_A_GO"
    return {
        "schema": "remura-c4b-offline-resource-check-v1",
        "state": state, "pressure": pressure,
        "validFreshSamples": len(results),
        "staleSamples": stale, "invalidSamples": invalid,
        "maxRamUsedPct": ram, "maxDiskUsedPct": disk,
        "minDiskFreeBytes": free, "maxSwapUsedBytes": swap,
        "maxLoad1PerLogicalCpu": load,
        "cpuLoadIsUsagePercent": False,
        "sqliteWalInventory": file_check["state"],
        "sqliteWalBackupSuppliedBytes": file_check["bytes"],
        "operationalDecision": "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION",
        "oracleBillingVerified": False, "firestoreBillingVerified": False,
        "githubUsageBillingVerified": False, "backupRestoreTestVerified": False,
        "coreSurvivalOnLiveVerified": False, "realFirstSeenVerified": False,
        "sourceAttestation": "UNVERIFIED_EXTERNAL_INPUT_NOT_LIVE_PROOF",
        "newProviderCalls": 0,
    }
