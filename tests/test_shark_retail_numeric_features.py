"""Track B: anonymous Myfxbook numeric feature vault; synthetic SQLITE ONLY.

Real original Myfxbook row, first-seen dual-pilot SQLite transaction and
same original Squalincome decision research modules. No real provider API,
credentials, broker calls, LIVE import, cloud storage or trading.
"""
from __future__ import annotations

import copy
from datetime import timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_cvd_incremental_protocol as frozen
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ,RECORDED
from test_shark_signal_ingest_decision_link import setup_case,NOW,SECRET
from test_shark_original_decision_atomic_gate import new_history


class ProspectiveRetailNumericTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.price=setup_case()
        retail.ensure_schema(self.db)
        self.original=original_pair()

    def tearDown(self):
        self.db.close()

    def capture(self,*,features=True,original=None):
        return retail.capture_pair(
            self.db,original_snapshot=self.original if original is None else original,
            file_read_at=READ,clock=RECORDED,
            research_numeric_features=features)

    def decide(self,*,inbox=True):
        return atomic.record_new(
            self.db,insert_history=new_history,
            original_document=self.price,clock=NOW,
            research_retail_inbox=inbox)

    def receipts(self):
        return self.db.execute(f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0]

    def feature_count(self):
        return self.db.execute(f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0]

    def test_actual_six_numeric_fields_original_hash_same_transaction_and_asof(self):
        numeric.ensure_schema(self.db)
        self.assertTrue(numeric.require_schema(self.db))
        self.capture()
        self.assertEqual((self.receipts(),self.feature_count()),(2,2))
        decision=self.decide()
        self.assertEqual(decision["retailFirstSeen"],
                         "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT")
        result=numeric.read_linked(self.db,history_id=1)
        self.assertEqual(result["status"],
                         "LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH")
        self.assertEqual(result["features"]["lPct"],62.5)
        self.assertEqual(result["features"]["sPct"],37.5)
        self.assertEqual(result["features"]["lLots"],1200.5)
        self.assertEqual(result["features"]["sLots"],800.25)
        self.assertEqual(result["features"]["lPos"],950)
        self.assertEqual(result["features"]["sPos"],725)
        self.assertFalse(result["retailInputToOriginalSignal"])
        self.assertFalse(result["myfxbookTimestampIndependentlyAuthenticated"])
        self.assertFalse(result["actualOutcomesOrCostsMeasured"])
        self.assertEqual(result["cvdCoverage"],"UNKNOWN")
        self.assertFalse(result["realEdgeEstablished"])
        self.assertEqual(numeric.aggregate(self.db)["prospectiveNumericRows"],2)
        safe=json.dumps(numeric.aggregate(self.db))+json.dumps(decision)
        for forbidden in (SECRET,"EURUSD","XAUUSD","62.5","950","2026-11-09"):
            self.assertNotIn(forbidden,safe)

    def test_default_first_seen_stores_no_numeric_or_migration(self):
        self.capture(features=False)
        self.assertEqual(self.receipts(),2)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM sqlite_master WHERE name=?",
            (numeric.TABLE,)).fetchone()[0],0)
        self.decide()
        with self.assertRaises(sqlite3.DatabaseError):
            numeric.read_linked(self.db,history_id=1)

    def test_explicit_numeric_without_migration_fails_before_receipts(self):
        with self.assertRaisesRegex(ValueError,
                                     "numeric_features_explicit_migration_required"):
            self.capture(features=True)
        self.assertEqual(self.receipts(),0)

    def test_existing_receipt_without_numeric_is_marked_unknown(self):
        numeric.ensure_schema(self.db)
        self.capture(features=False)
        self.decide()
        result=numeric.read_linked(self.db,history_id=1)
        self.assertEqual(result["status"],
                         "UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN")
        self.assertFalse(result["realEdgeEstablished"])

    def test_no_original_decision_cannot_expose_numeric_features(self):
        numeric.ensure_schema(self.db)
        self.capture()
        self.assertEqual(numeric.read_linked(self.db,history_id=1)["status"],
                         "UNKNOWN_NO_ORIGINAL_RETAIL_LINK")
        self.assertEqual(self.feature_count(),2)

    def test_second_numeric_feature_failure_rolls_back_both_first_seen(self):
        numeric.ensure_schema(self.db)
        self.db.execute(f"""CREATE TRIGGER reject_second_features
            BEFORE INSERT ON {numeric.TABLE}
            WHEN NEW.symbol='XAUUSD'
            BEGIN SELECT RAISE(ABORT,'synthetic_second_market_failure'); END""")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                     "synthetic_second_market_failure"):
            self.capture()
        self.assertEqual((self.receipts(),self.feature_count()),(0,0))
        self.assertFalse(self.db.in_transaction)

    def test_hard_cap_stops_before_exceeding_and_rolls_back_both(self):
        numeric.ensure_schema(self.db)
        with patch.object(numeric,"MAX_FEATURE_ROWS",1):
            with self.assertRaisesRegex(ValueError,"numeric_features_capacity_reached"):
                self.capture()
        self.assertEqual((self.receipts(),self.feature_count()),(0,0))

    def test_tampered_numeric_value_rejected_despite_privileged_trigger_drop(self):
        numeric.ensure_schema(self.db)
        self.capture()
        self.decide()
        self.db.execute("DROP TRIGGER research_retail_features_no_update")
        self.db.execute(
            f"UPDATE {numeric.TABLE} SET long_pct=63 "
            "WHERE symbol='EURUSD'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                    "numeric_features_tampered_or_not_same_original_receipt"):
            numeric.read_linked(self.db,history_id=1)

    def test_append_only_blocks_modify_and_delete(self):
        numeric.ensure_schema(self.db)
        self.capture()
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.db:
                self.db.execute(f"UPDATE {numeric.TABLE} SET long_pct=20")
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.db:
                self.db.execute(f"DELETE FROM {numeric.TABLE}")
        self.assertEqual(self.feature_count(),2)

    def test_original_source_features_are_never_backfilled_from_later_file(self):
        numeric.ensure_schema(self.db)
        self.capture(features=False)
        self.decide()
        # A later latest.json has different retail numbers. It is not
        # possible to transform the old receipt into the new feature proof.
        later=copy.deepcopy(self.original)
        later["symbols"]["EURUSD"]["lPct"]=75
        later["symbols"]["EURUSD"]["sPct"]=25
        self.assertEqual(numeric.read_linked(self.db,history_id=1)["status"],
                         "UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN")
        self.assertEqual(self.feature_count(),0)

    def test_numeric_schema_trigger_preflight_is_read_only(self):
        numeric.ensure_schema(self.db)
        self.db.execute("DROP TRIGGER research_retail_features_no_delete")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                     "numeric_features_append_only_trigger_missing"):
            self.capture()
        self.assertEqual(self.receipts(),0)

    def test_frozen_protocol_and_actual_signal_unchanged(self):
        numeric.ensure_schema(self.db)
        self.capture()
        self.decide()
        self.assertEqual(frozen.protocol_sha256(),frozen.FROZEN_PROTOCOL_SHA256)
        self.assertFalse(numeric.aggregate(self.db)["liveEnabled"])
        self.assertFalse(numeric.aggregate(self.db)["realEdgeEstablished"])


if __name__=="__main__":
    unittest.main()
