# REMURA TradingView v0.8.184 LAB — 21/11/2026 Europe/Rome
# Count ONLY manually requested synthetic M5 slots. No market calendar or outcomes.
"""Measure missing evidence among explicitly planned M5 capture slots.

Slots are caller-supplied, not attested as real trading opportunities.
A gap between planned slots is NOT filled or interpreted as a missing bar.
A missing capture is NOT evidence that the market was quiet.
"""
from __future__ import annotations
from datetime import timedelta
import json
import sys
from holdout_freeze_v0182_lab import guard, phase, FreezeError
from m5_intake_gate_v0183_lab import (
    evaluate, parse_utc, M5, GRACE, MAX_ITEMS, TimingError,
)

MAX_PLAN = 60

class CoverageError(ValueError):
    pass

def aligned(t) -> bool:
    return t.minute % 5 == 0 and t.second == 0 and t.microsecond == 0

def coverage(plan: object) -> dict[str, object]:
    result: dict[str, object] = {
        "schema": "remura.tradingview.explicit_m5_coverage.v0184.lab",
        "version": "0.8.184", "status": "INVALID_OR_UNVERIFIED",
        "planned_slots": None, "timely_captures": None,
        "late_captures": None, "uncaptured_requested_slots": None,
        "fold": "UNKNOWN", "slot_scope": "EXPLICIT_OPERATOR_PLAN_ONLY",
        "exchange_calendar_attested": False,
        "capture_provenance_attested": False,
        "market_coverage_attested": False,
        "zero_captures_prove_no_market_activity": False,
        "future_outcomes_used": False,
        "edge_claim_allowed": False,
        "automatic_capture_or_deploy_allowed": False,
        "decision": "NO_GO_LIVE",
    }
    try:
        pinned = guard()
        if pinned["protocol"] != "CVD_PROSPECTIVE_V2_PINNED":
            raise CoverageError("protocol_not_pinned")
        if not isinstance(plan, dict) or set(plan) != {
            "source", "fold", "requested_closes_utc", "observations"
        }:
            raise CoverageError("unexpected_plan_shape")
        if plan["source"] != "OFFLINE_SYNTHETIC_EXPLICIT_SLOTS":
            raise CoverageError("plan_source_untrusted")
        fold = plan["fold"]
        if fold not in ("HOLDOUT_1", "HOLDOUT_2"):
            raise CoverageError("fold_unexpected")
        requested = plan["requested_closes_utc"]
        observations = plan["observations"]
        if (not isinstance(requested, list) or not 1 <= len(requested) <= MAX_PLAN or
                not isinstance(observations, list) or len(observations) > MAX_ITEMS):
            raise CoverageError("plan_unbounded")
        # Strict ordering: never reorder or synthesize dates.
        requested_times = [parse_utc(x) for x in requested]
        if any(not aligned(x) or phase(x) != fold for x in requested_times):
            raise CoverageError("bad_planned_slot_or_fold")
        if any(a >= b for a,b in zip(requested_times, requested_times[1:])):
            raise CoverageError("duplicate_or_unordered_schedule")
        requested_set = set(requested_times)
        if len(observations) > len(requested):
            raise CoverageError("more_captures_than_requested")
        seen_close=set()
        timely=late=0
        if observations:
            quality=evaluate(observations)
            if quality["status"] != "BOUNDARIES_REVIEWED_OFFLINE_ONLY":
                raise CoverageError("invalid_event_batch")
            for event in observations:
                close = parse_utc(event["bar_close_utc"])
                received = parse_utc(event["received_utc"])
                next_close = parse_utc(event["next_close_utc"])
                if (close not in requested_set or close in seen_close
                        or phase(close) != fold or next_close - close != M5):
                    raise CoverageError("unrequested_duplicate_or_out_of_fold")
                seen_close.add(close)
                if received <= close + GRACE and received < next_close:
                    timely += 1
                else:
                    late += 1
            # Ensure we did not accidentally reinterpret downstream gate's accounting.
            if quality["eligible"] != timely or quality["late"] != late:
                raise CoverageError("intake_accounting_mismatch")
        missing = len(requested) - len(seen_close)
        result.update({
            "status": "EXPLICIT_CAPTURE_COVERAGE_OFFLINE_ONLY",
            "fold": fold,
            "planned_slots": len(requested),
            "timely_captures": timely,
            "late_captures": late,
            "uncaptured_requested_slots": missing,
        })
    except (CoverageError, FreezeError, TimingError, OSError, UnicodeError, TypeError, ValueError, KeyError):
        result["status"] = "INVALID_OR_UNVERIFIED"
    return result

def demo() -> dict[str, object]:
    return {
        "source": "OFFLINE_SYNTHETIC_EXPLICIT_SLOTS",
        "fold": "HOLDOUT_1",
        "requested_closes_utc": [
            "2026-11-23T00:05:00Z",
            "2026-11-23T00:10:00Z",
            "2026-11-23T00:15:00Z",
        ],
        "observations": [
            {
                "source": "OFFLINE_SYNTHETIC_M5",
                "decision_digest": "a" * 64,
                "bar_close_utc": "2026-11-23T00:05:00Z",
                "next_close_utc": "2026-11-23T00:10:00Z",
                "received_utc": "2026-11-23T00:07:00Z",
            },
            {
                "source": "OFFLINE_SYNTHETIC_M5",
                "decision_digest": "b" * 64,
                "bar_close_utc": "2026-11-23T00:10:00Z",
                "next_close_utc": "2026-11-23T00:15:00Z",
                "received_utc": "2026-11-23T00:12:01Z",
            },
        ],
    }

def main(argv: list[str]) -> int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_TV_V0184_COVERAGE=NO_GO_BAD_ARGUMENTS")
        return 2
    result = coverage(demo())
    if (result["status"] != "EXPLICIT_CAPTURE_COVERAGE_OFFLINE_ONLY" or
            result["timely_captures"] != 1 or result["late_captures"] != 1 or
            result["uncaptured_requested_slots"] != 1 or result["edge_claim_allowed"]):
        print("REMURA_TV_V0184_COVERAGE=NO_GO_FIXTURE_MISMATCH")
        return 3
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
