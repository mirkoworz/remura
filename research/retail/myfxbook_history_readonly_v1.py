#!/usr/bin/env python3
# REMURA Retail Observatory v0.1 LAB — 21/11/2026 Europe/Rome.
"""Read-only, offline audit of EXISTING public Myfxbook repository histories.

Unlike simulated provider fixtures, a checkout of the actual repository data
can be audited. This checks file structure, timestamps and per-symbol ordering;
it cannot certify live provider observations, commit-time truth, first-seen
provenance or trading opportunity coverage. NEVER infer institutional activity.
No market predictions, browser, network, API, Secret or repository changes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import json
import re
import sys

SCHEMA = "remura.retail.git_history_readonly.v1.lab"
SOURCE = "Myfxbook Community Outlook"
UTC = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
SYMBOL = re.compile(r"^[A-Z0-9]{3,12}$")
FIELDS = ("t", "lPct", "sPct", "lLots", "sLots", "lPos", "sPos", "avgL", "avgS")
MAX_LATEST_BYTES = 500_000
MAX_HISTORY_BYTES = 100_000
MAX_SERIES = 200
MAX_RECORDS = 3000

class InvalidHistory(ValueError):
    pass

def parse_utc(value):
    if not isinstance(value, str) or not UTC.fullmatch(value):
        raise InvalidHistory("invalid_utc")
    try:
        ts = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise InvalidHistory("invalid_utc") from exc
    if ts.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise InvalidHistory("noncanonical_utc")
    return ts

def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise InvalidHistory("duplicate_json_keys")
        result[key] = value
    return result

def read_json(path, cap):
    if not path.is_file() or path.is_symlink() or path.stat().st_size > cap:
        raise InvalidHistory("file_unavailable_or_oversized")
    return json.loads(path.read_bytes().decode("utf-8"), object_pairs_hook=unique_pairs)

def valid_row(row):
    if type(row) is not dict or set(row) != set(FIELDS):
        raise InvalidHistory("row_schema_mismatch")
    stamp = parse_utc(row["t"])
    for k in ("lPct", "sPct", "lLots", "sLots", "lPos", "sPos"):
        n = row[k]
        if type(n) not in (int, float) or not (0 <= n <= 10**12):
            raise InvalidHistory("row_measure_invalid")
    if row["lPct"] > 100 or row["sPct"] > 100:
        raise InvalidHistory("row_percentage_invalid")
    for k in ("avgL", "avgS"):
        if row[k] is not None and (type(row[k]) not in (int, float) or not (0 <= row[k] <= 10**12)):
            raise InvalidHistory("row_price_invalid")
    return stamp

def blank(status="UNVERIFIED_OR_INCOMPLETE", reason="UNKNOWN"):
    return {
        "schema": SCHEMA, "version": "0.1",
        "status": status, "reason": reason,
        "latest_utc": None, "symbols_in_latest": None,
        "series_checked": None, "records_checked": None,
        "history_gaps_over_2h": None,
        "current_series": None,
        "historical_only_legacy_series": None,
        "latest_snapshot_is_fresh_2h": None,
        "source": "REPOSITORY_JSON_ONLY",
        "collector_was_proven_online": False,
        "external_source_first_seen_verified": False,
        "independent_receipt_verified": False,
        "git_server_timestamp_verified": False,
        "original_market_coverage_verified": False,
        "retail_is_institutional": False,
        "holdout_causal_admission": False,
        "edge_established": False,
        "data_modified": False,
        "network_calls": 0,
        "provider_calls": 0,
        "trades_or_alerts_enabled": False,
    }

def audit(root, *, now_utc):
    out = blank()
    try:
        now = parse_utc(now_utc)
        if not isinstance(root, Path) or root.is_symlink() or not root.is_dir():
            raise InvalidHistory("root_invalid")
        folder = root / "history"
        if folder.is_symlink() or not folder.is_dir():
            raise InvalidHistory("history_directory_invalid")
        latest = read_json(root / "latest.json", MAX_LATEST_BYTES)
        if type(latest) is not dict or set(latest) != {"status", "source", "updatedAt", "symbols"} or (
            latest["status"] != "ok" or latest["source"] != SOURCE or
            type(latest["symbols"]) is not dict or not 1 <= len(latest["symbols"]) <= 200
        ):
            raise InvalidHistory("latest_schema_invalid")
        stamp = parse_utc(latest["updatedAt"])
        if stamp > now:
            raise InvalidHistory("future_latest")
        for symbol, row in latest["symbols"].items():
            if not SYMBOL.fullmatch(symbol) or valid_row(row) != stamp:
                raise InvalidHistory("latest_rows_or_clock_invalid")
        files = sorted(folder.glob("*"))
        if not 1 <= len(files) <= MAX_SERIES:
            raise InvalidHistory("history_series_count_invalid")
        total = 0
        gaps = 0
        current_series = 0
        historical_only = 0
        for file in files:
            if not file.name.endswith(".json") or not SYMBOL.fullmatch(file.stem):
                raise InvalidHistory("unexpected_file_name")
            history = read_json(file, MAX_HISTORY_BYTES)
            if type(history) is not dict or set(history) != {"symbol", "source", "sampling", "records"} or (
                history["symbol"] != file.stem or history["source"] != SOURCE or
                history["sampling"] not in {
                    "observed at recorded timestamps (not guaranteed 20m)",
                    "observed approximately every 20 minutes"
                } or
                type(history["records"]) is not list or not 1 <= len(history["records"]) <= MAX_RECORDS
            ):
                raise InvalidHistory("history_document_invalid")
            times = [valid_row(row) for row in history["records"]]
            if any(a >= b for a, b in zip(times, times[1:])):
                raise InvalidHistory("history_duplicate_or_regressive_time")
            if any(ts > now for ts in times):
                raise InvalidHistory("future_history")
            if history["sampling"] == "observed approximately every 20 minutes":
                # Legacy sampling claim is NOT a verified cadence or current feed.
                if file.stem in latest["symbols"] or times[-1] > stamp:
                    raise InvalidHistory("legacy_current_scope_ambiguous")
                historical_only += 1
            else:
                if file.stem not in latest["symbols"]:
                    raise InvalidHistory("current_symbol_missing_from_latest")
                if times[-1] != stamp or history["records"][-1] != latest["symbols"][file.stem]:
                    raise InvalidHistory("latest_history_not_synchronized")
                current_series += 1
            gaps += sum((b-a).total_seconds()>7200 for a,b in zip(times, times[1:]))
            total += len(times)
        out.update(
            status=("REPOSITORY_HISTORY_PARTIAL_LEGACY_UNATTESTED"
                    if historical_only else "REPOSITORY_HISTORY_STRUCTURALLY_CONSISTENT_UNATTESTED"),
            reason=("LEGACY_HISTORIES_NOT_CURRENT_PROVENANCE_UNVERIFIED"
                    if historical_only else "SOURCE_PROVENANCE_NOT_INDEPENDENTLY_VERIFIED"),
            latest_utc=latest["updatedAt"],
            symbols_in_latest=len(latest["symbols"]),
            series_checked=len(files), records_checked=total,
            history_gaps_over_2h=gaps,
            current_series=current_series,
            historical_only_legacy_series=historical_only,
            latest_snapshot_is_fresh_2h=(now-stamp).total_seconds()<=7200,
        )
    except InvalidHistory as exc:
        # Only a static enum-like label, never a row value, path or account identifier.
        out["reason"] = str(exc)
    except (ValueError, OSError, UnicodeError, OverflowError, TypeError, KeyError):
        pass
    return out

if __name__ == "__main__":
    if sys.argv[1:] != ["--repo-read-only"]:
        print("REMURA_RETAIL_HISTORY=NO_GO_ARGUMENTS")
        raise SystemExit(2)
    root = Path(__file__).resolve().parents[2] / "data" / "myfxbook"
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    print(json.dumps(audit(root,now_utc=now),sort_keys=True,separators=(",",":")))
