"""Track D0.7 offline reference-model tests. Does NOT compile Pine.

Sanity tests for clean segment continuity, a single untrusted bar after each
hole, a fixed warmup, and strictly confirmed research-only pivots.
"""
from pathlib import Path
import re
import unittest

SCRIPT = (Path(__file__).resolve().parents[1] / "experiments"
          / "tradingview" / "remura_shark_cvd_fx_v07.pine")


class SegmentReference:
    """Minimal model of eligibility decisions, not a market-data emulator."""

    def __init__(self, warmup=12):
        self.warmup = warmup
        self.prev_valid = False
        self.prev_time = None
        self.prev_day = None
        self.segment_id = 0
        self.segment_bars = 0
        self.segment_cvd = 0

    def bar(self, time_ms, day, valid, raw_delta=None):
        connected = (
            valid and self.prev_valid and self.prev_time is not None
            and time_ms - self.prev_time == 300_000 and day == self.prev_day
        )
        if not valid:
            self.segment_bars = 0
            self.segment_cvd = 0
        elif not connected:
            self.segment_id += 1
            self.segment_bars = 1
            self.segment_cvd = 0  # do not trust gap-adjacent first delta
        else:
            self.segment_bars += 1
            self.segment_cvd += raw_delta
        self.prev_valid, self.prev_time, self.prev_day = valid, time_ms, day
        return {
            "complete": bool(valid),
            "continuous": bool(connected),
            "eligible": bool(connected and self.segment_bars >= self.warmup),
            "segment_id": self.segment_id,
            "segment_bars": self.segment_bars,
            "segment_cvd": self.segment_cvd if valid and self.segment_bars >= 2 else None,
            "trusted_delta": raw_delta if connected else None,
            "raw_delta": raw_delta if valid else None,
        }


def confirmed_pivot(values, confirmation_index, left=2, right=2, *, minimum=True):
    """A candidate is invisible before its right-side confirmation bars."""
    candidate = confirmation_index - right
    if candidate < left or confirmation_index >= len(values):
        return False
    if minimum:
        return all(values[candidate] < values[i] for i in range(candidate-left, confirmation_index+1) if i != candidate)
    return all(values[candidate] > values[i] for i in range(candidate-left, confirmation_index+1) if i != candidate)


class TestD07Reference(unittest.TestCase):
    def test_untrusted_first_delta_and_clean_second(self):
        r = SegmentReference(warmup=3)
        a = r.bar(0, 1, True, raw_delta=60)
        b = r.bar(300000, 1, True, raw_delta=-20)
        c = r.bar(600000, 1, True, raw_delta=5)
        self.assertEqual((a["complete"], a["continuous"], a["trusted_delta"]), (True, False, None))
        self.assertIsNone(a["segment_cvd"])
        self.assertEqual(b["segment_cvd"], -20)
        self.assertEqual(b["trusted_delta"], -20)
        self.assertFalse(b["eligible"])
        self.assertEqual(c["segment_cvd"], -15)
        self.assertTrue(c["eligible"])

    def test_gap_or_data_hole_invalidate_and_require_new_warmup(self):
        r = SegmentReference(warmup=3)
        r.bar(0, 1, True, 100)
        r.bar(300000, 1, True, 10)
        old = r.bar(600000, 1, True, 10)
        self.assertTrue(old["eligible"])
        gap = r.bar(900000, 1, False)
        first = r.bar(1200000, 1, True, 300)
        second = r.bar(1500000, 1, True, -4)
        self.assertFalse(gap["complete"])
        self.assertFalse(first["continuous"])
        self.assertNotEqual(first["segment_id"], old["segment_id"])
        self.assertIsNone(first["trusted_delta"])
        self.assertFalse(second["eligible"])
        self.assertEqual(second["segment_cvd"], -4)

    def test_nonconsecutive_time_or_day_transition_resets_segment(self):
        r = SegmentReference(warmup=3)
        r.bar(0, 1, True, 1)
        old = r.bar(300000, 1, True, 2)
        far = r.bar(1200000, 1, True, 3)
        self.assertFalse(far["continuous"])
        self.assertNotEqual(far["segment_id"], old["segment_id"])
        next_day = r.bar(1500000, 2, True, 4)
        self.assertFalse(next_day["continuous"])
        self.assertNotEqual(next_day["segment_id"], far["segment_id"])

    def test_causal_pivot_not_visible_before_confirmation(self):
        arr = [10, 9, 7, 8]
        self.assertFalse(confirmed_pivot(arr, 3, minimum=True))
        self.assertTrue(confirmed_pivot(arr+[10], 4, minimum=True))
        self.assertFalse(confirmed_pivot([10, 9, 9, 10, 11], 4, minimum=True))

    def test_source_and_no_automatic_trading_or_alerts(self):
        p = SCRIPT.read_text(encoding="utf8")
        self.assertIn('const string FEED = "FX:EURUSD"', p)
        self.assertIn('const string MODEL = "remura_fx_1m_segment_d0.7"', p)
        self.assertIn('request.security_lower_tf(FEED, "1"', p)
        self.assertIn('fxTime - previousBarMs == 300000', p)
        self.assertIn('fxDay == previousDayKey', p)
        self.assertIn('continuousPrev := good ? (continuous ? 1.0 : 0.0)', p)
        self.assertIn('complete5m := good ? 1.0 : 0.0', p)
        self.assertIn('if not continuous', p)
        self.assertIn('segmentCvd := 0.0', p)
        self.assertIn('trustworthyDelta5m := d', p)
        self.assertIn('eligiblePivot := good and continuous and segmentBars >= warmupBars', p)
        self.assertIn('activeSegment == activeSegment[rightBars]', p)
        self.assertIn('activeSegment == activeSegment[rightBars + leftBars]', p)
        self.assertIn('eligiblePivot[rightBars] == 1.0', p)
        self.assertIn('previousLowSeg == activeSegment', p)
        self.assertIn('previousHighSeg == activeSegment', p)
        self.assertIn('ta.pivotlow(fxLow, leftBars, rightBars)', p)
        self.assertIn('ta.pivothigh(fxHigh, leftBars, rightBars)', p)
        self.assertIn('barstate.isconfirmed', p)
        self.assertIn('display=display.data_window', p)
        # On an open 5m candle, the exported per-bar value is na;
        # the UI must instead present continuity of the last CLOSED 5m.
        self.assertIn('var bool lastConfirmedPrevContinuous = false', p)
        self.assertIn('lastConfirmedPrevContinuous := good and continuous', p)
        self.assertIn('Contesto ultima 5m CHIUSA:', p)
        self.assertNotIn('"Contesto precedente: " + (continuousPrev', p)
        self.assertIn('const string MODEL = "remura_fx_1m_segment_d0.7"', p)
        self.assertNotIn('input.bool(false, "Alert', p)
        executable = "\n".join(line.split("//")[0] for line in p.splitlines())
        self.assertIsNone(re.search(r"\b(?:alert|alertcondition|strategy\.entry|strategy\.order)\s*\(", executable))


if __name__ == "__main__":
    unittest.main()
