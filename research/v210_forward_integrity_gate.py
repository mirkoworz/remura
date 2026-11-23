#!/usr/bin/env python3
"""REMURA V21.0 -- fail-closed PRIVATE CVD -> frozen baseline -> forward price gate.

Never reconstruct directional CVD signals from the 12 V20.3 observation-only
receipts. Locally tie the saved event digest to the actual source bytes, check
the PRE-FREEZE five M15 price candles against the same read-only cTrader DB,
recalculate the price-only direction, then (only on explicit opt-in) request
the V20.8 GitHub hash witness and V20.7 future-window adjudication.

The checks establish consistency, NOT authenticity of TradingView, broker,
physical receipt time, live quote executability or institutional alpha.
No files written, no GitHub push, no broker, Cloudflare, D1 or Mac calls.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re

from v204_private_cvd_price_coverage import checked_m15, ms, read_local_price_db, utc, M15_MS
from v207_forward_cvd_evaluation import SCHEMA as LEDGER_SCHEMA, checked_costs
from v208_github_decision_witness import manifest_for, verified_evaluation
from v209_private_decision_freezer import BASELINE_RULE, MAX_EVENT_AGE, MAX_PRICE_AGE

UTC = timezone.utc
MAX_SOURCE_BYTES = 1_000_000
FIVE = 5
OHLC = ("t","o","h","l","c")
HASH64 = re.compile(r"[0-9a-f]{64}")


def _as_of(t: datetime) -> datetime:
    if not isinstance(t, datetime) or t.tzinfo is None:
        raise ValueError("aware_utc_now_required")
    return t.astimezone(UTC)


def _row(ledger: dict) -> dict:
    if (type(ledger) is not dict or
        set(ledger) != {"schema","symbol","signal_family","decisions"} or
        ledger.get("schema") != LEDGER_SCHEMA or
        ledger.get("symbol") != "EURUSD" or
        ledger.get("signal_family") != "CVD_PROXY_M5"):
        raise ValueError("unrecognized_private_ledger")
    rows = ledger["decisions"]
    if type(rows) is not list or len(rows) != 1 or type(rows[0]) is not dict:
        raise ValueError("single_frozen_candidate_only")
    return rows[0]


def local_integrity(ledger: dict, manifest: dict, source_bytes: bytes,
                    prices: dict, *, as_of: datetime) -> dict:
    """Check LOCAL source hash and frozen baseline, WITHOUT GitHub/network."""
    as_of = _as_of(as_of)
    row = _row(ledger)
    if type(source_bytes) is not bytes or not 1 <= len(source_bytes) <= MAX_SOURCE_BYTES:
        raise ValueError("real_original_event_bytes_required")
    digest = row.get("source_event_sha256")
    if (type(digest) is not str or HASH64.fullmatch(digest) is None or
        digest != hashlib.sha256(source_bytes).hexdigest()):
        raise ValueError("original_source_event_digest_mismatch")
    if (type(manifest) is not dict or
        set(manifest) != {"schema","commitment_sha256"} or
        manifest != manifest_for(row)):
        raise ValueError("sealed_private_decision_differs_from_manifest")
    if (row.get("cvd_source_authentication") != "LOCAL_ASSERTION_UNVERIFIED" or
        row.get("price_feed_authentication") != "LOCAL_CTRADER_SQLITE_UNVERIFIED" or
        row.get("price_only_rule") != BASELINE_RULE or
        row.get("observations_count") != 1):
        raise ValueError("unexpected_source_rule_or_observation_count")
    if row.get("cvd_side") not in {"LONG","SHORT","FLAT"}:
        raise ValueError("bad_frozen_cvd_side")
    closed_at = utc(row.get("event_close_utc"))
    receipt = utc(row.get("received_at_utc"))
    recorded = utc(row.get("recorded_at_utc"))
    frozen = utc(row.get("frozen_at_utc"))
    baseline_known = utc(row.get("price_only_known_at_utc"))
    if (ms(closed_at) % (5*60_000) or
        not closed_at <= receipt <= recorded == frozen == baseline_known <= as_of or
        frozen - closed_at > MAX_EVENT_AGE):
        raise ValueError("invalid_forward_decision_timing")
    # Compare the frozen 5-bar snapshot to the ORIGINAL FREEZE INSTANT,
    # not to the most recent five bars available today.
    closed_market = checked_m15(prices, frozen)
    original = sorted(closed_market.items())[-FIVE:]
    if len(original) != FIVE:
        raise ValueError("not_enough_original_closed_m15")
    if any(right[0] - left[0] != M15_MS for left, right in zip(original, original[1:])):
        raise ValueError("original_five_m15_not_contiguous")
    end_ms = original[-1][0] + M15_MS
    if end_ms > ms(frozen) or ms(frozen) - end_ms > int(MAX_PRICE_AGE.total_seconds()*1000):
        raise ValueError("original_price_not_fresh_at_freeze")
    saved = row.get("price_only_input_m15")
    if type(saved) is not list or len(saved) != FIVE:
        raise ValueError("missing_original_price_snapshot")
    for private, (_, price) in zip(saved, original):
        if type(private) is not dict or set(private) != set(OHLC):
            raise ValueError("malformed_locked_ohlc")
        if any(type(private[k]) not in (int,float) for k in OHLC[1:]):
            raise ValueError("bad_locked_ohlc_numeric_type")
        if any(private[k] != price[k] for k in OHLC):
            raise ValueError("locked_ohlc_differs_from_local_price_database")
    baseline = (
        "LONG" if saved[-1]["c"] > saved[0]["c"] else
        "SHORT" if saved[-1]["c"] < saved[0]["c"] else "FLAT"
    )
    if row.get("price_only_side") != baseline:
        raise ValueError("frozen_price_only_direction_does_not_follow_rule")
    # This does not prove the data were in the DB at the time of freeze;
    # a database that was later rewritten would evade this check.
    return {
        "schema":"remura-v210-private-forward-integrity-v1",
        "status":"LOCAL_ORIGINAL_SOURCE_AND_BASELINE_CONSISTENT",
        "decisions_prospectively_hashed":1,
        "source_original_bytes_sha256_matches_frozen_digest":True,
        "source_receipt_timestamp_independently_verified":False,
        "cvd_direction_independently_derived_from_source":False,
        "original_closed_five_m15_match_current_local_ctrader_snapshot":True,
        "broker_market_data_history_independently_authenticated":False,
        "baseline_rule_and_timestamp_consistent":True,
        "github_first_seen_witness_verified":False,
        "actual_forward_outcomes_evaluated":False,
        "scientific_alpha_established":False,
        "prices_ids_source_content_or_secrets_exported":False,
    }


def adjudicate(ledger: dict, manifest: dict, source_bytes: bytes, prices: dict,
              *, as_of: datetime, github_readonly: bool = False,
              costs: dict | None = None, fetch_json=None) -> dict:
    report = local_integrity(ledger, manifest, source_bytes, prices, as_of=as_of)
    if costs is not None:
        costs = checked_costs(costs["spread_pips"],costs["slippage_pips_per_side"])
    if not github_readonly:
        report["status"] = "LOCAL_ONLY_NO_EXTERNAL_WITNESS_NO_OUTCOMES"
        return report
    # Network is a SEPARATE explicit action; two anonymous GitHub REST GETs
    # maximum for this ONE decision. Never send the private ledger.
    if fetch_json is None:
        from v208_github_decision_witness import get_github_json
        fetch_json = get_github_json
    measured = verified_evaluation(
        ledger, prices, as_of=as_of, costs=costs, fetch_json=fetch_json
    )
    if measured.get("github_hash_only_witness_verified") is not True:
        raise ValueError("github_witness_missing")
    report.update({
        "status":"HASH_WITNESSED_LOCAL_CONSISTENCY_VALIDATED_NO_SOURCE_AUTHENTICATION",
        "github_first_seen_witness_verified":True,
        "actual_forward_outcomes_evaluated":True if prices is not None else False,
        "forward_windows":measured["horizons"],
        "costs_are_observed_quotes":False,
        "cvd_direction_independently_derived_from_source":False,
        "source_receipt_timestamp_independently_verified":False,
        "broker_market_data_history_independently_authenticated":False,
        "scientific_alpha_established":False,
    })
    return report


def _read_limited(path: Path) -> bytes:
    with path.open("rb") as file:
        data = file.read(MAX_SOURCE_BYTES+1)
    if not data or len(data) > MAX_SOURCE_BYTES:
        raise ValueError("original_event_empty_or_oversize")
    return data


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--private-decision-ledger", type=Path)
    ap.add_argument("--private-manifest", type=Path,
                    help="Locally frozen hash-only manifest, NOT an automatic GitHub push")
    ap.add_argument("--original-event-bytes", type=Path,
                    help="Raw original event bytes; read locally, never uploaded")
    ap.add_argument("--private-sqlite", type=Path,
                    help="Existing cTrader SQLite opened in read-only mode")
    ap.add_argument("--github-readonly", action="store_true",
                    help="Explicitly allow 2 anonymous GitHub GETs, no retry")
    ap.add_argument("--spread-pips", type=float)
    ap.add_argument("--slippage-pips-per-side", type=float)
    args = ap.parse_args()
    if not any((
        args.private_decision_ledger, args.private_manifest,
        args.original_event_bytes, args.private_sqlite,
        args.github_readonly, args.spread_pips is not None,
        args.slippage_pips_per_side is not None,
    )):
        print(json.dumps({
            "status":"NO_PRIVATE_INPUTS_NO_EXTERNAL_CALLS",
            "true_forward_decisions_adjudicated":0,
            "profitable_trades_claimed":0,
        },sort_keys=True))
        return
    if not all((
        args.private_decision_ledger, args.private_manifest,
        args.original_event_bytes, args.private_sqlite,
    )):
        ap.error("All four LOCAL evidence paths required; no data accessed")
    try:
        ledger = json.loads(args.private_decision_ledger.read_text(encoding="utf-8"))
        manifest = json.loads(args.private_manifest.read_text(encoding="utf-8"))
        raw = _read_limited(args.original_event_bytes)
        prices = read_local_price_db(args.private_sqlite)
        costs = checked_costs(args.spread_pips,args.slippage_pips_per_side)
        result = adjudicate(
            ledger, manifest, raw, prices,
            as_of=datetime.now(UTC), github_readonly=args.github_readonly,
            costs=costs,
        )
    except (ValueError, OSError, UnicodeError, TypeError, KeyError,
            json.JSONDecodeError):
        ap.error("Source/baseline/time/witness rejected; private details suppressed")
    print(json.dumps(result,sort_keys=True,indent=2,allow_nan=False))


if __name__ == "__main__":
    main()
