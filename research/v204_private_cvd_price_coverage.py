#!/usr/bin/env python3
"""REMURA V20.4: LOCAL read-only cTrader M15 coverage probe for proven CVD TEST M5 slots.

Strictly observes which future closed M15 bars exist after a real, bounded,
aggregated CVD receipt window. Does NOT compute signal returns/alpha, trade,
infer per-bar CVD direction, use the TradingView OHLC as independent prices,
read Cloudflare, or disclose prices. Requires a private LOCAL SQLite DB.
No changes to existing Mac/Oracle collectors.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import sqlite3

UTC = timezone.utc
M5_MS = 5 * 60_000
M15_MS = 15 * 60_000
HORIZONS = { "60m": 4, "4h": 16, "24h": 96 }
REAL_RUN = "https://github.com/mirkoworz/remura/actions/runs/45121703188"
SYMBOL = "EURUSD"
MAX_PAYLOAD_BYTES = 8_000_000
MAX_CANDLES = 5_000
EXPECTED_SLOTS = 12
EXPECTED_START = 1795408200000
EXPECTED_END = 1795411500000


def utc(value: str) -> datetime:
    if type(value) is not str or not value.endswith("Z"):
        raise ValueError("explicit_utc_z_required")
    try:
        v = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise ValueError("bad_iso_time") from exc
    if v.tzinfo is None or v.utcoffset() != timedelta(0):
        raise ValueError("not_utc")
    return v


def ms(value: datetime) -> int:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("timezone_required")
    return int(value.astimezone(UTC).timestamp() * 1000)


def receipt_window(proof: dict) -> dict:
    if type(proof) is not dict or proof.get("schema") != "remura-v203-tradingview-test-receipt-real-proof":
        raise ValueError("unknown_real_receipt_evidence")
    p = proof.get("provenance")
    r = proof.get("result")
    if type(p) is not dict or type(r) is not dict:
        raise ValueError("missing_provenance")
    if p.get("github_workflow_run") != REAL_RUN or p.get("job_conclusion") != "success":
        raise ValueError("unverified_run")
    if r.get("schema") != "remura.tv.cvd.first.receipt.preview.v2" or r.get("status") != "COMPLETE_REQUESTED_WINDOW":
        raise ValueError("not_a_valid_real_window")
    w = r.get("window")
    c = r.get("collection")
    radar = r.get("radar")
    if type(w) is not dict or type(c) is not dict or type(radar) is not dict:
        raise ValueError("missing_ledger_metadata")
    if (r.get("symbol") != "FX:EURUSD" or r.get("sender_version") != "0.9.1-cvd-lab"
            or r.get("requested_slots") != EXPECTED_SLOTS
            or r.get("valid_unique_bars") != EXPECTED_SLOTS
            or r.get("missing_requested_slots") != 0
            or r.get("duplicate_rows") != 0
            or w.get("start_close_ms") != EXPECTED_START
            or w.get("end_close_ms") != EXPECTED_END
            or c.get("target") != "EU_D1_TEST_ONLY"
            or c.get("select_requests") != 1 or c.get("inventory_requests") != 1
            or c.get("query_rows_written") != 0
            or radar.get("verdict") != "NO_OPERATIONAL_SIGNAL"
            or radar.get("counts", {}).get("OBSERVATION_ONLY") != 12
            or radar.get("candidate_cooccurrences") != {}
            or r.get("scientific_admission") is not False
            or r.get("outcomes_computed") is not False):
        raise ValueError("receipt_evidence_drift")
    lag = r.get("max_lag_ms")
    if type(lag) is not int or not 0 <= lag <= 120_000:
        raise ValueError("invalid_receipt_lag")
    return {"start": EXPECTED_START, "end": EXPECTED_END, "max_lag": lag}


def read_local_price_db(dbpath: Path) -> dict:
    """Only a private local SQLite SELECT; opening never creates a database."""
    p = dbpath.expanduser().resolve(strict=True)
    if not p.is_file():
        raise ValueError("sqlite_file_required")
    uri = p.as_uri() + "?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True, timeout=3) as db:
            db.execute("PRAGMA query_only=ON")
            row = db.execute("SELECT payload FROM prices WHERE symbol=?", (SYMBOL,)).fetchone()
    except sqlite3.Error as exc:
        raise ValueError("private_price_snapshot_unavailable") from exc
    if not row or type(row[0]) is not str or len(row[0].encode("utf-8")) > MAX_PAYLOAD_BYTES:
        raise ValueError("missing_or_oversize_private_price_payload")
    try:
        return json.loads(row[0])
    except json.JSONDecodeError as exc:
        raise ValueError("invalid_private_price_json") from exc


def checked_m15(doc: dict, as_of: datetime) -> dict[int, dict]:
    if type(doc) is not dict or doc.get("symbol") != SYMBOL or doc.get("provider") != "ctrader":
        raise ValueError("only_local_ctrader_eurusd_accepted")
    broker = doc.get("providerSymbol")
    if type(broker) is not str or not 1 <= len(broker) <= 100:
        raise ValueError("broker_symbol_missing")
    rows = doc.get("timeframes", {}).get("M15")
    if type(rows) is not list or not 1 <= len(rows) <= MAX_CANDLES:
        raise ValueError("no_real_m15_rows")
    result: dict[int, dict] = {}
    prev = None
    now_ms = ms(as_of)
    for row in rows:
        if type(row) is not dict or not {"t", "o", "h", "l", "c"} <= set(row):
            raise ValueError("malformed_m15")
        instant = ms(utc(row["t"]))
        if instant % M15_MS or (prev is not None and instant <= prev):
            raise ValueError("unsorted_duplicate_or_unaligned_m15")
        prev = instant
        nums = tuple(row[k] for k in ("o", "h", "l", "c"))
        if any(type(x) not in (int, float) or not math.isfinite(x) or x <= 0 for x in nums):
            raise ValueError("invalid_ohlc")
        op, hi, lo, cl = nums
        if lo > min(op, cl) or hi < max(op, cl) or hi < lo:
            raise ValueError("invalid_candle_extremes")
        # Fail closed: no future/unclosed bar may become evidence, even if present in a file.
        if instant + M15_MS <= now_ms:
            result[instant] = row
    return result


def next_entry_after_max_receipt(close_ms: int, maximum_lag_ms: int) -> int:
    """First whole M15 open after receipt worst-case bound; never enter at M5 close."""
    after = close_ms + maximum_lag_ms
    return (after // M15_MS + 1) * M15_MS


def assess(proof: dict, private_m15: dict | None, *, as_of: datetime) -> dict:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError("asof_must_be_aware")
    target = receipt_window(proof)
    if ms(as_of) <= target["end"] + target["max_lag"]:
        raise ValueError("receipt_window_not_fully_past")
    starts = [
        next_entry_after_max_receipt(t, target["max_lag"])
        for t in range(target["start"], target["end"] + M5_MS, M5_MS)
    ]
    if len(starts) != 12 or len(set(starts)) != 4:
        raise ValueError("expected_four_unique_m15_cohorts")
    result = {
        "schema": "remura-v204-private-cvd-independent-price-coverage",
        "proof_run": REAL_RUN,
        "as_of_utc": as_of.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "status": "PRICE_NOT_PROVIDED" if private_m15 is None else "PRICE_COVERAGE_CHECKED",
        "cvd_receipts_verified_requested_window": 12,
        "cvd_events_with_direction_proven": 0,
        "conservative_receipt_bound_ms": target["max_lag"],
        "m15_cohorts_unique_not_12_independent_trades": len(set(starts)),
        "price_provider_family": "ctrader" if private_m15 is not None else "UNKNOWN",
        "price_broker_is_independently_authenticated": False,
        "price_only_m15_is_not_same_as_cvd_m5": True,
        "price_values_or_broker_ids_exported": False,
        "directional_outcomes_computed": False,
        "statistical_alpha_established": False,
        "costs_spreads_slippage_verified": False,
        "orders_enabled": False,
        "horizons": {}
    }
    bars = checked_m15(private_m15, as_of) if private_m15 is not None else {}
    for label, n in HORIZONS.items():
        ready = 0
        immature = 0
        missing = 0
        # Distinguish correlated 12 M5 receptions from 4 unique future M15 entry cohorts.
        for entry in sorted(set(starts)):
            if entry + n * M15_MS > ms(as_of):
                immature += 1
            elif any(entry + i * M15_MS not in bars for i in range(n)):
                missing += 1
            else:
                ready += 1
        result["horizons"][label] = {
            "complete_unique_m15_price_cohorts": ready,
            "closed_but_price_missing_unique_cohorts": missing,
            "not_yet_mature_unique_cohorts": immature,
            "total_unique_cohorts": len(set(starts)),
            "price_outcomes_or_cvd_directions_calculated": False,
        }
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--receipt-proof", type=Path, required=True)
    ap.add_argument("--private-sqlite", type=Path, help="Read-only private prices DB; never upload to GitHub")
    args = ap.parse_args()
    proof = json.loads(args.receipt_proof.read_text(encoding="utf-8"))
    private = read_local_price_db(args.private_sqlite) if args.private_sqlite else None
    report = assess(proof, private, as_of=datetime.now(UTC))
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
