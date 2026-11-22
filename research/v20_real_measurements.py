#!/usr/bin/env python3
"""REMURA V20 real file cadence audit; no network, provider calls or secrets.

Reads existing JSON records only. Private feed, when supplied, is summarized
without leaking individual symbol values or input paths in JSON output.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import median


def parse_utc(text: str) -> datetime:
    if not isinstance(text, str) or not text.endswith("Z"):
        raise ValueError("timestamp must be an explicit UTC ISO-8601 Z string")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid UTC timestamp") from exc
    if parsed.tzinfo is None:
        raise ValueError("timestamp has no timezone")
    return parsed.astimezone(timezone.utc)


def summarize_records(records: list[dict], as_of: datetime) -> dict:
    if not isinstance(records, list) or not records:
        raise ValueError("nonempty records list required")
    checked = []
    for item in records:
        if not isinstance(item, dict):
            raise ValueError("non-object record")
        checked.append((parse_utc(item.get("t")), item))
    checked.sort(key=lambda pair: pair[0])
    if checked[-1][0] > as_of:
        raise ValueError("future timestamp; refuse look-ahead")
    intervals = []
    same_pct = duplicate_times = invalid_pct = 0
    for i, (dt, record) in enumerate(checked):
        lp, sp = record.get("lPct"), record.get("sPct")
        if (not isinstance(lp, (int, float)) or isinstance(lp, bool)
                or not isinstance(sp, (int, float)) or isinstance(sp, bool)
                or not 0 <= lp <= 100 or not 0 <= sp <= 100
                or abs(lp + sp - 100) > 1.01):
            invalid_pct += 1
        if i:
            prev_dt, prev = checked[i - 1]
            h = (dt - prev_dt).total_seconds() / 3600
            if h == 0:
                duplicate_times += 1
            else:
                intervals.append(h)
            if record.get("lPct") == prev.get("lPct"):
                same_pct += 1
    return {
        "observations": len(checked),
        "first_at": checked[0][0].isoformat().replace("+00:00", "Z"),
        "last_at": checked[-1][0].isoformat().replace("+00:00", "Z"),
        "distinct_utc_days": len({dt.date() for dt, _ in checked}),
        "adjacent_pairs": len(checked) - 1,
        "unchanged_long_pct_pairs": same_pct,
        "duplicate_timestamps": duplicate_times,
        "invalid_percentage_records": invalid_pct,
        "median_interval_hours": round(median(intervals), 2) if intervals else None,
        "gaps_over_12_hours": sum(h > 12 for h in intervals),
        "gaps_over_24_hours": sum(h > 24 for h in intervals),
    }


def scan_directory(folder: Path, as_of: datetime, *, show_stale_names: bool) -> dict:
    if not folder.is_dir():
        raise ValueError("history directory does not exist")
    per_series = []
    stale = []
    for file in sorted(folder.glob("*.json")):
        if file.is_symlink() or not file.is_file():
            raise ValueError("history file is not a regular file")
        if file.stat().st_size > 1_000_000:
            raise ValueError("oversize history file")
        data = json.loads(file.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or data.get("symbol") != file.stem:
            raise ValueError("history filename/symbol mismatch")
        summary = summarize_records(data.get("records"), as_of)
        summary["symbol"] = file.stem
        per_series.append(summary)
        if (as_of - parse_utc(summary["last_at"])).total_seconds() > 24 * 3600:
            stale.append(file.stem)
    if not per_series:
        raise ValueError("no historical series")
    pairs = sum(r["adjacent_pairs"] for r in per_series)
    unchanged = sum(r["unchanged_long_pct_pairs"] for r in per_series)
    median_series = [r["median_interval_hours"] for r in per_series
                     if r["median_interval_hours"] is not None]
    result = {
        "series_count": len(per_series),
        "observations": sum(r["observations"] for r in per_series),
        "adjacent_pairs": pairs,
        "unchanged_long_pct_pairs": unchanged,
        "unchanged_long_pct_pct": round(100 * unchanged / pairs, 1) if pairs else None,
        "duplicate_timestamps": sum(r["duplicate_timestamps"] for r in per_series),
        "invalid_percentage_records": sum(r["invalid_percentage_records"] for r in per_series),
        "gaps_over_12_hours": sum(r["gaps_over_12_hours"] for r in per_series),
        "gaps_over_24_hours": sum(r["gaps_over_24_hours"] for r in per_series),
        "median_of_series_median_hours": round(median(median_series), 2)
        if median_series else None,
        "stale_series_count_at_24h": len(stale),
    }
    if show_stale_names:
        result["stale_public_series"] = sorted(stale)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--myfxbook-dir", required=True, type=Path)
    parser.add_argument("--capital-dir", type=Path,
                        help="OPTIONAL private local directory; only aggregates emitted")
    parser.add_argument("--as-of", required=True,
                        help="Fixed UTC ISO Z audit timestamp; no retroactive first-seen")
    args = parser.parse_args()
    as_of = parse_utc(args.as_of)
    report = {
        "version": "REMURA_V20",
        "as_of": args.as_of,
        "scope": "record counts and cadence; NOT independent observations or alpha",
        "no_network": True,
        "myfxbook_retail": scan_directory(
            args.myfxbook_dir, as_of, show_stale_names=True),
    }
    if args.capital_dir is not None:
        report["capital_demo_private_aggregates_only"] = scan_directory(
            args.capital_dir, as_of, show_stale_names=False)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
