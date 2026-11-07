"""Pinned original B contract: C owns only a thin offline orchestration.

This test is *only* run by CI after checkout of the exact B commit SHA into
track-b-pinned/. B's own real synthetic fixtures are imported and reused.
"""
from __future__ import annotations

import copy
from datetime import timedelta
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

# The runner sets this to the separate, exact SHA checkout. No ambient B
# checkout: the test must fail closed if CI omitted the pinned dependency.
ROOT = Path(__file__).resolve().parents[1]
B_ROOT = ROOT / "track-b-pinned"
if not B_ROOT.is_dir() or not (B_ROOT / "scripts/shark_retail_first_seen.py").is_file():
    raise RuntimeError("pinned_original_track_b_checkout_missing")
sys.path.insert(0, str(B_ROOT / "tests"))
sys.path.insert(0, str(B_ROOT / "scripts"))
sys.path.insert(0, str(B_ROOT))

from scripts import track_c_b_original_contract as bridge
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_signal_ingest_decision_link as link
from test_shark_signal_ingest_decision_link import setup_case, NOW
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ, RECORDED
from test_shark_original_decision_atomic_gate import new_history


class OriginalBContractTests(unittest.TestCase):
    def setUp(self):
        self.db, _source_child, self.price = setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)
        self.snapshot = original_pair()

    def tearDown(self):
        self.db.close()

    def invoke(self, **updates):
        args = {
            "original_snapshot": self.snapshot,
            "file_read_at": READ,
            "receipt_clock": RECORDED,
            "original_price_document": self.price,
            "insert_history": new_history,
            "decision_clock": NOW,
            "mode": bridge.MODE,
        }
        args.update(updates)
        return bridge.rehearsal(self.db, **args)

    def counts(self):
        return [
            self.db.execute(f"SELECT count(*) FROM {name}").fetchone()[0]
            for name in (retail.TABLE, numeric.TABLE, "squalincome_history",
                         retail.LINK, link.TABLE)
        ]

    def test_actual_original_b_modules_entire_local_chain(self):
        result = self.invoke()
        self.assertEqual(self.counts(), [2, 2, 1, 1, 1])
        self.assertEqual(result["state"],
                         "SYNTHETIC_PINNED_ORIGINAL_B_CHAIN_VERIFIED_NOT_LIVE")
        self.assertEqual(result["retailReceipts"], 2)
        self.assertEqual(result["numericFeatures"], 2)
        self.assertFalse(result["realOutcomesRecorded"])
        self.assertFalse(result["statisticalEdgeEstablished"])
        self.assertFalse(result["providerTimestampsAuthenticated"])
        self.assertFalse(result["liveEnabled"])
        self.assertEqual(result["cvdCoverage"], "UNKNOWN")
        self.assertEqual(result["brokerCalls"], 0)
        self.assertEqual(result["ordersEnabled"], False)
        self.assertEqual(result["notificationsEnabled"], False)
        # No symbols, numeric values, broker aliases, raw source, account IDs.
        public = json.dumps(result)
        for forbidden in ("EURUSD", "XAUUSD", "62.5", "2015", "2026-11-09"):
            self.assertNotIn(forbidden, public)

    def test_no_b_checkout_no_live_or_disk(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = sqlite3.connect(str(Path(tmp) / "mimic-live.db"))
            try:
                with self.assertRaisesRegex(ValueError, "never_use_disk"):
                    bridge.rehearsal(
                        db, original_snapshot=self.snapshot,
                        file_read_at=READ, receipt_clock=RECORDED,
                        original_price_document=self.price,
                        insert_history=new_history, decision_clock=NOW,
                        mode=bridge.MODE)
            finally:
                db.close()
        self.assertEqual(self.counts(), [0, 0, 0, 0, 0])

    def test_default_is_fail_closed_and_no_auto_schema(self):
        with self.assertRaisesRegex(ValueError, "offline_only_explicit"):
            self.invoke(mode=None)
        self.db.execute(f"DROP TABLE {numeric.TABLE}")
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "numeric_features_explicit_migration"):
            self.invoke()
        self.assertEqual(self.counts()[:1], [0])
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0], 0)

    def test_original_receipt_from_future_refused(self):
        future = RECORDED + timedelta(seconds=40)
        with self.assertRaises(ValueError):
            self.invoke(receipt_clock=future)
        self.assertEqual(self.counts(), [0, 0, 0, 0, 0])

    def test_no_second_market_rolls_back_pair(self):
        broken = copy.deepcopy(self.snapshot)
        del broken["symbols"]["XAUUSD"]
        with self.assertRaisesRegex(ValueError, "both_original_pilot"):
            self.invoke(original_snapshot=broken)
        self.assertEqual(self.counts(), [0, 0, 0, 0, 0])

    def test_late_decision_blocks_original_link(self):
        with self.assertRaises(ValueError):
            self.invoke(decision_clock=NOW+timedelta(minutes=6))
        # Earlier retail capture is a separate real-first-seen transaction:
        # it remains valid even when the later decision fails.
        self.assertEqual(self.counts(), [2, 2, 0, 0, 0])

    def test_wrong_market_receipt_does_not_become_original_signal(self):
        self.db.execute(f"""CREATE TRIGGER synthetic_remove_eur_receipt
            AFTER INSERT ON {retail.TABLE}
            WHEN NEW.symbol='EURUSD'
            BEGIN SELECT RAISE(ABORT,'synthetic_receipt_failure'); END""")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                     "synthetic_receipt_failure"):
            self.invoke()
        self.assertEqual(self.counts(), [0, 0, 0, 0, 0])


if __name__ == "__main__":
    unittest.main()
