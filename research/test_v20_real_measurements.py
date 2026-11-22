# REMURA V20 — only NEW tests of the offline real-history measurement engine.
# No market fixtures used for claims of actual REMURA metrics; tiny samples check math.
import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0, str(Path(__file__).resolve().parent))
from v20_real_measurements import parse_utc, scan_directory, summarize_records

AS_OF = parse_utc("2026-11-22T22:33:00Z")


def record(t, long_pct=60, short_pct=40):
    return {"t": t, "lPct": long_pct, "sPct": short_pct}


class RealMeasurementsV20Tests(unittest.TestCase):
    def test_01_cadence_and_persistent_percent(self):
        r = summarize_records([
            record("2026-11-20T00:00:00Z"),
            record("2026-11-20T06:00:00Z"),
            record("2026-11-20T20:00:00Z", 55, 45),
        ], AS_OF)
        self.assertEqual(r["observations"], 3)
        self.assertEqual(r["adjacent_pairs"], 2)
        self.assertEqual(r["unchanged_long_pct_pairs"], 1)
        self.assertEqual(r["median_interval_hours"], 10)
        self.assertEqual(r["gaps_over_12_hours"], 1)

    def test_02_duplicate_and_invalid_percentage(self):
        r = summarize_records([
            record("2026-11-22T00:00:00Z"),
            record("2026-11-22T00:00:00Z", 61, 39),
            record("2026-11-22T04:00:00Z", 110, -10),
        ], AS_OF)
        self.assertEqual(r["duplicate_timestamps"], 1)
        self.assertEqual(r["invalid_percentage_records"], 1)
        self.assertEqual(r["median_interval_hours"], 4)

    def test_03_no_lookahead_and_timezone_guards(self):
        with self.assertRaisesRegex(ValueError, "future timestamp"):
            summarize_records([record("2026-11-23T01:00:00Z")], AS_OF)
        with self.assertRaises(ValueError):
            parse_utc("2026-11-22T22:33:00")
        with self.assertRaises(ValueError):
            parse_utc("2026-11-22T22:33:00+01:00")

    def test_04_stale_public_flag_but_private_never_lists_symbols(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            for symbol, when in [
                ("EURUSD", "2026-11-22T21:33:00Z"),
                ("US500", "2026-10-22T01:38:06Z"),
            ]:
                (root / (symbol + ".json")).write_text(
                    json.dumps({"symbol": symbol, "records": [record(when)]}),
                    encoding="utf-8",
                )
            public = scan_directory(root, AS_OF, show_stale_names=True)
            self.assertEqual(public["series_count"], 2)
            self.assertEqual(public["stale_public_series"], ["US500"])
            private = scan_directory(root, AS_OF, show_stale_names=False)
            self.assertNotIn("stale_public_series", private)
            self.assertNotIn("EURUSD", json.dumps(private))
            self.assertNotIn("US500", json.dumps(private))

    def test_05_fail_closed_mismatch_and_empty_directory(self):
        with TemporaryDirectory() as folder:
            root = Path(folder)
            with self.assertRaisesRegex(ValueError, "no historical series"):
                scan_directory(root, AS_OF, show_stale_names=True)
            (root / "EURUSD.json").write_text(
                json.dumps({"symbol": "GBPUSD", "records": [record("2026-11-22T21:00:00Z")]}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "mismatch"):
                scan_directory(root, AS_OF, show_stale_names=True)

    def test_06_reject_boolean_pct_and_empty_records(self):
        with self.assertRaises(ValueError):
            summarize_records([], AS_OF)
        r = summarize_records([
            record("2026-11-22T12:00:00Z", True, 99),
        ], AS_OF)
        self.assertEqual(r["invalid_percentage_records"], 1)


if __name__ == "__main__":
    unittest.main()
