"""REMURA B v21.2: NEW only offline parity-first real-data handoff tests."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from cot_offline_parity_fx_bundle import assemble, main
from test_cot_intelligence_parity import fixtures, resign, NOW, DATES


class TestNewOfflineParityFxBundle(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        folder = Path(self.scratch.name)
        self.public_path = folder / "public-offline.json"
        self.private_path = folder / "private-copy-offline.json"

    def put(self, public=None, private=None):
        default_public, default_private = fixtures()
        public = default_public if public is None else public
        private = default_private if private is None else private
        self.public_path.write_text(json.dumps(public), encoding="utf-8")
        self.private_path.write_text(json.dumps(private), encoding="utf-8")
        return self.public_path.read_bytes(), self.private_path.read_bytes()

    def test_clean_two_weeks_28_pairs_outputs_seven_public_futures_and_28_overlaps(self):
        before = self.put()
        output = assemble(self.public_path, self.private_path, DATES, NOW)
        self.assertEqual(output["state"], "DESCRIPTIVE_PUBLIC_FACTORS_PRIVATE_VALUES_MATCH")
        self.assertEqual(output["parityState"], "value_parity_only")
        self.assertEqual(output["verifiedValuePairs"], 28)
        self.assertEqual(output["privateFirstSeenKnownMatchedPairs"], 28)
        self.assertEqual(output["privateFirstSeenUnknownMatchedPairs"], 0)
        self.assertEqual(len(output["dashboard"]["factors"]), 7)
        self.assertEqual(len(output["dashboard"]["crosses"]), 28)
        self.assertEqual(output["dashboard"]["mode"], "descriptive_only")
        self.assertFalse(output["historicalDataAvailabilityIndependentlyVerified"])
        self.assertFalse(output["futurePricesOrPerformanceVerified"])
        self.assertEqual(self.public_path.read_bytes(), before[0])
        self.assertEqual(self.private_path.read_bytes(), before[1])
        self.assertNotIn("private-copy-offline.json", json.dumps(output))

    def test_one_private_cot_mismatch_blocks_export_before_node_launch(self):
        public, private = fixtures()
        private["rows"][0]["first_long"] += 1
        self.put(public, private)
        def never(*args, **kwargs):
            raise AssertionError("Do not launch Node for a mismatch")
        output = assemble(self.public_path, self.private_path, DATES, NOW, runner=never)
        self.assertEqual(output["state"], "BLOCKED_PUBLIC_PRIVATE_PARITY_NOT_CLEAN")
        self.assertIsNone(output["dashboard"])
        self.assertEqual(output["verifiedValuePairs"], 27)

    def test_first_seen_absent_keeps_values_descriptive_but_explicitly_unverified(self):
        public, private = fixtures()
        private["rows"][0]["first_seen_at"] = None
        self.put(public, private)
        output = assemble(self.public_path, self.private_path, DATES, NOW)
        self.assertEqual(output["state"], "DESCRIPTIVE_PUBLIC_FACTORS_PRIVATE_VALUES_MATCH")
        self.assertEqual(output["privateFirstSeenUnknownMatchedPairs"], 1)
        self.assertEqual(output["privateFirstSeenCoverageState"], "incomplete_or_unknown")
        self.assertFalse(output["privateFirstSeenIsOfficialPublication"])
        self.assertFalse(output["historicalDataAvailabilityIndependentlyVerified"])

    def test_public_digest_modified_rejected_before_export(self):
        public, private = fixtures()
        public["rows"][0]["first_long"] += 1
        self.put(public, private)
        def never(*args, **kwargs):
            raise AssertionError("No export before checksum gate")
        with self.assertRaisesRegex(ValueError, "PUBLIC_ROWS_CHECKSUM_MISMATCH"):
            assemble(self.public_path, self.private_path, DATES, NOW, runner=never)

    def test_missing_private_copy_fails_closed_without_creating_files(self):
        public, private = fixtures()
        self.put(public, private)
        self.private_path.unlink()
        before = self.public_path.read_bytes()
        with self.assertRaises(FileNotFoundError):
            assemble(self.public_path, self.private_path, DATES, NOW)
        self.assertEqual(self.public_path.read_bytes(), before)
        self.assertFalse(self.private_path.exists())

    def test_wrong_dates_or_misaligned_latest_period_fail_closed(self):
        public, private = fixtures()
        self.put(public, private)
        with self.assertRaisesRegex(ValueError, "INVALID_WEEKLY_COMPARISON"):
            assemble(self.public_path, self.private_path,
                     ["2026-11-10", "2026-11-12"], NOW)
        # A newer, extraneous week must not quietly become the dashboard
        # when custody parity covers a different earlier comparison.
        for snapshot in (public, private):
            current = [dict(x) for x in snapshot["rows"]
                       if x["report_date"] == "2026-11-17"]
            for row in current:
                row["report_date"] = "2026-11-21"
                if row["first_seen_at"] is not None:
                    row["first_seen_at"] = "2026-11-22T20:00:00Z"
            snapshot["rows"].extend(current)
            snapshot["rowCount"] = len(snapshot["rows"])
        resign(public)
        self.put(public, private)
        output = assemble(self.public_path, self.private_path, DATES, NOW)
        self.assertEqual(output["state"], "BLOCKED_DASHBOARD_PERIOD_OR_COVERAGE")
        self.assertIsNone(output["dashboard"])


if __name__ == "__main__":
    unittest.main()
