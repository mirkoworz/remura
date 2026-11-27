#!/usr/bin/env python3
# REMURA v0.8.58 LAB — 14/11/2026 11:50 CET. Static checks, NOT Pine compilation.
from pathlib import Path
import re,unittest

HERE=Path(__file__).resolve().parent
old=(HERE/"REMURA-ALL-IN-ONE-Premium-v0.8-TELEMETRY.pine").read_text()
new=(HERE/"REMURA-ALL-IN-ONE-Premium-v0.9-CVD-LAB.pine").read_text()

class IntegratedPineTests(unittest.TestCase):
    def test_original_delta_body_preserved(self):
        a=old.split("// DELTA STIMATO DA TIMEFRAME INFERIORE",1)[1].split("// DATI E ALLARMI",1)[0]
        b=new.split("// DELTA STIMATO DA TIMEFRAME INFERIORE",1)[1].split("// === CVD D0.8 PORT",1)[0]
        self.assertEqual(a.replace("LAB v0.8.1","LAB v0.9").strip(),b.strip())
    def test_visual_only_no_alerts(self):
        self.assertNotRegex(new,r"\balert(?:condition)?\s*\(")
        self.assertNotIn("telemetryEnabled",new)
        self.assertIn("alert(payload, alert.freq_once_per_bar_close)",old)
    def test_one_footprint(self):
        self.assertEqual(len(re.findall(r"=\s*request\.footprint\(",new)),1)
    def test_feed_and_timeframe_gate(self):
        self.assertIn('chart.is_standard and (cvd_chartId == "FX:EURUSD" or cvd_chartId == "FXCM:EURUSD")',new)
        self.assertIn('timeframe.multiplier == 5 and lowerTF == "1"',new)
        self.assertIn('request.security_lower_tf(syminfo.tickerid, "1"',new)
    def test_continuity_and_quality_guards(self):
        self.assertIn("else if n != 5",new)
        self.assertIn("tm != cvd_fxTime + i * 60000",new)
        self.assertIn("cvd_fxTime - cvd_previousBarMs == 300000",new)
        self.assertIn("cvd_segmentBars := 0",new)
        self.assertIn("cvd_validDay := false",new)
        self.assertIn("cvd_segmentBars >= cvd_warmupBars",new)
    def test_benchmark_subset_and_confirmation(self):
        self.assertIn("cvd_bullishStudy := cvd_bullishPriceOnly and",new)
        self.assertIn("cvd_bearishStudy := cvd_bearishPriceOnly and",new)
        self.assertIn("if cvd_chartOk and barstate.isconfirmed and cvd_eligiblePivot",new)
        self.assertNotRegex(new,r"offset\s*=\s*-")
        self.assertIn("CVD_DELTA_MENO_DELTA_NATIVO",new)
    def test_plot_budget_static(self):
        self.assertLess(len(re.findall(r"(?m)^plot(?:shape)?\(",new)),40)
        self.assertIn("position.bottom_left",new)
        self.assertIn("position.top_right",new)
if __name__=="__main__":
    unittest.main()
