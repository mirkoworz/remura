"""Track B OFFLINE exact Myfxbook receipt-ID handoff at original decision.

Genuine source value is NEVER re-read or rehydrated: only the metadata
receipt ID recorded by the private first-seen pair is available. Uses real
COT-price-ingest original decision coordinator with synthetic market bars,
never live feeds, trading, provider credentials or paid infrastructure.
"""
from __future__ import annotations

import copy
from datetime import timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import shark_retail_first_seen as retail
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_signal_ingest_decision_link as price_link
from scripts import shark_cvd_incremental_protocol as protocol
from test_shark_retail_first_seen import original,READ,RECORDED
from test_shark_signal_ingest_decision_link import setup_case,NOW,OBS,SECRET
from test_shark_original_decision_atomic_gate import new_history


def original_pair():
    document=original()
    document["symbols"]["XAUUSD"]=copy.deepcopy(document["symbols"]["EURUSD"])
    document["symbols"]["XAUUSD"]["avgL"]=2015.0
    return document


class OriginalRetailReceiptHandoffTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.price=setup_case()
        retail.ensure_schema(self.db)
        self.snapshot=original_pair()
        retail.capture_pair(
            self.db,original_snapshot=self.snapshot,
            file_read_at=READ,clock=RECORDED)

    def tearDown(self):
        self.db.close()

    def receipt(self,symbol="EURUSD"):
        row=self.db.execute(
            f"SELECT id FROM {retail.TABLE} WHERE symbol=? "
            "ORDER BY id DESC LIMIT 1",(symbol,)
        ).fetchone()
        return row[0]

    def new_decision(self,receipt_id,**kwargs):
        return atomic.record_new(
            self.db,insert_history=new_history,
            original_document=self.price,clock=NOW,
            retail_receipt_id=receipt_id,**kwargs)

    def history_count(self):
        return self.db.execute(
            "SELECT count(*) FROM squalincome_history"
        ).fetchone()[0]

    def test_pinned_receipt_links_without_latest_json_or_rehydrate(self):
        original_id=self.receipt()
        with patch.object(retail,"_identity",
                          side_effect=AssertionError("forbidden retail re-read")):
            out=self.new_decision(original_id)
        self.assertEqual(out["retailFirstSeen"],
                         "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT")
        self.assertTrue(out["retailReceiptBoundWithoutSourceRefetch"])
        self.assertFalse(out["retailValuesRehydrated"])
        self.assertFalse(out["retailUsedByOriginalSqualincomeSignal"])
        self.assertEqual(out["cvdCoverage"],"UNKNOWN")
        self.assertFalse(out["statisticalEdgeEstablished"])
        self.assertEqual(self.history_count(),1)
        self.assertEqual(retail.aggregate(self.db)["localOriginalSignalContextLinks"],1)
        record=self.db.execute(
            f"SELECT retail_witness_id,original_numeric_sha256 "
            f"FROM {retail.LINK}").fetchone()
        self.assertEqual(record[0],original_id)
        self.assertEqual(len(record[1]),64)
        safe=json.dumps(out)+json.dumps(retail.aggregate(self.db))
        for forbidden in (SECRET,"EURUSD","62.5","2015.0","2026-11-09"):
            self.assertNotIn(forbidden,safe)

    def test_wrong_market_receipt_is_rejected_with_whole_rollback(self):
        with self.assertRaisesRegex(
                ValueError,"pinned_retail_receipt_not_originally_available"):
            self.new_decision(self.receipt("XAUUSD"))
        self.assertEqual(self.history_count(),0)
        self.assertEqual(price_link.aggregate(self.db)["locallyJoined"],0)
        self.assertEqual(retail.aggregate(self.db)["localOriginalSignalContextLinks"],0)
        self.assertEqual(retail.aggregate(self.db)["localFirstSeenSnapshots"],2)

    def test_missing_and_boolean_receipt_cannot_attach(self):
        with self.assertRaisesRegex(ValueError,"pinned_retail_receipt_absent"):
            self.new_decision(999999)
        for value in (True,False,0,-1,"1"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                        ValueError,"exact_positive_retail_receipt_id_required"):
                    self.new_decision(value)
        self.assertEqual(self.history_count(),0)

    def test_exclusive_legacy_snapshot_and_receipt(self):
        with self.assertRaisesRegex(
                ValueError,"retail_snapshot_and_pinned_receipt_are_exclusive"):
            self.new_decision(self.receipt(),
                              original_retail_snapshot=self.snapshot)
        self.assertEqual(self.history_count(),0)

    def test_timestamp_of_receipt_after_decision_cannot_be_backdated(self):
        # The existing first-seen row is immutable. Simulate a distinct
        # future receipt inserted AFTER original decision time.
        later=original_pair()
        later["updatedAt"]="2026-11-09T12:00:40Z"
        for entry in later["symbols"].values():
            entry["t"]=later["updatedAt"]
        retail.capture_pair(
            self.db,original_snapshot=later,
            file_read_at=OBS+timedelta(seconds=10),
            clock=OBS+timedelta(seconds=12))
        with self.assertRaisesRegex(
                ValueError,"pinned_retail_receipt_not_originally_available"):
            self.new_decision(self.receipt())
        self.assertEqual(self.history_count(),0)

    def test_older_receipt_cannot_be_cherry_picked_if_newer_predecision(self):
        old=self.receipt()
        newer=original_pair()
        newer["updatedAt"]="2026-11-09T11:56:00Z"
        for entry in newer["symbols"].values():
            entry["t"]=newer["updatedAt"]
        retail.capture_pair(
            self.db,original_snapshot=newer,
            file_read_at=OBS-timedelta(seconds=45),
            clock=OBS-timedelta(seconds=35))
        with self.assertRaisesRegex(
                ValueError,"pinned_receipt_superseded_before_original_decision"):
            self.new_decision(old)
        self.assertEqual(self.history_count(),0)
        out=self.new_decision(self.receipt())
        self.assertEqual(out["retailFirstSeen"],
                         "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT")
        self.assertEqual(self.history_count(),1)

    def test_future_receipt_must_not_invalidate_prior_asof_decision(self):
        old=self.receipt()
        newer=original_pair()
        newer["updatedAt"]="2026-11-09T12:00:40Z"
        for entry in newer["symbols"].values():
            entry["t"]=newer["updatedAt"]
        retail.capture_pair(
            self.db,original_snapshot=newer,
            file_read_at=OBS+timedelta(seconds=10),
            clock=OBS+timedelta(seconds=12))
        out=self.new_decision(old)
        self.assertTrue(out["retailReceiptBoundWithoutSourceRefetch"])
        self.assertEqual(self.history_count(),1)
        # This is an AS-OF test only. A malicious caller can forge clock
        # inputs: database chronology does not independently certify them.

    def test_corrupt_receipt_digest_cannot_be_used_even_by_privileged_sqlite(self):
        target=self.receipt()
        # In-memory adversarial owner deliberately DROP trigger; the
        # application refuses invalid hash anyway, no LIVE schema touched.
        self.db.execute("DROP TRIGGER research_retail_first_update")
        self.db.execute(
            f"UPDATE {retail.TABLE} SET numeric_sha256='BAD'"
            " WHERE id=?",(target,))
        self.db.commit()
        with self.assertRaisesRegex(
                ValueError,"pinned_retail_receipt_not_originally_available"):
            self.new_decision(target)
        self.assertEqual(self.history_count(),0)

    def test_missing_research_link_schema_rolls_back_original_history(self):
        self.db.execute(f"DROP TABLE {retail.LINK}")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            self.new_decision(self.receipt())
        self.assertEqual(self.history_count(),0)
        self.assertEqual(price_link.aggregate(self.db)["locallyJoined"],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0],
            2)
        # The context link table has deliberately been DROPPED in this
        # fixture; testing its row count would mask the actual rollback.

    def test_cvd_protocol_unchanged_and_no_real_retail_values_stored(self):
        self.assertEqual(protocol.protocol_sha256(),
                         protocol.FROZEN_PROTOCOL_SHA256)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0],2)
        columns=[r[1] for r in self.db.execute(
            f"PRAGMA table_info({retail.TABLE})")]
        for absent in ("lPct","sPct","lLots","sLots","lPos","sPos"):
            self.assertNotIn(absent,columns)
        self.assertEqual(self.history_count(),0)


if __name__=="__main__":
    unittest.main()
