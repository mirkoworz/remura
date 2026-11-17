"""Track D0.3 source provenance contract. Offline static checks, not Pine compilation."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "experiments/tradingview/remura_shark_cvd_fxcm_v03.pine"


class TestFxcmSourcePinned(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = PINE.read_text(encoding="utf-8")

    def test_both_price_and_volume_explicitly_fxcm(self):
        p = self.code
        self.assertIn('const string FEED = "FXCM:EURUSD"', p)
        self.assertIn('request.security(FEED, "5", [high, low, time, time("D"), close, syminfo.mintick]', p)
        self.assertIn('request.security_lower_tf(FEED, "1", [time, open, close, volume])', p)
        self.assertIn('gaps=barmerge.gaps_on', p)
        self.assertIn('lookahead=barmerge.lookahead_off', p)
        self.assertNotIn('request.security_lower_tf(syminfo.tickerid', p)

    def test_pivots_only_fxcm_and_bar_clock_guard(self):
        p = self.code
        self.assertIn('ta.pivotlow(fxL, leftBars, rightBars)', p)
        self.assertIn('ta.pivothigh(fxH, leftBars, rightBars)', p)
        self.assertIn('float p = fxL[rightBars]', p)
        self.assertIn('float p = fxH[rightBars]', p)
        self.assertIn('fxT == time', p)
        self.assertIn('tm != fxT + i * 60000', p)
        self.assertIn('n == 5', p)
        self.assertIn('validSession := false', p)

    def test_chart_alias_only_for_context_not_data(self):
        p = self.code
        self.assertIn('chartId == "FXCM:EURUSD" or chartId == "FX:EURUSD"', p)
        self.assertIn('timeframe.isminutes and timeframe.multiplier == 5', p)
        self.assertIn('Grafico: ', p)
        self.assertIn('DATI CALCOLATI: FXCM:EURUSD 5m+1m', p)

    def test_no_trading_or_automatic_alerts(self):
        p = self.code
        self.assertIn('input.bool(false, "Alert SOLO RICERCA', p)
        self.assertIn('chartOk and researchAlerts and barstate.isrealtime and barstate.isconfirmed', p)
        self.assertIn('"RESEARCH_ONLY"', p)
        self.assertIn('const string MODEL = "remura_fxcm_1m_cvd_d0.3"', p)
        for forbidden in ("strategy.entry(", "strategy.order(", "runtime.error(", "http://", "https://"):
            self.assertNotIn(forbidden, p)


if __name__ == "__main__":
    unittest.main()
