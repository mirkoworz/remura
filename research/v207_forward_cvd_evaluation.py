#!/usr/bin/env python3
"""REMURA V20.7 - OFFLINE prospective CVD vs price-only evaluation.

No network, broker requests, secrets, order execution, database writes, or
public price export. Requires separately captured, PRE-OUTCOME decisions;
the 12 V20.3 OBSERVATION_ONLY receipts are NOT trading decisions.
This is a research evaluator, not proof of independent first-seen or alpha.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import json
import math
from pathlib import Path
import re

from v204_private_cvd_price_coverage import (
    HORIZONS, M15_MS, checked_m15, ms, next_entry_after_max_receipt,
    read_local_price_db, utc,
)

UTC = timezone.utc
SCHEMA = "remura-v207-prospective-decision-ledger-v1"
SIDES = {"LONG": 1, "SHORT": -1, "FLAT": 0}
MIN_COMPLETED_PAIRS = 30
MIN_NONOVERLAPPING_WINDOWS = 10
MAX_DECISIONS = 10000
PIP_SIZE_EURUSD = 0.0001


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def checked_costs(spread_pips: float | None, slippage_pips_per_side: float | None) -> dict | None:
    if spread_pips is None or slippage_pips_per_side is None:
        if spread_pips is not None or slippage_pips_per_side is not None:
            raise ValueError("both_cost_assumptions_required")
        return None
    if not all(type(v) in (float, int) and math.isfinite(v) and 0 <= v <= 20
               for v in (spread_pips, slippage_pips_per_side)):
        raise ValueError("invalid_cost_assumption")
    return {"roundtrip_pips": float(spread_pips + 2 * slippage_pips_per_side),
            "spread_pips": float(spread_pips),
            "slippage_pips_per_side": float(slippage_pips_per_side)}


def _decisions(ledger: dict, as_of: datetime) -> list[dict]:
    if type(ledger) is not dict or ledger.get("schema") != SCHEMA:
        raise ValueError("unknown_ledger_schema")
    if ledger.get("symbol") != "EURUSD" or ledger.get("signal_family") != "CVD_PROXY_M5":
        raise ValueError("only_eurusd_cvd_proxy_m5")
    rows = ledger.get("decisions")
    if type(rows) is not list or len(rows) > MAX_DECISIONS:
        raise ValueError("invalid_decision_count")
    seen_ids: set[str] = set()
    seen_anchors: set[str] = set()
    seen_entry: set[int] = set()
    output = []
    now = ms(as_of)
    for row in rows:
        if type(row) is not dict:
            raise ValueError("malformed_decision")
        identity = row.get("decision_id")
        if type(identity) is not str or re.fullmatch(r"[A-Za-z0-9_-]{8,80}", identity) is None:
            raise ValueError("invalid_decision_id")
        if identity in seen_ids:
            raise ValueError("duplicate_decision_id")
        seen_ids.add(identity)
        if row.get("cvd_side") not in SIDES or row.get("price_only_side") not in SIDES:
            raise ValueError("invalid_prespecified_sides")
        count = row.get("observations_count")
        if type(count) is not int or not 1 <= count <= 100:
            raise ValueError("invalid_observations_per_decision")
        times = [ms(utc(row.get(k))) for k in (
            "event_close_utc", "received_at_utc", "recorded_at_utc",
            "frozen_at_utc", "price_only_known_at_utc")]
        close, received, recorded, frozen, baseline_known = times
        if close % (5 * 60_000) or not (close <= received <= recorded <= frozen):
            raise ValueError("invalid_causal_event_timestamps")
        if not (close <= baseline_known <= frozen):
            raise ValueError("baseline_uses_future_information")
        anchor = row.get("anchor")
        if type(anchor) is not dict or anchor.get("kind") != "github_commit":
            raise ValueError("immutable_external_anchor_required")
        sha = anchor.get("sha")
        if type(sha) is not str or re.fullmatch(r"[a-fA-F0-9]{40}", sha) is None:
            raise ValueError("invalid_anchor_sha")
        if sha.lower() in seen_anchors:
            raise ValueError("reused_immutable_anchor")
        seen_anchors.add(sha.lower())
        anchored = ms(utc(anchor.get("committed_at_utc")))
        if anchored < frozen or anchored > now:
            raise ValueError("anchor_outside_causal_window")
        if anchored - close > 30 * 60_000:
            raise ValueError("stale_or_backfilled_decision")
        # Exact M15 open is excluded: first opening STRICTLY AFTER the anchor.
        entry = next_entry_after_max_receipt(anchored, 0)
        if anchored >= entry or entry in seen_entry:
            raise ValueError("duplicate_or_nonprospective_m15_entry")
        seen_entry.add(entry)
        output.append({
            "entry": entry, "cvd": SIDES[row["cvd_side"]],
            "baseline": SIDES[row["price_only_side"]],
            "observations": count,
        })
    return sorted(output, key=lambda item: item["entry"])


def _nonoverlap(entry_times: list[int], interval_ms: int) -> int:
    count = 0
    eligible_from = -1
    for entry in sorted(entry_times):
        if entry >= eligible_from:
            count += 1
            eligible_from = entry + interval_ms
    return count


def _hypothetical_pips(entry_open: float, exit_close: float,
                       side: int, roundtrip_cost_pips: float) -> tuple[float, float]:
    gross = side * ((exit_close - entry_open) / PIP_SIZE_EURUSD)
    net = gross - (roundtrip_cost_pips if side else 0.0)
    return gross, net


def evaluate(ledger: dict | None, prices: dict | None, *,
             as_of: datetime, costs: dict | None = None) -> dict:
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError("aware_evaluation_time_required")
    if costs is not None:
        costs = checked_costs(costs["spread_pips"], costs["slippage_pips_per_side"])
    decisions = _decisions(ledger, as_of) if ledger is not None else []
    bars = checked_m15(prices, as_of) if prices is not None else {}
    report = {
        "schema": "remura-v207-forward-price-evaluation-report-v1",
        "scope": "OFFLINE_RESEARCH_ONLY",
        "as_of_utc": _iso(as_of),
        "status": ("NO_PRECOMMITTED_FORWARD_DECISIONS" if not decisions else
                   "PRICE_NOT_PROVIDED" if prices is None else
                   "PROVISIONAL_UNVERIFIED_ANCHORS_AND_FEED"),
        "observations_in_premarked_decisions": sum(d["observations"] for d in decisions),
        "unique_m15_decisions": len(decisions),
        "cvd_directional_decisions": sum(d["cvd"] != 0 for d in decisions),
        "price_only_directional_decisions": sum(d["baseline"] != 0 for d in decisions),
        "anchor_sha_and_time_claims_externally_verified": False,
        "independent_price_feed_authenticity_externally_verified": False,
        "prices_are_separate_ctrader_m15_not_tv_cvd_m5": prices is not None,
        "entry_rule": "first_full_M15_open_strictly_after_immutable_anchor",
        "exit_rule": "close_of_Nth_contiguous_closed_M15; no_gap_fill",
        "execution_model": "HYPOTHETICAL_MID_OHLC_NOT_EXECUTABLE_QUOTES",
        "cost_model": "UNVERIFIED_ASSUMPTIONS" if costs is not None else "COSTS_MISSING",
        "costs_are_observed_quotes": False,
        "scientific_alpha_established": False,
        "trades_or_notifications_activated": False,
        "price_values_or_event_ids_exported": False,
        "horizons": {}
    }
    for label, n in HORIZONS.items():
        completed = []
        immature = missing = 0
        for d in decisions:
            entry = d["entry"]
            if entry + n * M15_MS > ms(as_of):
                immature += 1
                continue
            series = [bars.get(entry + k * M15_MS) for k in range(n)]
            if any(b is None for b in series):
                missing += 1
                continue
            completed.append((d, series[0]["o"], series[-1]["c"]))
        directional = [row for row in completed if row[0]["cvd"] or row[0]["baseline"]]
        nonoverlap = _nonoverlap([d["entry"] for d, _, _ in directional], n * M15_MS)
        sufficient = (len(directional) >= MIN_COMPLETED_PAIRS and
                      nonoverlap >= MIN_NONOVERLAPPING_WINDOWS)
        item = {
            "complete_matched_m15_windows": len(completed),
            "complete_directional_comparisons": len(directional),
            "missing_contiguous_m15_windows": missing,
            "not_yet_mature_windows": immature,
            "max_nonoverlapping_directional_windows": nonoverlap,
            "overlaps_not_independent_samples": len(directional) > nonoverlap,
            "metric_gate": ("COST_ASSUMPTIONS_MISSING" if costs is None else
                            "PRICE_NOT_PROVIDED" if prices is None else
                            "SAMPLE_TOO_SMALL_OR_CORRELATED" if not sufficient else
                            "PROVISIONAL_DESCRIPTIVE_ONLY"),
            "net_pips": None,
            "paired_cvd_minus_price_only_net_pips": None,
            "cvd_win_fraction": None,
            "price_only_win_fraction": None,
        }
        if costs is not None and prices is not None and sufficient:
            gross_net = [
                (_hypothetical_pips(op, close, d["cvd"], costs["roundtrip_pips"]),
                 _hypothetical_pips(op, close, d["baseline"], costs["roundtrip_pips"]))
                for d, op, close in directional
            ]
            cvd_net = [pair[0][1] for pair in gross_net]
            baseline_net = [pair[1][1] for pair in gross_net]
            item["net_pips"] = {
                "cvd_mean": round(sum(cvd_net) / len(cvd_net), 5),
                "price_only_mean": round(sum(baseline_net) / len(baseline_net), 5),
            }
            item["paired_cvd_minus_price_only_net_pips"] = round(
                sum(a - b for a, b in zip(cvd_net, baseline_net)) / len(cvd_net), 5)
            item["cvd_win_fraction"] = round(sum(p > 0 for p in cvd_net) / len(cvd_net), 5)
            item["price_only_win_fraction"] = round(
                sum(p > 0 for p in baseline_net) / len(baseline_net), 5)
        report["horizons"][label] = item
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--decision-ledger", type=Path,
                        help="PRE-OUTCOME locally frozen JSON (never upload private events)")
    parser.add_argument("--private-sqlite", type=Path,
                        help="Optional LOCAL cTrader prices DB, opened strictly read-only")
    parser.add_argument("--spread-pips", type=float,
                        help="User-supplied assumed full spread, NOT verified historical quotes")
    parser.add_argument("--slippage-pips-per-side", type=float,
                        help="User-supplied assumed slippage on EACH side")
    args = parser.parse_args()
    try:
        costs = checked_costs(args.spread_pips, args.slippage_pips_per_side)
        ledger = json.loads(args.decision_ledger.read_text(encoding="utf-8")) if args.decision_ledger else None
        prices = read_local_price_db(args.private_sqlite) if args.private_sqlite else None
        result = evaluate(ledger, prices, as_of=datetime.now(UTC), costs=costs)
    except (ValueError, KeyError, FileNotFoundError, TypeError, OSError, json.JSONDecodeError):
        parser.error("Private input or prospective evidence rejected; details redacted")
    print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
