#!/usr/bin/env python3
"""Track C4b(d): strictly offline adapter for redacted private diagnostic logs.

No network, server, filesystem, Oracle, providers or secrets. Caller-supplied
metadata and timestamps are NOT independently authenticated. NEVER enables C5.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import re

MODE = "OFFLINE_C4BD_PRIVATE_DIAGNOSTIC_LINES_REDACTED_ONLY"
MAX_LINES = 12
MAX_LINE_BYTES = 180
FRESHNESS = timedelta(minutes=10)
MAX_SKEW = timedelta(minutes=1)
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
ROW = re.compile(
    r"(?P<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,9})?Z) "
    r"(?P<key>VPS_RAM_USATA_PERCENTO|VPS_DISCO_USATO_PERCENTO|BACKUP_SQLITE)="
    r"(?P<value>\d{1,3}(?:\.\d{1,2})?|NON_VERIFICATO_DA_QUESTO_TEST)\Z"
)
NUM = re.compile(r"\d{1,3}(?:\.\d{1,2})?\Z")
PERCENT = frozenset(("VPS_RAM_USATA_PERCENTO", "VPS_DISCO_USATO_PERCENTO"))


def _time(value):
    if type(value) is not str or len(value) > 35 or not value.endswith("Z"):
        raise ValueError("strict_utc_timestamp_required")
    try:
        stamp = datetime.fromisoformat(value[:-1] + "+00:00")
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_utc_timestamp") from exc
    if stamp.utcoffset() != timedelta(0):
        raise ValueError("strict_utc_timestamp_required")
    return stamp.astimezone(timezone.utc)


def _result(state, *, ram=None, disk=None, first=None, last=None,
            backup="UNKNOWN_NO_RESTORE_EVIDENCE", pressure="UNKNOWN"):
    return {
        "schema": "remura-c4bd-historic-logs-v1",
        "state": state,
        "ramUsedPercentObserved": ram,
        "diskUsedPercentObserved": disk,
        "firstLogTimestampUtc": first,
        "lastLogTimestampUtc": last,
        "backupSqliteEvidence": backup,
        "historicPressureClassification": pressure,
        "vpsCurrentHeadroomVerified": False,
        "anyLiveDatabaseSizesVerified": False,
        "offhostBackupAndRestoreVerified": False,
        "oracleBillingVerified": False,
        "githubBillingVerified": False,
        "firestoreBillingVerified": False,
        "sourceLogAuthenticityVerified": False,
        "collectorsChanged": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
        "newVpsRequests": 0,
        "newProviderCalls": 0,
    }


def inspect_redacted_lines(lines, *, run_id, job_id, job_conclusion,
                           checked_at_utc, mode=None):
    """Use only three previously redacted allowlisted output keys from one run."""
    if mode != MODE:
        raise ValueError("explicit_offline_c4bd_mode_required")
    now = _time(checked_at_utc)
    if (type(run_id) is not int or run_id <= 0 or
            type(job_id) is not int or job_id <= 0 or
            type(job_conclusion) is not str or
            job_conclusion not in ("success", "failure", "cancelled", "skipped") or
            type(lines) not in (list, tuple) or len(lines) > MAX_LINES):
        raise ValueError("strict_bounded_existing_run_metadata_required")
    if job_conclusion != "success":
        return _result("UNKNOWN_DIAGNOSTIC_JOB_NOT_SUCCESSFUL")
    if not lines:
        return _result("UNKNOWN_NO_REDACTED_LINES")
    samples = {}
    timestamps = []
    backup_seen = False
    for line in lines:
        if type(line) is not str:
            return _result("UNKNOWN_UNEXPECTED_LOG_CONTENT")
        try:
            if len(line.encode("utf-8")) > MAX_LINE_BYTES:
                return _result("UNKNOWN_UNEXPECTED_LOG_CONTENT")
        except UnicodeError:
            return _result("UNKNOWN_UNEXPECTED_LOG_CONTENT")
        match = ROW.fullmatch(line)
        if match is None:
            return _result("UNKNOWN_UNEXPECTED_LOG_CONTENT")
        key, value = match.group("key"), match.group("value")
        try:
            at = _time(match.group("time"))
        except ValueError:
            return _result("UNKNOWN_INVALID_LOG_CLOCK")
        if at > now:
            return _result("UNKNOWN_FUTURE_LOG_CLOCK")
        timestamps.append(at)
        if key == "BACKUP_SQLITE":
            if value != "NON_VERIFICATO_DA_QUESTO_TEST":
                return _result("UNKNOWN_UNEXPECTED_BACKUP_STATUS")
            backup_seen = True
            continue
        if key in samples or not NUM.fullmatch(value):
            return _result("UNKNOWN_DUPLICATE_OR_MALFORMED_MEASUREMENT")
        try:
            dec = Decimal(value)
        except InvalidOperation:
            return _result("UNKNOWN_INVALID_PERCENT")
        if not Decimal("0") <= dec <= Decimal("100"):
            return _result("UNKNOWN_PERCENT_OUTSIDE_BOUNDS")
        samples[key] = float(dec)
    if not PERCENT.issubset(samples):
        return _result("UNKNOWN_MISSING_RESOURCE_MEASUREMENT")
    if max(timestamps) - min(timestamps) > MAX_SKEW:
        return _result("UNKNOWN_NONCOMPARABLE_TIMESTAMPS")
    first, last = min(timestamps), max(timestamps)
    backup = ("DIAGNOSTIC_SPECIFICALLY_DID_NOT_VERIFY_BACKUP" if backup_seen
              else "UNKNOWN_NO_RESTORE_EVIDENCE")
    ram, disk = samples["VPS_RAM_USATA_PERCENTO"], samples["VPS_DISCO_USATO_PERCENTO"]
    if now - last > FRESHNESS:
        state = "HISTORICAL_PAST_RUN_NOT_CURRENT_VPS_EVIDENCE"
        pressure = ("HISTORICAL_THRESHOLD_EXCEEDED" if max(ram, disk) >= 80
                    else "HISTORICAL_BELOW_THRESHOLD_NOT_CURRENT_PROOF")
    else:
        state = "TIMESTAMP_RECENT_BUT_UNAUTHENTICATED_AND_INCOMPLETE"
        pressure = ("UNATTESTED_THRESHOLD_EXCEEDED" if max(ram, disk) >= 80
                    else "UNATTESTED_BELOW_THRESHOLD_NOT_GO")
    return _result(state, ram=ram, disk=disk,
                   first=first.isoformat(), last=last.isoformat(),
                   backup=backup, pressure=pressure)
