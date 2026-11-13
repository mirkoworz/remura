"""D0.6 offline source contract and numeric parity protocol (not Pine compiler)."""
from pathlib import Path
import unittest

HERE = Path(__file__).resolve().parents[1]
SCRIPT = HERE / "experiments" / "tradingview" / "remura_shark_cvd_fx_v06.pine"


class TestBarDeltaComparison(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pine = SCRIPT.read_text(encoding="utf8")

    def test_same_symbol_and_complete_intrabar_gate(self):
        p = self.pine
        self.assertIn('const string FEED = "FX:EURUSD"', p)
        self.assertIn('request.security(FEED, "5"', p)
        self.assertIn('request.security_lower_tf(FEED, "1"', p)
        self.assertIn('barstate.isconfirmed', p)
        self.assertIn('n != 5', p)
        self.assertIn('tm != fxT + i * 60000', p)
        self.assertIn('coverage5m := barValid ? 1.0 : 0.0', p)
        self.assertIn('deltaVerified5m := delta', p)
        self.assertIn('lastVerifiedDelta := delta', p)
        self.assertLess(p.index('if not barValid\n'), p.index('deltaVerified5m := delta'))

    def test_comparison_outputs_do_not_overwrite_partial_or_signals(self):
        p = self.pine
        self.assertIn('"DELTA 5M REMURA verificato", display=display.data_window + display.status_line', p)
        self.assertIn('"QUALITA 5M (1 valida / 0 incompleta)", display=display.data_window', p)
        self.assertIn('"NUMERO INTRABAR 1M", display=display.data_window', p)
        self.assertIn('lastVerifiedDeltaEndMs = na', p)
        self.assertIn('str.format_time(lastVerifiedDeltaEndMs, "dd/MM HH:mm", "Europe/Rome")', p)
        self.assertIn('partialPlot := segmentBars >= 2 ? segmentCvd : na', p)
        self.assertIn('if chartOk and barstate.isconfirmed and validSession and not na(cvd)', p)
        self.assertIn('input.bool(false, "Alert SOLO RICERCA', p)
        self.assertIn('if chartOk and researchAlerts and barstate.isrealtime and barstate.isconfirmed', p)
        self.assertNotIn('strategy.entry(', p)
        self.assertNotIn('strategy.order(', p)

    def test_native_cvd_ohlc_bar_difference_protocol(self):
        # TradingView CVD candle open is previous cumulative close (or 0
        # at an anchor reset); native closed-bar delta is close - open.
        native_open, native_close = -150, -92
        remura_verified_delta = 58
        self.assertEqual(native_close - native_open, remura_verified_delta)
        # Cumulative close would be the WRONG quantity for comparison.
        self.assertNotEqual(native_close, remura_verified_delta)


if __name__ == "__main__":
    unittest.main()
