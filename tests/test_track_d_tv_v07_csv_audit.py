"""Offline quality auditor fixtures, no user CSV, no network."""
import csv
import importlib.util
import io
from pathlib import Path
import unittest

SCRIPT = (Path(__file__).resolve().parents[1] / "experiments" /
          "tradingview" / "analyze_d07_export.py")
spec = importlib.util.spec_from_file_location("d07_analyzer", SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestD07CsvAuditor(unittest.TestCase):
    header = [
        "time", "QUALITA_5M_COMPLETA", "CONTINUITA_PRECEDENTE_5M",
        "DELTA_5M_GREZZO_COMPLETO", "DELTA_5M_CONTINUO_VERIFICATO",
        "EVENTO_STUDIO_RIALZISTA", "EVENTO_STUDIO_RIBASSISTA",
        "CVD (Apertura)", "CVD (Chiudi)"
    ]

    def analyze(self, lines):
        f = io.StringIO()
        writer = csv.DictWriter(f, fieldnames=self.header)
        writer.writeheader()
        writer.writerows(lines)
        f.seek(0)
        reader = csv.DictReader(f)
        return mod.audit_rows(reader, reader.fieldnames)

    def test_continuous_matching_native_and_event_sample(self):
        x = self.analyze([
            dict(zip(self.header, ["t0", "1", "0", "50", "", "0", "0", "0", "50"])),
            dict(zip(self.header, ["t1", "1", "1", "-3", "-3", "0", "0", "15", "12"])),
            dict(zip(self.header, ["t2", "0", "", "", "", "0", "0", "", ""])),
            dict(zip(self.header, ["t3", "1", "0", "12", "", "0", "0", "0", "12"])),
            dict(zip(self.header, ["t4", "1", "1", "4", "4", "1", "0", "-2", "2"])),
            dict(zip(self.header, ["t5", "", "", "", "", "", "", "", ""])),
        ])
        self.assertEqual(x["records"], 6)
        self.assertEqual(x["complete_5m"], 4)
        self.assertEqual(x["incomplete_5m"], 1)
        self.assertEqual(x["unknown_quality"], 1)
        self.assertEqual(x["complete_with_verified_continuity"], 2)
        self.assertEqual(x["complete_but_context_unverified"], 2)
        self.assertEqual(x["numeric_comparisons_contiguous"], 2)
        self.assertEqual(x["exact_delta_matches_contiguous"], 2)
        self.assertEqual(x["exact_match_pct_contiguous"], 100.0)
        self.assertEqual(x["study_bullish_events"], 1)
        self.assertEqual(x["events_on_unverified_context"], 0)
        self.assertEqual(x["mae_contiguous"], "0")

    def test_reject_missing_quality_columns(self):
        with self.assertRaisesRegex(ValueError, "missing required columns"):
            mod.audit_rows([], ["time", "close"])

    def test_missing_native_columns_still_counts_and_is_transparent(self):
        headers = self.header[:-2]
        row = dict(zip(headers, ["t0", "1", "1", "5", "5", "0", "1"]))
        x = mod.audit_rows([row], headers)
        self.assertFalse(x["has_native_cvd_ohlc"])
        self.assertEqual(x["study_bearish_events"], 1)
        self.assertEqual(x["numeric_comparisons_contiguous"], 0)
        self.assertIsNone(x["exact_match_pct_contiguous"])

    def test_untrusted_event_and_inconsistent_reliable_delta_are_counted(self):
        row = dict(zip(self.header, ["t0", "1", "0", "2", "2", "1", "0", "0", "2"]))
        x = mod.audit_rows([row], self.header)
        self.assertEqual(x["events_on_unverified_context"], 1)
        self.assertGreater(x["context_flag_inconsistencies"], 0)

    def test_decimal_parser_does_not_interpret_na_as_zero(self):
        self.assertIsNone(mod.number(""))
        self.assertIsNone(mod.number("na"))
        self.assertIsNone(mod.number("nan"))
        self.assertIsNone(mod.number("Infinity"))
        self.assertEqual(mod.number("-17.000"), -17)


if __name__ == "__main__":
    unittest.main()
