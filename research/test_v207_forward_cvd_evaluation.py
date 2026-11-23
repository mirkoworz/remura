"""REMURA V20.7 NEW-only tests: synthetic OHLC and synthetic prospective decisions.

No remote calls, no secrets, no real individual CVD rows, no broker prices.
Older V20/V20.4/V20.6 suites are intentionally not invoked here.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import unittest

from v207_forward_cvd_evaluation import (
    _decisions, _hypothetical_pips, checked_costs, evaluate,
    SCHEMA,
)

UTC = timezone.utc
BASE = datetime(2026, 11, 23, 4, 45, tzinfo=UTC)
ASOF = datetime(2026, 11, 23, 7, 0, tzinfo=UTC)


def stamp(value):
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def decision(day=0, *, side="LONG", baseline="SHORT", sha_number=1):
    close = BASE + timedelta(days=day, minutes=-15)
    return {
        "decision_id": f"synthetic_{day:03d}_{sha_number:03d}",
        "event_close_utc": stamp(close),
        "received_at_utc": stamp(close + timedelta(seconds=15)),
        "recorded_at_utc": stamp(close + timedelta(seconds=20)),
        "frozen_at_utc": stamp(close + timedelta(minutes=1)),
        "price_only_known_at_utc": stamp(close + timedelta(seconds=18)),
        "cvd_side": side,
        "price_only_side": baseline,
        "observations_count": 3,
        "anchor": {
            "kind": "github_commit",
            "sha": f"{sha_number:040x}",
            "committed_at_utc": stamp(close + timedelta(minutes=3))
        },
    }


def ledger(*decisions):
    return {"schema": SCHEMA, "symbol": "EURUSD",
            "signal_family": "CVD_PROXY_M5", "decisions": list(decisions)}


def prices(count, *, gap=None):
    candles = []
    for i in range(count):
        start = BASE + timedelta(minutes=i * 15)
        if start == gap:
            continue
        # All OHLC values are obviously SYNTHETIC; constant movement by design.
        candles.append({
            "t": stamp(start), "o": 1.1000, "h": 1.1003,
            "l": 1.0999, "c": 1.1002,
        })
    return {
        "symbol": "EURUSD", "provider": "ctrader",
        "providerSymbol": "SYNTHETIC_TEST_ONLY",
        "timeframes": {"M15": candles}
    }


class V207ForwardCvdNewOnlyTests(unittest.TestCase):
    def test_no_forward_decisions_no_alpha_even_with_prices(self):
        r = evaluate(None, prices(8), as_of=ASOF, costs=checked_costs(1.0, 0.2))
        self.assertEqual(r["status"], "NO_PRECOMMITTED_FORWARD_DECISIONS")
        self.assertEqual(r["unique_m15_decisions"], 0)
        self.assertEqual(r["horizons"]["60m"]["complete_directional_comparisons"], 0)
        self.assertFalse(r["scientific_alpha_established"])

    def test_one_decision_three_observations_not_three_trades(self):
        r = evaluate(ledger(decision()), prices(8), as_of=ASOF)
        self.assertEqual(r["unique_m15_decisions"], 1)
        self.assertEqual(r["observations_in_premarked_decisions"], 3)
        self.assertEqual(r["horizons"]["60m"]["complete_matched_m15_windows"], 1)
        self.assertIsNone(r["horizons"]["60m"]["net_pips"])

    def test_entry_strict_after_external_anchor_even_at_boundary(self):
        d = decision()
        d["anchor"]["committed_at_utc"] = "2026-11-23T04:45:00Z"
        as_of = datetime(2026, 11, 24, tzinfo=UTC)
        r = _decisions(ledger(d), as_of)
        self.assertEqual(r[0]["entry"], int(
            datetime(2026, 11, 23, 5, 0, tzinfo=UTC).timestamp() * 1000))
        # The decision was frozen before open; anchor exactly at the open
        # still forces entry into the NEXT, unavailable-at-anchor bar.
        # Its anchor is <=30min from the M5 event close.

    def test_reject_cvd_side_rewritten_after_freeze(self):
        d = decision()
        d["recorded_at_utc"] = "2026-11-23T04:34:00Z"
        with self.assertRaisesRegex(ValueError, "causal"):
            _decisions(ledger(d), ASOF)
        d = decision()
        d["price_only_known_at_utc"] = "2026-11-23T04:36:00Z"
        with self.assertRaisesRegex(ValueError, "future"):
            _decisions(ledger(d), ASOF)

    def test_reject_backfill_or_late_anchor(self):
        d = decision()
        d["anchor"]["committed_at_utc"] = "2026-11-23T05:05:00Z"
        with self.assertRaisesRegex(ValueError, "backfilled"):
            _decisions(ledger(d), ASOF)
        d = decision()
        d["anchor"]["committed_at_utc"] = "2026-11-24T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "window"):
            _decisions(ledger(d), ASOF)

    def test_reject_duplicate_entry_or_reused_commit_anchor(self):
        d1 = decision()
        d2 = decision(sha_number=2)
        d2["decision_id"] = "synthetic_second"
        d2["event_close_utc"] = "2026-11-23T04:35:00Z"
        d2["received_at_utc"] = "2026-11-23T04:35:15Z"
        d2["recorded_at_utc"] = "2026-11-23T04:35:20Z"
        d2["price_only_known_at_utc"] = "2026-11-23T04:35:18Z"
        d2["frozen_at_utc"] = "2026-11-23T04:36:00Z"
        d2["anchor"]["committed_at_utc"] = "2026-11-23T04:40:00Z"
        with self.assertRaisesRegex(ValueError, "duplicate"):
            _decisions(ledger(d1, d2), ASOF)
        d3 = decision(day=1, sha_number=1)
        with self.assertRaisesRegex(ValueError, "reused"):
            _decisions(ledger(d1, d3), datetime(2026, 11, 25, tzinfo=UTC))

    def test_maturation_censors_4h_24h_until_closed(self):
        r = evaluate(ledger(decision()), prices(400), as_of=ASOF)
        self.assertEqual(r["horizons"]["60m"]["complete_matched_m15_windows"], 1)
        self.assertEqual(r["horizons"]["4h"]["not_yet_mature_windows"], 1)
        self.assertEqual(r["horizons"]["24h"]["not_yet_mature_windows"], 1)

    def test_gap_not_interpolated_and_waiting_is_not_missing(self):
        r = evaluate(ledger(decision()), prices(8, gap=BASE+timedelta(minutes=15)),
                     as_of=ASOF, costs=checked_costs(1.0, 0.2))
        self.assertEqual(r["horizons"]["60m"]["missing_contiguous_m15_windows"], 1)
        self.assertEqual(r["horizons"]["60m"]["complete_matched_m15_windows"], 0)
        self.assertIsNone(r["horizons"]["60m"]["paired_cvd_minus_price_only_net_pips"])

    def test_net_pips_include_spread_and_both_slippage_sides(self):
        cost = checked_costs(1.0, 0.25)
        self.assertEqual(cost["roundtrip_pips"], 1.5)
        gross, net = _hypothetical_pips(1.1000, 1.1002, 1, cost["roundtrip_pips"])
        self.assertAlmostEqual(gross, 2.0, places=6)
        self.assertAlmostEqual(net, 0.5, places=6)
        _, flat = _hypothetical_pips(1.1000, 1.1002, 0, 1.5)
        self.assertEqual(flat, 0.0)

    def test_costs_mandatory_for_net_metrics(self):
        r = evaluate(ledger(decision()), prices(8), as_of=ASOF)
        self.assertEqual(r["cost_model"], "COSTS_MISSING")
        self.assertEqual(r["horizons"]["60m"]["metric_gate"], "COST_ASSUMPTIONS_MISSING")
        with self.assertRaises(ValueError):
            checked_costs(1.0, None)
        with self.assertRaises(ValueError):
            checked_costs(float("nan"), 0.2)

    def test_small_correlated_sample_suppressed(self):
        decisions = [decision(day=i, sha_number=i+1) for i in range(4)]
        as_of = BASE + timedelta(days=6)
        r = evaluate(ledger(*decisions), prices(6*96), as_of=as_of,
                     costs=checked_costs(0.8, 0.1))
        self.assertEqual(r["horizons"]["24h"]["complete_directional_comparisons"], 4)
        self.assertEqual(r["horizons"]["24h"]["metric_gate"], "SAMPLE_TOO_SMALL_OR_CORRELATED")
        self.assertIsNone(r["horizons"]["24h"]["net_pips"])
        self.assertFalse(r["anchor_sha_and_time_claims_externally_verified"])

    def test_paired_benchmark_math_on_synthetic_30_day_ledger(self):
        # ONLY synthetic 30 daily decisions and 31 consecutive synthetic days.
        rows = [decision(day=i, sha_number=i+1) for i in range(30)]
        as_of = BASE + timedelta(days=32)
        r = evaluate(ledger(*rows), prices(31*96), as_of=as_of,
                     costs=checked_costs(0.8, 0.1))
        for tf in ("60m", "4h", "24h"):
            h = r["horizons"][tf]
            self.assertEqual(h["complete_directional_comparisons"], 30)
            self.assertEqual(h["metric_gate"], "PROVISIONAL_DESCRIPTIVE_ONLY")
            self.assertAlmostEqual(h["paired_cvd_minus_price_only_net_pips"], 4.0, places=5)
            self.assertAlmostEqual(h["net_pips"]["cvd_mean"], 1.0, places=5)
            self.assertAlmostEqual(h["net_pips"]["price_only_mean"], -3.0, places=5)
        self.assertFalse(r["scientific_alpha_established"])
        self.assertFalse(r["independent_price_feed_authenticity_externally_verified"])
        self.assertFalse(r["trades_or_notifications_activated"])


if __name__ == "__main__":
    unittest.main()
