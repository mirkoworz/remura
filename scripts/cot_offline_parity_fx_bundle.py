#!/usr/bin/env python3
"""REMURA Filone B v21.2 LAB: one-shot OFFLINE CFTC parity -> FX dashboard.
Never fetches CFTC/network, writes a DB, accesses collectors, or activates trading.
The caller must supply two existing local JSON snapshots. Output contains ONLY
descriptive PUBLIC futures aggregates, plus private timestamp COVERAGE COUNTS.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

from cot_intelligence_parity import read_local, reconcile

SCHEMA = "remura-cot-offline-parity-fx-bundle-v1"
VERSION = "B_V21_2_LAB"
NODE_EXPORT = Path(__file__).with_name("cot_fx_dashboard_export.js")


def assemble(public_path: Path, private_path: Path, dates: list[str],
             now_utc: str, *, runner=subprocess.run) -> dict:
    """Require the existing strict parity to pass BEFORE calculating 7 factors."""
    public = read_local(public_path)
    private = read_local(private_path)
    parity = reconcile(public, private, dates, now_utc)
    coverage = parity["coverage"]
    observed = sum(x["capture_known"] for x in coverage)
    unknown = sum(x["capture_unknown"] for x in coverage)
    keys = sum(x["expected"] for x in coverage)
    result = {
        "schema": SCHEMA,
        "version": VERSION,
        "asOfUtc": parity["nowUtc"],
        "publicReadAtUtc": parity["publicReadAtUtc"],
        "reportDates": parity["reportDates"],
        "parityState": parity["state"],
        "verifiedValuePairs": parity["matchedKeys"],
        "expectedValuePairs": parity["expectedKeys"],
        "privateFirstSeenKnownMatchedPairs": observed,
        "privateFirstSeenUnknownMatchedPairs": unknown,
        "privateFirstSeenCoverageState":
            "all_matched_pairs_timestamped" if observed == keys
            else "incomplete_or_unknown",
        "privateFirstSeenIsOfficialPublication": False,
        "historicalDataAvailabilityIndependentlyVerified": False,
        "futurePricesOrPerformanceVerified": False,
        "institutionalLiveFlowClaimed": False,
        "dashboard": None,
    }
    if parity["state"] != "value_parity_only":
        result["state"] = "BLOCKED_PUBLIC_PRIVATE_PARITY_NOT_CLEAN"
        return result
    # No shell, no network, no writing, no human-input command construction.
    # Existing, validated public JSON is the only data input of JS exporter.
    cmd = ["node", str(NODE_EXPORT.resolve()), "--snapshot",
           str(Path(public_path).expanduser().resolve(strict=True)),
           "--now-utc", now_utc]
    completed = runner(cmd, capture_output=True, text=True, timeout=10,
                       check=True)
    dashboard = json.loads(completed.stdout)
    if (dashboard.get("schema") != "remura-cot-dashboard-fx-v1" or
        dashboard.get("state") != "descriptive_ready" or
        dashboard.get("mode") != "descriptive_only" or
        dashboard.get("latestCftcReportDate") != parity["reportDates"][1] or
        dashboard.get("previousCftcReportDate") != parity["reportDates"][0] or
        dashboard.get("underlyingCount") != 7 or
        dashboard.get("overlappingFxCrossCount") != 28 or
        len(dashboard.get("factors", [])) != 7 or
        len(dashboard.get("crosses", [])) != 28):
        result["state"] = "BLOCKED_DASHBOARD_PERIOD_OR_COVERAGE"
        return result
    # Critical: no private rows, price history, broker/collector identifiers.
    result["dashboard"] = dashboard
    result["state"] = "DESCRIPTIVE_PUBLIC_FACTORS_PRIVATE_VALUES_MATCH"
    return result


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--public", type=Path)
    p.add_argument("--private", type=Path)
    p.add_argument("--report-dates")
    p.add_argument("--now-utc")
    args = p.parse_args()
    if all(x is None for x in (args.public, args.private,
                                args.report_dates, args.now_utc)):
        print(json.dumps({"schema": SCHEMA, "version": VERSION,
                          "state": "NO_OFFLINE_INPUTS_NO_REAL_FACTORS",
                          "dashboard": None, "networkCalls": 0,
                          "writes": 0}, sort_keys=True))
        return
    if not all((args.public, args.private, args.report_dates, args.now_utc)):
        p.error("Both existing offline snapshots and both explicit clocks required")
    try:
        report = assemble(args.public, args.private,
                          args.report_dates.split(","), args.now_utc)
    except (ValueError, OSError, TypeError, KeyError, json.JSONDecodeError,
            subprocess.SubprocessError) as exc:
        p.error("Read-only provenance/parity export rejected (" +
                type(exc).__name__ + "); private detail withheld")
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True,
                     allow_nan=False))


if __name__ == "__main__":
    main()
