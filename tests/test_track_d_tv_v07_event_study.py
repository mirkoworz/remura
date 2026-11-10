"""Deterministic fixtures for D0.7 offline event-outcome evaluator."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / "experiments/tradingview/evaluate_d07_events.py"
spec = importlib.util.spec_from_file_location("track_d07_event_study", MODULE)
study = importlib.util.module_from_spec(spec)
spec.loader.exec_module(study)


def bars(count=13, side="bull"):
    out = []
    for j in range(count):
        r = {
            "time": str(j * 300),
            "close": f"{1.10000 + j * .0001:.5f}",
            "QUALITA_5M_COMPLETA": "1",
            "CONTINUITA_PRECEDENTE_5M": "1",
            "SEGMENTO_ELIGIBILE_STUDIO": "1",
            "EVENTO_STUDIO_RIALZISTA": "1" if j == 0 and side == "bull" else "0",
            "EVENTO_STUDIO_RIBASSISTA": "1" if j == 0 and side == "bear" else "0",
        }
        out.append(r)
    return out


class TestD07EventStudy(unittest.TestCase):
    def test_close_of_confirmation_bar_and_exact_one_hour(self):
        result = study.outcome_audit(bars())
        self.assertEqual(result["study_events_eligible"], 1)
        self.assertEqual(result["horizons"]["1h"]["observed"], 1)
        self.assertEqual(result["horizons"]["1h"]["mean_pips"], 12.0)
        self.assertEqual(result["horizons"]["4h"]["observed"], 0)
        self.assertTrue(result["events"][0]["confirmed_at_italy"].endswith("+01:00"))
        self.assertEqual(result["events"][0]["confirmed_at_italy"][11:16], "01:05")

    def test_bearish_sign_reversed(self):
        result = study.outcome_audit(bars(side="bear"))
        self.assertEqual(result["horizons"]["1h"]["mean_pips"], -12.0)
        self.assertEqual(result["horizons"]["1h"]["directionally_positive"], 0)

    def test_gap_or_still_open_target_suppresses_future_label(self):
        rows = bars()
        rows.pop(7)  # one 5m gap: never jump across it to the next target
        self.assertEqual(study.outcome_audit(rows)["horizons"]["1h"]["observed"], 0)
        rows = bars()
        rows[-1]["QUALITA_5M_COMPLETA"] = ""
        self.assertEqual(study.outcome_audit(rows)["horizons"]["1h"]["observed"], 0)

    def test_invalid_signal_is_not_measured(self):
        rows = bars()
        rows[0]["CONTINUITA_PRECEDENTE_5M"] = "0"
        result = study.outcome_audit(rows)
        self.assertEqual(result["study_events_eligible"], 0)
        self.assertEqual(len(result["study_events_rejected"]), 1)

    def test_reject_duplicate_or_out_of_order_timestamps(self):
        data = bars()
        data[1]["time"] = data[0]["time"]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            study.outcome_audit(data)
        with self.assertRaisesRegex(ValueError, "Missing D0.7 columns"):
            study.outcome_audit([{"time": "1", "close": "1.0"}])


if __name__ == "__main__":
    unittest.main()
