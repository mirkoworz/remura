"""Track D FXCM CVD: offline SPECIFICATION/model tests, NOT Pine compilation.

No TradingView connection, brokerage data, secrets, network, notifications or LIVE.
The Python reference mirrors the D0.1 assumptions so drift can be detected
by inspection. Visual/runtime compilation on TradingView remains a hard gate.
"""
from __future__ import annotations

import unittest
from pathlib import Path

BAR_MS = 5 * 60 * 1000


class DayAccumulator:
    """Conservative 1m direction inference and day-anchored cumulative sum."""

    def __init__(self):
        self.day = None
        self.last_time = None
        self.last_close = None
        self.last_side = 0
        self.cvd = 0.0
        self.healthy = True

    def consume(self, *, day: int, time_ms: int, intrabars: list[tuple]):
        if day != self.day:
            self.day = day
            self.last_time = None
            self.last_close = None
            self.last_side = 0
            self.cvd = 0.0
            self.healthy = True
        if self.last_time is not None and time_ms - self.last_time != BAR_MS:
            self.healthy = False
        self.last_time = time_ms
        if len(intrabars) != 5:
            self.healthy = False
        if not self.healthy:
            return None
        delta = 0.0
        for o, c, v in intrabars:
            if any(x is None for x in (o, c, v)) or v < 0:
                self.healthy = False
                return None
            if c > o:
                side = 1
            elif c < o:
                side = -1
            elif self.last_close is not None and c > self.last_close:
                side = 1
            elif self.last_close is not None and c < self.last_close:
                side = -1
            else:
                side = self.last_side
            delta += side * v
            self.last_close = c
            self.last_side = side
        self.cvd += delta
        return self.cvd


def confirmed_extreme(series: list[float], center: int, left: int, right: int, *, low: bool):
    """Return false until the last confirming bar exists (no look-ahead)."""
    if center - left < 0 or center + right >= len(series):
        return False
    neighbors = [series[k] for k in range(center - left, center + right + 1) if k != center]
    return all(series[center] < v for v in neighbors) if low else all(series[center] > v for v in neighbors)


def regular_divergence(price1, price2, cvd1, cvd2, *, low: bool, min_price: float, min_cvd: float):
    if low:
        return price2 < price1 - min_price and cvd2 > cvd1 + min_cvd
    return price2 > price1 + min_price and cvd2 < cvd1 - min_cvd


class TestDayAccumulator(unittest.TestCase):
    def test_1m_buy_sell_and_equal_price_continuation(self):
        acc = DayAccumulator()
        # +4 -3 -2 +5 +7 = +11 (the last equal bar inherits positive side)
        bars = [(10, 11, 4), (11, 10, 3), (10, 9, 2),
                (9, 10, 5), (10, 10, 7)]
        self.assertEqual(acc.consume(day=1, time_ms=0, intrabars=bars), 11.0)

    def test_cumulative_and_daily_reset(self):
        acc = DayAccumulator()
        buys = [(1, 2, 3)] * 5
        sells = [(2, 1, 1)] * 5
        self.assertEqual(acc.consume(day=1, time_ms=0, intrabars=buys), 15.0)
        self.assertEqual(acc.consume(day=1, time_ms=BAR_MS, intrabars=sells), 10.0)
        self.assertEqual(acc.consume(day=2, time_ms=2 * BAR_MS, intrabars=sells), -5.0)

    def test_missing_minute_stops_session_not_fabricated(self):
        acc = DayAccumulator()
        bars = [(1, 2, 1)] * 5
        self.assertEqual(acc.consume(day=1, time_ms=0, intrabars=bars), 5.0)
        self.assertIsNone(acc.consume(day=1, time_ms=BAR_MS, intrabars=bars[:4]))
        self.assertIsNone(acc.consume(day=1, time_ms=2 * BAR_MS, intrabars=bars))
        self.assertEqual(acc.consume(day=2, time_ms=3 * BAR_MS, intrabars=bars), 5.0)

    def test_gap_rejected(self):
        acc = DayAccumulator()
        bars = [(1, 2, 1)] * 5
        self.assertEqual(acc.consume(day=1, time_ms=0, intrabars=bars), 5.0)
        self.assertIsNone(acc.consume(day=1, time_ms=3 * BAR_MS, intrabars=bars))

    def test_negative_volume_rejected(self):
        acc = DayAccumulator()
        self.assertIsNone(acc.consume(day=1, time_ms=0,
                                      intrabars=[(1, 2, 1)] * 4 + [(1, 2, -1)]))


class TestCausalDivergence(unittest.TestCase):
    def test_pivot_cannot_confirm_before_right_bars(self):
        points = [10, 9, 8, 9]
        self.assertFalse(confirmed_extreme(points, 2, 2, 2, low=True))
        self.assertTrue(confirmed_extreme(points + [10], 2, 2, 2, low=True))

    def test_regular_bullish_and_bearish_not_reverse(self):
        self.assertTrue(regular_divergence(1.1010, 1.1000, -50, -25,
                                           low=True, min_price=.0001, min_cvd=10))
        self.assertTrue(regular_divergence(1.1000, 1.1010, 50, 25,
                                           low=False, min_price=.0001, min_cvd=10))
        self.assertFalse(regular_divergence(1.1010, 1.1000, -50, -60,
                                            low=True, min_price=.0001, min_cvd=10))

    def test_equal_extreme_does_not_count(self):
        self.assertFalse(confirmed_extreme([10, 9, 9, 10, 11], 2, 2, 2, low=True))
        self.assertFalse(regular_divergence(1.1, 1.1, 1, 20,
                                            low=True, min_price=0, min_cvd=0))

    def test_threshold_is_strict(self):
        self.assertFalse(regular_divergence(10, 9, 10, 20,
                                            low=True, min_price=1, min_cvd=10))


class TestPineSafetyContract(unittest.TestCase):
    def test_pine_kept_out_of_live_and_research_alert_opt_in(self):
        pine = (Path(__file__).resolve().parents[1]
                / "experiments" / "tradingview" / "remura_shark_cvd_fxcm_v01.pine").read_text()
        self.assertIn('syminfo.prefix != "FXCM"', pine)
        self.assertIn('timeframe.period != "5"', pine)
        self.assertIn('input.bool(false, "Abilita alert', pine)
        self.assertIn('barstate.isconfirmed', pine)
        self.assertIn('request.security_lower_tf', pine)
        self.assertIn('completeSession := false', pine)
        self.assertIn('"RESEARCH_ONLY"', pine)
        self.assertNotIn('strategy.entry(', pine)
        self.assertNotIn('strategy.order(', pine)


if __name__ == "__main__":
    unittest.main()
