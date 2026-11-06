#!/usr/bin/env python3
"""REMURA Track B P0b: OFFLINE comparison of passively observed batches.

This does NOT sample Oracle, connect to cTrader, access SQLite, trade, or
enable CVD. It only accepts operator-supplied, unsigned aggregate JSON from
the already-tested one-shot passive observer. No raw evidence is persisted.
A large enough descriptive sample is NEVER a statistical trading edge or
permission to add production load.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import math
import sys

SCHEMA = "remura-track-b-p0b-passive-census-v1"
INPUT_SCHEMA = "remura-track-b-p0b-passive-natural-batch-v1"
MAX_REPORTS = 32
MAX_INPUT_BYTES = 65536
ENGINEERING_TARGET = 8  # internal coverage goal, NOT a statistical threshold


def _number(record, key, upper):
    value = record.get(key)
    if (type(value) not in (float, int) or
            not math.isfinite(value) or not 0 <= value <= upper):
        raise ValueError("invalid_aggregate_metric")
    return float(value)


def _utc(value):
    if type(value) is not str or len(value) != 20 or not value.endswith("Z"):
        raise ValueError("invalid_target_utc")
    try:
        moment = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc)
    except ValueError:
        raise ValueError("invalid_target_utc") from None
    if (moment.minute not in (1, 16, 31, 46) or
            moment.second != 30 or moment.microsecond):
        raise ValueError("not_a_natural_m15_target")
    return moment


def _validate(report):
    """Allowlist all used fields; never serialize untrusted unknown fields."""
    if type(report) is not dict or report.get("schema") != INPUT_SCHEMA:
        raise ValueError("invalid_input_schema")
    expected = {
        "status":"NATURAL_INGEST_BASELINE_OBSERVED",
        "windowSeconds":85,
        "samples":18,
        "sampleIntervalSeconds":5,
        "collectorRecordAdvancedInWindow":True,
        "servicePidUnchanged":True,
        "onlySampledMaximaNotActualPeaks":True,
        "oracleCpuEntitlementMeasured":False,
        "realCvdCollectorCoLoadTested":False,
        "oracleBillingVerified":False,
        "cvdResearchMayBeEnabled":False,
        "additionalBrokerCalls":0,
        "localReadOnlyStatusGets":2,
        "writesOrServiceChanges":False,
    }
    if any(type(report.get(k)) is not type(v) or report[k] != v
           for k, v in expected.items()):
        raise ValueError("unsupported_or_unsafe_observation")
    t = _utc(report.get("targetUtc"))
    metrics = {
        "cpuPct":_number(report, "serviceCpuPctOfOneFullCore", 1000),
        "cpuMs":_number(report, "serviceCpuDuringWindowMs", 1000000),
        "serviceMemMiB":_number(report, "maxSampledServiceMemMiB", 8192),
        "hostAvailableMiB":_number(report, "minSampledHostAvailableMiB", 8192),
        "cpuPsiMs":_number(report, "cpuPsiSomeTotalDeltaMs", 1000000),
        "ioPsiMs":_number(report, "ioPsiSomeTotalDeltaMs", 1000000),
        "memoryPsiMs":_number(report, "memoryPsiSomeTotalDeltaMs", 1000000),
    }
    # Check internal CPU agreement to within output rounding.
    if abs(metrics["cpuPct"]-metrics["cpuMs"]/(85*10)) > 0.001:
        raise ValueError("inconsistent_cpu_units")
    return t, metrics


def summarize(reports):
    """Pure coverage audit. Operator-supplied numbers are NOT authenticated."""
    if type(reports) is not list or not 1 <= len(reports) <= MAX_REPORTS:
        raise ValueError("invalid_observation_count")
    observations = [_validate(item) for item in reports]
    times = [t for t, _ in observations]
    if len(set(times)) != len(times):
        raise ValueError("duplicate_natural_batch")
    observations.sort(key=lambda item:item[0])
    start, end = observations[0][0], observations[-1][0]
    utc_days = len({x[0].date() for x in observations})
    utc_hours = len({x[0].hour for x in observations})
    sessions = len({x[0].hour // 6 for x in observations})
    diversified = (len(observations) >= ENGINEERING_TARGET
                   and utc_days >= 2 and utc_hours >= 3 and sessions >= 2)
    m = [p for _, p in observations]
    # No claim about unsampled peaks, external CPU entitlement or broker
    # performance regressions. Host PSI is NOT service-only PSI.
    return {
        "schema":SCHEMA,
        "status":("MULTI_WINDOW_BASELINE_COVERAGE_OBSERVED_NOT_CVD_GO"
                  if diversified else "BASELINE_COVERAGE_INCOMPLETE"),
        "sourceProvenanceVerified":False,
        "inputType":"OPERATOR_SUPPLIED_UNSIGNED_AGGREGATES",
        "windows":len(observations),
        "engineeringTargetWindows":ENGINEERING_TARGET,
        "differentUtcDates":utc_days,
        "differentUtcHours":utc_hours,
        "differentSixHourUtcBands":sessions,
        "firstTargetUtc":start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "lastTargetUtc":end.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "maxMeanServiceCpuPctOfOneCore":round(max(v["cpuPct"] for v in m),4),
        "maxServiceCpuWindowMs":round(max(v["cpuMs"] for v in m),3),
        "maxSampledServiceMemMiB":round(max(v["serviceMemMiB"] for v in m),2),
        "minSampledHostAvailableMiB":round(min(v["hostAvailableMiB"] for v in m),2),
        "maxWindowHostCpuPsiSomeDeltaMs":round(max(v["cpuPsiMs"] for v in m),3),
        "maxWindowHostIoPsiSomeDeltaMs":round(max(v["ioPsiMs"] for v in m),3),
        "maxWindowHostMemoryPsiSomeDeltaMs":round(
            max(v["memoryPsiMs"] for v in m),3),
        "peakCpuQuotaUtilizationMeasured":False,
        "realCvdCollectorCoLoadTested":False,
        "priceIngestLatencyRegressionMeasured":False,
        "oracleFreeTierBillingVerified":False,
        "cvdResearchMayBeEnabled":False,
        "statisticalTradingEdgeEstablished":False,
        "noNewBrokerCallsOrWritesFromThisComparator":True,
    }


def main(argv=None):
    args=sys.argv[1:] if argv is None else argv
    if args == ["--self-check"]:
        print("REMURA_P0B_CENSUS_SELF_CHECK=PASS")
        return 0
    if args != ["--audit-stdin"]:
        print("usage: python3 -B scripts/shark_p0b_window_census.py --self-check|--audit-stdin")
        return 2
    try:
        raw=sys.stdin.buffer.read(MAX_INPUT_BYTES+1)
        if not raw or len(raw)>MAX_INPUT_BYTES:
            raise ValueError("invalid_input_size")
        records=json.loads(raw.decode("utf-8"))
        result=summarize(records)
    except (ValueError, TypeError, UnicodeError, OverflowError):
        print("REMURA_P0B_CENSUS=NO_GO_INVALID_OR_UNVERIFIED_INPUT")
        return 2
    print("REMURA_P0B_CENSUS="+json.dumps(
        result,sort_keys=True,separators=(",",":")))
    # Incomplete observational coverage still is a valid audit result, NOT
    # an authorization to load Oracle or enable CVD.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
