"""Private D0.8 snapshot ledger: synthetic tests, no provider data or network."""
import csv
from datetime import datetime
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

SRC = Path(__file__).resolve().parents[1] / "experiments/tradingview/record_d08_snapshots.py"
spec = importlib.util.spec_from_file_location("d08_snapshots", SRC)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

T0 = int(datetime.fromisoformat("2026-11-10T12:20:00+01:00").timestamp())
RECEIVED1 = datetime.fromisoformat("2026-11-10T13:00:00+01:00")
RECEIVED2 = datetime.fromisoformat("2026-11-10T13:15:00+01:00")


def candle(index, *, price=False, cvd=False, quality="1", close="1.12345"):
    row = {name: "0" for name in mod.FIELDS}
    row.update({
        "time": str(T0 + index * 300),
        "close": close,
        "QUALITA_5M_COMPLETA": quality,
        "CONTINUITA_PRECEDENTE_5M": "1",
        "SEGMENTO_ELIGIBILE_STUDIO": "1",
        "BASELINE_PREZZO_RIALZISTA": "1" if price else "0",
        "EVENTO_STUDIO_RIALZISTA": "1" if cvd else "0",
    })
    return row


def write_csv(path, rows):
    with path.open("w", newline="", encoding="utf8") as f:
        writer = csv.DictWriter(f, fieldnames=mod.FIELDS)
        writer.writeheader()
        writer.writerows(rows)


class TestPrivateD08Snapshots(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.csv = self.root / "FX_EURUSD_5.csv"
        self.ledger = self.root / "private" / "snapshots.json"

    def test_baseline_then_new_bar_and_exact_duplicate(self):
        write_csv(self.csv, [candle(0, price=True), candle(1)])
        first = mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)
        self.assertEqual(first["status"], "recorded_baseline")
        self.assertEqual(first["snapshot"]["new_event_classes"]["historical_at_baseline"], 1)
        before = self.ledger.read_text()
        self.assertNotIn("1.12345", before)  # no provider close prices in ledger
        write_csv(self.csv, [candle(0, price=True), candle(1),
                             candle(2, price=True, cvd=True)])
        second = mod.ingest(self.csv, self.ledger, RECEIVED2)
        self.assertEqual(second["snapshot"]["new_event_classes"]["new_on_new_bar"], 1)
        self.assertEqual(second["snapshot"]["new_event_classes"]["backfill_or_recalculation"], 0)
        self.assertEqual(second["snapshot"]["overlapping_rows_changed"], 0)
        unchanged = self.ledger.read_bytes()
        duplicate = mod.ingest(self.csv, self.ledger, RECEIVED2)
        self.assertEqual(duplicate["status"], "duplicate_unchanged")
        self.assertEqual(self.ledger.read_bytes(), unchanged)
        self.assertEqual(len(json.loads(unchanged)["snapshots"]), 2)

    def test_old_signal_appearing_later_is_backfill_not_prospective(self):
        write_csv(self.csv, [candle(0), candle(1)])
        mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)
        write_csv(self.csv, [candle(0, price=True, cvd=True), candle(1)])
        result = mod.ingest(self.csv, self.ledger, RECEIVED2)
        self.assertEqual(result["snapshot"]["new_event_classes"]["backfill_or_recalculation"], 1)
        self.assertEqual(result["snapshot"]["new_event_classes"]["new_on_new_bar"], 0)
        self.assertEqual(result["snapshot"]["overlapping_rows_changed"], 1)

    def test_existing_signal_upgraded_to_cvd_is_revision_not_new(self):
        write_csv(self.csv, [candle(0, price=True), candle(1)])
        mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)
        write_csv(self.csv, [candle(0, price=True, cvd=True), candle(1)])
        result = mod.ingest(self.csv, self.ledger, RECEIVED2)
        self.assertEqual(result["snapshot"]["new_study_events_total"], 0)
        self.assertEqual(result["snapshot"]["overlapping_rows_changed"], 1)

    def test_live_unconfirmed_bar_ignored_and_not_historically_valid(self):
        write_csv(self.csv, [candle(0), candle(1, quality="")])
        result = mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)
        self.assertEqual(result["snapshot"]["confirmed_rows"], 1)
        self.assertEqual(result["snapshot"]["new_study_events_total"], 0)

    def test_errors_for_invalid_provenance_and_unqualified_events(self):
        write_csv(self.csv, [candle(0), candle(1)])
        with self.assertRaisesRegex(ValueError, "baseline"):
            mod.ingest(self.csv, self.ledger, RECEIVED1)
        with self.assertRaisesRegex(ValueError, "timezone-aware"):
            mod.ingest(self.csv, self.ledger, datetime(2026, 11, 10, 13), baseline=True)
        with self.assertRaisesRegex(ValueError, "OUTSIDE"):
            mod.ingest(self.csv, SRC.parent / "private_ledger.json", RECEIVED1, baseline=True)
        with self.assertRaisesRegex(ValueError, "confirmed candle after"):
            mod.ingest(self.csv, self.ledger, datetime.fromisoformat("2026-11-10T12:21:00+01:00"), baseline=True)
        write_csv(self.csv, [candle(0, cvd=True)])
        with self.assertRaisesRegex(ValueError, "without price-only"):
            mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)

    def test_timestamp_order_and_stale_exports_do_not_modify_ledger(self):
        write_csv(self.csv, [candle(0), candle(1)])
        mod.ingest(self.csv, self.ledger, RECEIVED1, baseline=True)
        initial = self.ledger.read_bytes()
        write_csv(self.csv, [candle(0)])
        with self.assertRaisesRegex(ValueError, "Stale"):
            mod.ingest(self.csv, self.ledger, RECEIVED2)
        self.assertEqual(initial, self.ledger.read_bytes())
        write_csv(self.csv, [candle(1), candle(0)])
        with self.assertRaisesRegex(ValueError, "unordered"):
            mod.ingest(self.csv, self.ledger, RECEIVED2)


if __name__ == "__main__":
    unittest.main()
