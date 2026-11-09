"""Offline original-history predecision pin and cross-shard reconciliation.

Real Squalincome COT+price+ingest proof algorithms and real retail segment
producer over disposable SQLite. No collector, provider, real prices, OCI,
trading outcomes, source backfill, API calls, or live activation.
"""
from __future__ import annotations

from datetime import timedelta
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_retail_crossdb_predecision as pin
from scripts import shark_retail_segment_writer as writer
from scripts import shark_observation_bundle as bundle
from scripts import shark_signal_ingest_decision_link as sources
from test_shark_original_decision_atomic_gate import new_history
from test_shark_signal_ingest_decision_link import setup_case,OBS,NOW
from test_shark_retail_segment_readiness import make_pair,AUTHORIZED


class PredecisionCrossDbTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(prefix="remura-retail-lab-")
        self.folder=Path(self.tmp.name)
        self.env=patch.dict(os.environ,{writer.ENV:writer.ACK})
        self.env.start()
        self.core,_,self.ohlc=setup_case()
        pin.ensure_schema(self.core)
        self.received=OBS-timedelta(minutes=20)
        writer.record(
            self.folder,authorized_at=AUTHORIZED,
            original_snapshot=make_pair(self.received),
            file_read_at=self.received-timedelta(seconds=5),
            clock=self.received)
        self.prepared=OBS-timedelta(seconds=1)

    def tearDown(self):
        self.core.close()
        self.env.stop()
        self.tmp.cleanup()

    def prepare(self,when=None):
        return pin.prepare(
            self.folder,authorized_at=AUTHORIZED,symbol="EURUSD",
            prepared_at=self.prepared if when is None else when)

    def original(self,ticket,*,fail_after_pin=False):
        self.core.execute("BEGIN IMMEDIATE")
        try:
            fresh=new_history(self.core)
            outcome=pin.pin_new(
                self.core,fresh_history_cursor=fresh,
                ticket=ticket,clock=NOW)
            self.assertTrue(outcome["originalTransactionStillOpen"])
            if fail_after_pin:
                raise RuntimeError("synthetic_crash_after_exact_predecision_pin")
            evid=bundle.record(
                self.core,history_id=fresh.lastrowid,
                observed_document=self.ohlc,clock=NOW)
            self.assertEqual(evid["state"],"BOTH_LOCAL_PROOFS_PRESENT")
            origin=sources.capture(
                self.core,history_id=fresh.lastrowid,
                original_document=self.ohlc,clock=NOW)
            self.assertEqual(
                origin["status"],"ORIGINAL_LOCAL_COT_PRICE_INGEST_LINKED")
            self.core.commit()
            return fresh.lastrowid
        except BaseException:
            self.core.rollback()
            raise

    def read(self,history_id):
        self.core.execute("PRAGMA query_only=ON")
        try:
            return pin.reconcile(
                self.core,self.folder,history_id=history_id,
                authorized_at=AUTHORIZED)
        finally:
            self.core.execute("PRAGMA query_only=OFF")

    def test_receipt_selected_before_event_and_reconciled_exactly(self):
        ticket=self.prepare()
        self.assertEqual(ticket["symbol"],"EURUSD")
        self.assertLessEqual(ticket["recordedAt"],ticket["preparedAt"])
        hid=self.original(ticket)
        report=self.read(hid)
        self.assertEqual(
            report["status"],"LOCAL_PREDECISION_TICKET_AND_SHARD_MATCH_NOT_LIVE_GO")
        self.assertTrue(report["verifiedOriginalRetailPin"])
        self.assertFalse(report["crossDatabaseAtomicityProven"])
        self.assertFalse(report["retailActuallyUsedBySqualincome"])
        self.assertFalse(report["tradingEdgeEstablished"])

    def test_crash_after_original_pin_rolls_back_both_original_rows(self):
        ticket=self.prepare()
        with self.assertRaisesRegex(RuntimeError,"synthetic_crash_after"):
            self.original(ticket,fail_after_pin=True)
        self.assertEqual(self.core.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(self.core.execute(
            f"SELECT count(*) FROM {pin.TABLE}").fetchone()[0],0)
        self.assertEqual(self.core.execute(
            f"SELECT count(*) FROM {sources.TABLE}").fetchone()[0],0)

    def test_later_source_not_retroactively_selected(self):
        with self.assertRaisesRegex(ValueError,"no_asof_persisted_retail_receipt"):
            self.prepare(self.received-timedelta(minutes=2))
        # A receipt that arrives after original scan can be stored in the
        # segment but must NEVER be invented during future reconciliation.
        ticket=self.prepare()
        late=OBS+timedelta(minutes=1)
        writer.record(self.folder,authorized_at=AUTHORIZED,
                      original_snapshot=make_pair(late),
                      file_read_at=late-timedelta(seconds=5),clock=late)
        hid=self.original(ticket)
        self.assertEqual(
            self.read(hid)["status"],
            "LOCAL_PREDECISION_TICKET_AND_SHARD_MATCH_NOT_LIVE_GO")
        self.assertEqual(self.core.execute(
            f"SELECT receipt_id FROM {pin.TABLE}").fetchone()[0],
            ticket["receiptId"])

    def test_future_prepared_time_rejected_before_original_history_commit(self):
        ticket=self.prepare()
        ticket["preparedAt"]=(OBS+timedelta(seconds=1)).isoformat()
        with self.assertRaisesRegex(ValueError,"not_known_before_original"):
            self.original(ticket)
        self.assertEqual(self.core.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_old_committed_history_cannot_accept_new_pin(self):
        ticket=self.prepare()
        hid=self.original(ticket)
        with self.assertRaisesRegex(ValueError,"new_original_write_transaction"):
            pin.pin_new(self.core,fresh_history_cursor=None,
                        ticket=ticket,clock=NOW)
        self.assertEqual(self.read(hid)["verifiedOriginalRetailPin"],True)

    def test_deleted_shard_is_unknown_not_reconstructed_as_new_sample(self):
        ticket=self.prepare()
        hid=self.original(ticket)
        (self.folder/"retail-000001.sqlite3").unlink()
        report=self.read(hid)
        self.assertEqual(
            report["status"],"UNKNOWN_ORIGINAL_OR_SHARD_PROOF_UNVERIFIABLE")
        self.assertFalse(report["verifiedOriginalRetailPin"])
        self.assertFalse(report["reconstructedFromLaterRetailData"])

    def test_original_pruning_is_unknown_even_if_pin_is_still_present(self):
        ticket=self.prepare()
        hid=self.original(ticket)
        self.core.execute("DELETE FROM squalincome_history WHERE id=?",(hid,))
        self.core.commit()
        report=self.read(hid)
        self.assertEqual(
            report["status"],"UNKNOWN_ORIGINAL_OR_SHARD_PROOF_UNVERIFIABLE")

    def test_mutated_shard_numeric_value_is_not_a_valid_recovered_proof(self):
        ticket=self.prepare()
        hid=self.original(ticket)
        shard=self.folder/"retail-000001.sqlite3"
        with sqlite3.connect(shard) as db:
            db.execute("DROP TRIGGER research_retail_features_no_update")
            db.execute(
                "UPDATE research_retail_numeric_features "
                "SET long_pct=70,short_pct=30 WHERE symbol='EURUSD'")
        report=self.read(hid)
        self.assertEqual(
            report["status"],"UNKNOWN_ORIGINAL_OR_SHARD_PROOF_UNVERIFIABLE")
        self.assertFalse(report["verifiedOriginalRetailPin"])


if __name__=="__main__":
    unittest.main()
