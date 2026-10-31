"""Offline safety tests for REMURA Shark Science Lab. No network / VPS."""
import datetime as dt
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import shark_science as lab

UTC = dt.timezone.utc
START = dt.datetime(2026, 10, 26, 8, 0, tzinfo=UTC)


def candles(n=96, *, step=0.0001, gap_after=None):
    rows = []
    for i in range(n):
        moment = START + dt.timedelta(minutes=15 * (i + (1 if gap_after is not None and i > gap_after else 0)))
        op = 1.0 + step * i
        cl = op + step / 2 if step > 0 else op + step / 2
        hi = max(op, cl) + 0.00002
        lo = min(op, cl) - 0.00002
        rows.append({"t": moment.isoformat(), "o": op,
                     "h": hi, "l": lo, "c": cl})
    return rows


def as_of(rows):
    return (dt.datetime.fromisoformat(rows[-1]["t"]) + dt.timedelta(minutes=15)).isoformat()


class SharkScienceTests(unittest.TestCase):
    def run_lab(self, rows, **kwargs):
        return lab.evaluate(rows, as_of=as_of(rows), round_trip_cost_bps=1.5, **kwargs)

    def test_breakout_after_close_then_next_open_and_costs(self):
        rows = candles()
        result = self.run_lab(rows)
        self.assertEqual(result["verdict"], "research_only_never_live_signal")
        self.assertEqual(result["execution"], "next_bar_open_to_closed_bar_close")
        self.assertGreater(result["all"]["trades"], 0)
        self.assertEqual(result["all"]["evidence"], "insufficient")
        expensive = lab.evaluate(rows, as_of=as_of(rows), round_trip_cost_bps=5.5)
        self.assertAlmostEqual(result["all"]["netMeanBps"] - expensive["all"]["netMeanBps"], 4.0, places=3)
        self.assertNotIn("tradesDetail", result)

    def test_false_positive_prevented_for_flat_market(self):
        rows = candles(step=0.0)
        value = self.run_lab(rows)
        self.assertEqual(value["all"]["trades"], 0)
        self.assertIsNone(value["holdout"]["netMeanBps"])

    def test_gaps_are_never_interpolated(self):
        intact = candles(18)
        with_gap = candles(18, gap_after=12)
        self.assertGreater(self.run_lab(intact, lookback=12)["all"]["trades"], 0)
        self.assertEqual(self.run_lab(with_gap, lookback=12)["all"]["trades"], 0)

    def test_no_closed_bar_no_backtest(self):
        rows = candles()
        before_last_close = dt.datetime.fromisoformat(rows[-1]["t"]) + dt.timedelta(minutes=14)
        with self.assertRaisesRegex(ValueError, "incomplete_or_future_bar"):
            lab.evaluate(rows, as_of=before_last_close, round_trip_cost_bps=2)

    def test_duplicated_or_wrong_timestamp_rejected(self):
        rows = candles(30)
        with self.assertRaisesRegex(ValueError, "out_of_order_or_duplicate"):
            self.run_lab(rows + [rows[-1]])
        rows[5]["t"] = rows[5]["t"].replace("+00:00", "")  # naive timestamp
        with self.assertRaisesRegex(ValueError, "timestamp_requires_timezone"):
            self.run_lab(rows)

    def test_invalid_ohlc_and_missing_costs_rejected(self):
        rows = candles()
        rows[2]["h"] = rows[2]["l"]
        with self.assertRaisesRegex(ValueError, "invalid_ohlc"):
            self.run_lab(rows)
        with self.assertRaisesRegex(ValueError, "explicit_positive_cost_required"):
            lab.evaluate(candles(), as_of=as_of(candles()), round_trip_cost_bps=0)

    def test_holdout_is_chronologically_separate_by_week(self):
        rows = candles(1900)
        result = self.run_lab(rows, hold_bars=4)
        self.assertGreater(result["train"]["trades"], 0)
        self.assertGreater(result["holdout"]["trades"], 0)
        self.assertEqual(result["train"]["trades"] + result["holdout"]["trades"],
                         result["all"]["trades"])
        self.assertNotEqual(result["train"]["weeks"], 0)

    def test_pullback_is_a_separate_hypothesis(self):
        rows = candles(150)
        value = self.run_lab(rows, strategy="pullback")
        self.assertEqual(value["strategy"], "pullback")
        self.assertEqual(value["verdict"], "research_only_never_live_signal")
        with self.assertRaisesRegex(ValueError, "unsupported_strategy"):
            self.run_lab(rows, strategy="pretend-institutional")

    def test_future_mutation_does_not_change_prior_signal(self):
        rows = lab._bars(candles(80), as_of(candles(80)))
        observed = lab._direction(rows, 30, "breakout", 12)
        changed = list(rows)
        for i in range(31, len(changed)):
            t, op, hi, lo, cl = changed[i]
            changed[i] = (t, op, hi * 1.2, lo * 0.8, cl)
        self.assertEqual(observed, lab._direction(changed, 30, "breakout", 12))


if __name__ == "__main__":
    unittest.main()
