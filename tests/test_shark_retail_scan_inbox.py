"""Offline process-isolated Myfxbook first-seen SQLite inbox -> NEW decision.

No LIVE scanner, price requests, Myfxbook GET, Oracle, orders or real data.
Uses genuine original Squalincome COT+price+ingest coordinator with synthetic
rows. The single SQLite BEGIN IMMEDIATE prevents concurrent receipt writes
between selection and the new-event COMMIT.
"""
from __future__ import annotations

import copy
from datetime import timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_scan_inbox as inbox
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_signal_ingest_decision_link as source
from scripts import shark_cvd_incremental_protocol as frozen
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ, RECORDED
from test_shark_signal_ingest_decision_link import setup_case,OBS,NOW,SECRET
from test_shark_original_decision_atomic_gate import new_history


class RetailInboxTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.price=setup_case()
        retail.ensure_schema(self.db)
        self.first=original_pair()
        retail.capture_pair(self.db,original_snapshot=self.first,
                            file_read_at=READ,clock=RECORDED)

    def tearDown(self):
        self.db.close()

    def decision(self,**kw):
        args={"insert_history":new_history,
              "original_document":self.price,"clock":NOW,
              "research_retail_inbox":True}
        args.update(kw)
        return atomic.record_new(self.db,**args)

    def counts(self):
        return (
            self.db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0],
            source.aggregate(self.db)["locallyJoined"],
            retail.aggregate(self.db)["localOriginalSignalContextLinks"],
        )

    def later_pair(self,updated,read_at,record_at):
        doc=copy.deepcopy(self.first)
        doc["updatedAt"]=updated
        for item in doc["symbols"].values():
            item["t"]=updated
        retail.capture_pair(
            self.db,original_snapshot=doc,
            file_read_at=read_at,clock=record_at)
        return doc

    def test_receipt_selected_in_same_new_event_no_original_json_reload(self):
        with patch.object(retail,"_identity",
                          side_effect=AssertionError("no latest.json read")):
            result=self.decision()
        self.assertEqual(result["retailFirstSeen"],
                         "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT")
        self.assertTrue(result["retailSelectedInsideOriginalDecision"])
        self.assertFalse(result["retailValuesRehydrated"])
        self.assertFalse(result["retailUsedByOriginalSqualincomeSignal"])
        self.assertEqual(result["cvdCoverage"],"UNKNOWN")
        self.assertEqual(self.counts(),(1,1,1))
        self.assertEqual(frozen.protocol_sha256(),frozen.FROZEN_PROTOCOL_SHA256)
        value=json.dumps(result)+json.dumps(retail.aggregate(self.db))
        for forbidden in (SECRET,"EURUSD","62.5","2015.0","2026-11-09"):
            self.assertNotIn(forbidden,value)

    def test_cot_price_research_default_stays_retail_unknown(self):
        result=self.decision(research_retail_inbox=False)
        self.assertEqual(result["retailFirstSeen"],"UNKNOWN")
        self.assertFalse(result["retailSelectedInsideOriginalDecision"])
        self.assertEqual(self.counts(),(1,1,0))

    def test_later_local_receipts_must_not_leak_back_in_time(self):
        self.later_pair("2026-11-09T12:00:40Z",
                        OBS+timedelta(seconds=10),
                        OBS+timedelta(seconds=12))
        result=self.decision()
        self.assertTrue(result["retailSelectedInsideOriginalDecision"])
        row=self.db.execute(
            f"SELECT retail_witness_id FROM {retail.LINK}").fetchone()
        original_id=self.db.execute(
            f"SELECT id FROM {retail.TABLE} WHERE symbol='EURUSD'"
            " ORDER BY id LIMIT 1").fetchone()[0]
        self.assertEqual(row[0],original_id)
        self.assertEqual(self.counts(),(1,1,1))

    def test_predecision_newer_receipt_always_wins(self):
        self.later_pair("2026-11-09T11:56:00Z",
                        OBS-timedelta(seconds=45),
                        OBS-timedelta(seconds=35))
        self.decision()
        chosen=self.db.execute(
            f"SELECT retail_witness_id FROM {retail.LINK}").fetchone()[0]
        latest=self.db.execute(
            f"SELECT id FROM {retail.TABLE} WHERE symbol='EURUSD'"
            " ORDER BY id DESC LIMIT 1").fetchone()[0]
        self.assertEqual(chosen,latest)

    def test_invalid_latest_eligible_receipt_fails_closed_not_fallback(self):
        self.later_pair("2026-11-09T11:56:00Z",
                        OBS-timedelta(seconds=45),
                        OBS-timedelta(seconds=35))
        # Deliberately simulate a PRIVILEGED file-owner write to one local
        # receipt after dropping only sandbox append-only protection.
        self.db.execute("DROP TRIGGER research_retail_first_update")
        self.db.execute(
            f"UPDATE {retail.TABLE} SET numeric_sha256='INVALID' "
            "WHERE symbol='EURUSD' AND id=(SELECT max(id) FROM "
            f"{retail.TABLE} WHERE symbol='EURUSD')")
        self.db.commit()
        with self.assertRaisesRegex(
                ValueError,"pinned_retail_receipt_not_originally_available"):
            self.decision()
        self.assertEqual(self.counts(),(0,0,0))

    def test_missing_pilot_receipt_fails_research_only(self):
        self.db.execute(f"DROP TABLE {retail.LINK}")
        self.db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.decision()
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_mutually_exclusive_retail_inputs_not_mutated(self):
        with self.assertRaisesRegex(ValueError,
                                    "retail_sources_are_mutually_exclusive"):
            self.decision(original_retail_snapshot=self.first)
        with self.assertRaisesRegex(ValueError,
                                    "retail_sources_are_mutually_exclusive"):
            self.decision(retail_receipt_id=1)
        with self.assertRaisesRegex(ValueError,
                                    "retail_inbox_opt_in_requires_boolean"):
            self.decision(research_retail_inbox="yes")
        self.assertEqual(self.counts(),(0,0,0))

    def test_absent_retail_source_rolls_back_cot_price_history(self):
        # SANDBOX ONLY: simulate missing previously recorded receipts by
        # deliberately disabling DELETE protection in an in-memory fixture.
        # Production append-only behavior remains unchanged.
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.db:
                self.db.execute(f"DELETE FROM {retail.TABLE}")
        self.db.execute("DROP TRIGGER research_retail_first_delete")
        self.db.execute(f"DELETE FROM {retail.TABLE}")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                    "retail_prior_receipt_inbox_empty"):
            self.decision()
        self.assertEqual(self.counts(),(0,0,0))
        self.assertFalse(self.db.in_transaction)

    def test_require_original_owned_sqlite_transaction(self):
        with self.assertRaisesRegex(ValueError,
                    "original_signal_immediate_transaction_required"):
            inbox.attach_from_inbox(
                self.db,history_id=1,clock=NOW)
        self.db.execute("BEGIN")
        with self.assertRaisesRegex(ValueError,"new_history_row_id_required"):
            inbox.attach_from_inbox(
                self.db,history_id=False,clock=NOW)
        self.db.rollback()

    def test_two_process_sqlite_write_lock_rejects_receipt_race(self):
        # The actual original decision coordinator does BEGIN IMMEDIATE.
        # A second connection must not be able to insert a newer local
        # receipt in the middle of selection/commit on the first writer.
        # SQLite in-memory DB has no second process; verify the invariant
        # on a temporary shared copy with timeout=0 and no broker calls.
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/"pilot.sqlite"
            other=sqlite3.connect(str(path),timeout=0)
            other.execute("CREATE TABLE lock_probe(id INTEGER)")
            other.commit()
            first=sqlite3.connect(str(path),timeout=0)
            first.execute("BEGIN IMMEDIATE")
            with self.assertRaises(sqlite3.OperationalError):
                other.execute("BEGIN IMMEDIATE")
            first.rollback()
            other.execute("BEGIN IMMEDIATE")
            other.rollback()
            first.close()
            other.close()


if __name__=="__main__":
    unittest.main()
