"""Track D0.4 FX:EURUSD provenance and runtime-safety static tests (NOT Pine compilation)."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "experiments" / "tradingview" / "remura_shark_cvd_fx_v04.pine"


class TestCanonicalFxEurusd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = PINE.read_text(encoding="utf-8")

    def test_only_accessible_canonical_symbol_used(self):
        p = self.s
        self.assertIn('const string FEED = "FX:EURUSD"', p)
        self.assertIn('request.security(FEED, "5"', p)
        self.assertIn('request.security_lower_tf(FEED, "1"', p)
        self.assertIn('chartId == "FX:EURUSD"', p)
        self.assertNotIn('const string FEED = "FXCM:EURUSD"', p)
        self.assertNotIn('request.security_lower_tf(syminfo.tickerid', p)
        self.assertIn('ignore_invalid_symbol=true', p)
        self.assertIn('gaps=barmerge.gaps_on', p)
        self.assertIn('lookahead=barmerge.lookahead_off', p)

    def test_no_cross_provider_price_pivots(self):
        p = self.s
        self.assertIn('ta.pivotlow(fxL, leftBars, rightBars)', p)
        self.assertIn('ta.pivothigh(fxH, leftBars, rightBars)', p)
        self.assertIn('float p = fxL[rightBars]', p)
        self.assertIn('float p = fxH[rightBars]', p)
        self.assertIn('fxT == time', p)
        self.assertIn('tm != fxT + i * 60000', p)
        self.assertIn('validSession := false', p)
        self.assertIn('Minuti 1m ultima 5m chiusa:', p)

    def test_research_only_no_outbound_effects(self):
        p = self.s
        self.assertIn('input.bool(false, "Alert SOLO RICERCA', p)
        self.assertIn('chartOk and researchAlerts and barstate.isrealtime and barstate.isconfirmed', p)
        self.assertIn('"RESEARCH_ONLY"', p)
        self.assertIn('const string MODEL = "remura_fx_1m_cvd_d0.4"', p)
        self.assertIn('"source":"TV_FX_EURUSD_TICK_VOLUME_PROXY_1M"', p)
        for banned in ('strategy.entry(', 'strategy.order(', 'runtime.error(', 'http://', 'https://'):
            self.assertNotIn(banned, p)


if __name__ == "__main__":
    unittest.main()
