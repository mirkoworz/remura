"""D0.8 offline fixtures: fair baseline cohorts, no lookahead, no trading."""
from datetime import datetime
from decimal import Decimal
import importlib.util
import re
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PINE = ROOT / "experiments/tradingview/remura_shark_cvd_fx_v08.pine"
CODE = ROOT / "experiments/tradingview/compare_d08_baseline.py"
spec = importlib.util.spec_from_file_location("d08_compare", CODE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def make_rows(n=302):
    pips = Decimal("0.0001")
    starting = Decimal("1.10000")
    rows = []
    for i in range(n):
        rows.append({
            "time": str(i * 300),
            "close": str(starting + i * pips),
            "QUALITA_5M_COMPLETA": "1",
            "CONTINUITA_PRECEDENTE_5M": "1",
            "SEGMENTO_ELIGIBILE_STUDIO": "1",
            "EVENTO_STUDIO_RIALZISTA": "1" if i == 0 else "0",
            "EVENTO_STUDIO_RIBASSISTA": "0",
            "BASELINE_PREZZO_RIALZISTA": "1" if i == 0 else "0",
            "BASELINE_PREZZO_RIBASSISTA": "1" if i == 13 else "0",
        })
    return rows


class TestD08Baseline(unittest.TestCase):
    def test_nested_cohorts_and_directional_outcomes(self):
        out = mod.evaluate(make_rows())
        cohorts = out["cohorts"]
        self.assertEqual(cohorts["price_all"]["events"], 2)
        self.assertEqual(cohorts["cvd_selected"]["events"], 1)
        self.assertEqual(cohorts["price_rejected_by_cvd"]["events"], 1)
        self.assertEqual(cohorts["cvd_selected"]["horizons"]["1h"]["mean_pips"], 12)
        self.assertEqual(cohorts["price_rejected_by_cvd"]["horizons"]["1h"]["mean_pips"], -12)
        self.assertEqual(out["mean_cvd_minus_rejected_pips"]["1h"], 24)
        self.assertEqual(cohorts["price_all"]["horizons"]["24h"]["observable"], 2)
        self.assertEqual(out["mode"], "EXPLORATORY_HISTORICAL")

    def test_strict_closing_confirmation_and_future_gaps(self):
        data = make_rows()
        data.pop(8)
        out = mod.evaluate(data)
        self.assertEqual(out["cohorts"]["cvd_selected"]["horizons"]["1h"]["observable"], 0)
        # The later price-only candidate has an intact 1h window.
        self.assertEqual(out["cohorts"]["price_rejected_by_cvd"]["horizons"]["1h"]["observable"], 1)
        data = make_rows()
        data[12]["QUALITA_5M_COMPLETA"] = ""
        self.assertEqual(mod.evaluate(data)["cohorts"]["cvd_selected"]["horizons"]["1h"]["observable"], 0)

    def test_prospective_cutoff_must_be_predeclared_and_aware(self):
        cutoff = datetime.fromisoformat("1970-01-01T01:00:00+00:00")
        out = mod.evaluate(make_rows(), prospective_from=cutoff)
        self.assertEqual(out["mode"], "PROSPECTIVE_CUTOFF_SUPPLIED")
        self.assertEqual(out["cohorts"]["cvd_selected"]["events"], 0)
        self.assertEqual(out["cohorts"]["price_rejected_by_cvd"]["events"], 1)
        with self.assertRaisesRegex(ValueError, "fuso orario"):
            mod.evaluate(make_rows(), prospective_from=datetime(2026, 11, 10))

    def test_reject_subset_violation_and_ambiguous_signal(self):
        data = make_rows(n=20)
        data[5]["EVENTO_STUDIO_RIBASSISTA"] = "1"  # CVD without price candidate
        data[6]["BASELINE_PREZZO_RIALZISTA"] = "1"
        data[6]["BASELINE_PREZZO_RIBASSISTA"] = "1"
        out = mod.evaluate(data)
        self.assertEqual(out["quality_problems"]["cvd_not_subset_of_price"], 1)
        self.assertEqual(out["quality_problems"]["dual_direction_ambiguous"], 1)

    def test_untrusted_candidate_does_not_count_and_missing_columns_fail(self):
        data = make_rows(n=30)
        data[0]["CONTINUITA_PRECEDENTE_5M"] = "0"
        result = mod.evaluate(data)
        self.assertEqual(result["quality_problems"]["quality_mask_rejected"], 1)
        self.assertEqual(result["cohorts"]["cvd_selected"]["events"], 0)
        with self.assertRaisesRegex(ValueError, "colonne mancanti"):
            mod.evaluate([{"time": "1", "close": "1.10000"}])

    def test_pine_study_only_and_exact_matched_gate(self):
        p = PINE.read_text(encoding="utf8")
        self.assertIn('const string MODEL = "remura_fx_price_vs_cvd_d0.8"', p)
        self.assertIn('const string FEED = "FX:EURUSD"', p)
        self.assertIn('request.security_lower_tf(FEED, "1"', p)
        self.assertIn('activeSegment == activeSegment[rightBars]', p)
        self.assertIn('eligiblePivot[rightBars] == 1.0', p)
        self.assertIn('bullishStudy := bullishPriceOnly and pointCvd > previousLowCvd', p)
        self.assertIn('bearishStudy := bearishPriceOnly and pointCvd < previousHighCvd', p)
        self.assertIn('"BASELINE_PREZZO_RIALZISTA"', p)
        self.assertIn('"BASELINE_PREZZO_RIBASSISTA"', p)
        self.assertIn('"PREZZO_SENZA_CVD_RIALZISTA"', p)
        self.assertIn('display=display.data_window', p)
        self.assertIn('barstate.isconfirmed', p)
        executable = "\n".join(line.split("//")[0] for line in p.splitlines())
        self.assertIsNone(re.search(r"\b(?:alert|alertcondition|strategy\.entry|strategy\.order)\s*\(", executable))
        self.assertNotIn("https://", p)


if __name__ == "__main__":
    unittest.main()
