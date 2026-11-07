"""Offline tests for a *coordinator-owned* original-history proof transaction.

All records are synthetic SQLite fixtures; not market performance evidence.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from scripts import shark_price_regime_atomic_gate as gate
from scripts import shark_price_asof_evidence as price
from scripts import shark_regime_first_seen as regime
from test_shark_regime_first_seen import (
    fixture, CLOSE, OBS, NOW, RECEIVED, FAKE_BROKER, stamp
)


def new_history(db):
    return db.execute(
        "INSERT INTO squalincome_history("
        "symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin)"
        " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("EURUSD","aligned",1,1,1,1,1,"confirmed","2026-11-03",
         stamp(CLOSE),stamp(OBS),5.,"update")
    )


def run(db, doc, **kwargs):
    args={"insert_history": new_history,
          "original_document":doc,
          "source_received_at": RECEIVED, "clock": NOW}
    args.update(kwargs)
    return gate.capture_new(db,**args)


def counts(db):
    return (
        db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0],
        db.execute(f"SELECT count(*) FROM {price.TABLE}").fetchone()[0],
        db.execute(f"SELECT count(*) FROM {regime.TABLE}").fetchone()[0],
    )


class AtomicPriceRegimeCaptureTests(unittest.TestCase):
    def setUp(self):
        self.db,self.doc=fixture()

    def tearDown(self):
        self.db.close()

    def test_one_original_insert_and_two_witnesses_commit_as_one(self):
        out=run(self.db,self.doc)
        self.assertEqual(counts(self.db),(1,1,1))
        self.assertEqual(
            out["status"],"LOCAL_ATOMIC_PAIR_RECORDED_RESEARCH_ONLY")
        self.assertTrue(out["historyAndBothLocalProofsCommittedTogether"])
        self.assertTrue(out["originalSourceNotRefetched"])
        self.assertFalse(out["originalCTraderFetchInstrumentedInLive"])
        self.assertFalse(out["sourceReceiptClockIndependentlyAttested"])
        self.assertFalse(out["cotAndRetailProvenanceIncluded"])
        self.assertFalse(out["tradingEdgeEstablished"])
        self.assertFalse(out["costsOrRealFillsMeasured"])
        self.assertEqual(out["brokerCalls"],0)
        self.assertFalse(self.db.in_transaction)
        payload=json.dumps(out)+json.dumps(regime.aggregate(self.db))
        self.assertNotIn(FAKE_BROKER,payload)
        self.assertNotIn("EURUSD",payload)
        self.assertNotIn("2026-11-09T11:",payload)
        self.assertNotIn("1.010",payload)

    def test_original_in_memory_doc_changed_fails_and_rolls_back_all_three(self):
        mutated=copy.deepcopy(self.doc)
        mutated["timeframes"]["M15"][0]["c"]+=0.0001
        with self.assertRaisesRegex(ValueError,"price_document_changed_since_scan"):
            run(self.db,mutated)
        self.assertEqual(counts(self.db),(0,0,0))
        self.assertFalse(self.db.in_transaction)

    def test_impossible_or_fake_collection_time_never_committed(self):
        for received in (
            CLOSE-timedelta(seconds=1), OBS+timedelta(seconds=1),
            RECEIVED-timedelta(days=1), NOW+timedelta(seconds=1)
        ):
            with self.subTest(received=received):
                with self.assertRaises(ValueError):
                    run(self.db,self.doc,source_received_at=received)
                self.assertEqual(counts(self.db),(0,0,0))
        for receipt in (stamp(RECEIVED),None,42,
                        RECEIVED.astimezone(timezone(timedelta(hours=1)))):
            with self.subTest(receipt=receipt):
                with self.assertRaises(ValueError):
                    run(self.db,self.doc,source_received_at=receipt)
                self.assertEqual(counts(self.db),(0,0,0))

    def test_already_open_external_transaction_rejected_and_not_committed(self):
        self.db.execute("BEGIN")
        with self.assertRaisesRegex(ValueError,
                                     "fresh_owned_sqlite_transaction_required"):
            run(self.db,self.doc)
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(counts(self.db),(0,0,0))

    def test_reused_committed_cursor_not_a_new_history_insert(self):
        cursor=new_history(self.db)
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                     "one_new_original_history_insert_required"):
            run(self.db,self.doc,insert_history=lambda db: cursor)
        self.assertEqual(counts(self.db),(1,0,0))
        self.assertFalse(self.db.in_transaction)

    def test_noninsert_callback_and_ignored_insert_cannot_create_proofs(self):
        with self.assertRaisesRegex(ValueError,
                                     "one_new_original_history_insert_required"):
            run(self.db,self.doc,insert_history=lambda db:
                db.execute("SELECT * FROM squalincome_history"))
        self.assertEqual(counts(self.db),(0,0,0))
        def do_other_query(db):
            new_history(db)
            return db.execute("SELECT * FROM squalincome_history")
        with self.assertRaisesRegex(ValueError,
                                     "one_new_original_history_insert_required"):
            run(self.db,self.doc,insert_history=do_other_query)
        self.assertEqual(counts(self.db),(0,0,0))

    def test_without_regime_schema_original_history_and_price_roll_back(self):
        self.db.execute(f"DROP TABLE {regime.TABLE}")
        self.db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            run(self.db,self.doc)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {price.TABLE}").fetchone()[0],0)
        self.assertFalse(self.db.in_transaction)

    def test_committed_duplicate_original_cannot_be_backfilled(self):
        run(self.db,self.doc)
        with self.assertRaises(sqlite3.IntegrityError):
            run(self.db,self.doc)
        self.assertEqual(counts(self.db),(1,1,1))
        self.assertFalse(self.db.in_transaction)

    def test_new_original_insertion_without_genuine_price_document_rolled_back(self):
        self.db.execute("UPDATE prices SET source='someone_else'")
        self.db.commit()
        with self.assertRaises(ValueError):
            run(self.db,self.doc)
        self.assertEqual(counts(self.db),(0,0,0))

    def test_prospective_gate_disallows_prior_start_and_requires_explicit_clock(self):
        before=datetime(2026,11,8,12,0,tzinfo=timezone.utc)
        with self.assertRaisesRegex(ValueError,
                                     "frozen_prospective_protocol_gate"):
            run(self.db,self.doc,clock=before)
        for invalid in ("2026-11-09T11:01:00Z",None,True):
            with self.assertRaisesRegex(
                    ValueError,"actual_utc_receipt_and_record_clocks_required"):
                run(self.db,self.doc,clock=invalid)
        self.assertEqual(counts(self.db),(0,0,0))

    def test_callback_failure_rolls_back_entire_insert(self):
        def fails_after_insert(db):
            new_history(db)
            raise RuntimeError("simulated_crash_after_original_history")
        with self.assertRaisesRegex(RuntimeError,
                                     "simulated_crash_after_original_history"):
            run(self.db,self.doc,insert_history=fails_after_insert)
        self.assertEqual(counts(self.db),(0,0,0))
        self.assertFalse(self.db.in_transaction)


if __name__ == "__main__":
    unittest.main()
