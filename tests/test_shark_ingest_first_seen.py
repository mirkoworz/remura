"""OFFLINE synthetic proof that opt-in research digest is inserted AT price UPSERT.

Executes real price_store.ingest, never a mocked broker or actual VPS file.
"""
from __future__ import annotations

import copy
from datetime import timedelta,timezone
import json
import sqlite3
import unittest

from scripts import shark_ingest_first_seen as fingerprint
from test_shark_ctrader_ingest_handoff import (
    fixture,CHILD_STARTED,PARENT_READ,INGEST_DONE,SCAN,SECRET,CLOSE,iso
)
from price_store import ingest,latest


def prepared():
    db, child, doc = fixture()
    fingerprint.ensure_schema(db)
    return db,child,doc


def record(db,child, *,received=PARENT_READ,now=INGEST_DONE):
    return ingest(db,child,now=now,research_parent_read_at=received)


class ResearchIngestFirstSeenTests(unittest.TestCase):
    def setUp(self):
        self.db,self.child,self.stored=prepared()

    def tearDown(self):
        self.db.close()

    def total(self):
        return self.db.execute(
            f"SELECT count(*) FROM {fingerprint.TABLE}").fetchone()[0]

    def test_true_ingest_same_market_transaction_and_later_scan_check(self):
        report=record(self.db,self.child)
        self.assertIn("EURUSD",report["saved"])
        self.assertEqual(self.total(),1)
        s=fingerprint.verify_scan(
            self.db,symbol="EURUSD",current_document=latest(self.db,"EURUSD"),
            scan_at=SCAN)
        self.assertEqual(s["status"],"LOCAL_SAME_MERGED_DOCUMENT_MATCHED")
        self.assertTrue(s["locallyPersistedAsPartOfPriceUpsert"])
        self.assertFalse(s["brokerSignedOrExternallyTimestamped"])
        self.assertFalse(s["realProspectiveOutcomeOrCostsKnown"])
        self.assertFalse(s["independentOOSValidated"])
        self.assertFalse(s["statisticalEdgeEstablished"])
        self.assertEqual((s["additionalBrokerCalls"],s["writes"]),(0,0))
        self.assertEqual(
            fingerprint.aggregate(self.db)["locallyRecorded"],1)
        safe=json.dumps(s)+json.dumps(fingerprint.aggregate(self.db))
        self.assertNotIn(SECRET,safe)
        self.assertNotIn("EURUSD",safe)
        self.assertNotIn("2026-11-09",safe)
        self.assertNotIn("0.0001",safe)
        # Misleading existing field is candle OPEN, never parent receipt.
        self.assertEqual(self.db.execute(
            "SELECT updated_at FROM prices WHERE symbol='EURUSD'"
        ).fetchone()[0],iso(CLOSE-timedelta(minutes=15)))

    def test_default_legacy_path_stays_identical_and_no_research_write(self):
        pre=json.dumps(latest(self.db,"EURUSD"),sort_keys=True)
        out=ingest(self.db,self.child,now=INGEST_DONE)
        self.assertEqual(out["errors"],{})
        self.assertIn("EURUSD",out["saved"])
        self.assertEqual(self.total(),0)
        self.assertEqual(
            json.dumps(latest(self.db,"EURUSD"),sort_keys=True),pre)

    def test_missing_migration_raises_and_prevents_price_update(self):
        self.db.execute(f"DROP TABLE {fingerprint.TABLE}")
        self.db.commit()
        baseline=json.dumps(latest(self.db,"EURUSD"),sort_keys=True)
        with self.assertRaises(sqlite3.OperationalError):
            record(self.db,self.child)
        self.assertEqual(
            json.dumps(latest(self.db,"EURUSD"),sort_keys=True),baseline)

    def test_append_only_trigger_and_scan_detects_price_revision(self):
        record(self.db,self.child)
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(
                    f"UPDATE {fingerprint.TABLE} SET symbol='XAUUSD'")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(f"DELETE FROM {fingerprint.TABLE}")
        changed=copy.deepcopy(latest(self.db,"EURUSD"))
        changed["timeframes"]["M15"][0]["c"]+=0.00001
        self.db.execute("UPDATE prices SET payload=? WHERE symbol=?",
                        (json.dumps(changed),"EURUSD"))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                     "source_document_mutated_since_original_ingest"):
            fingerprint.verify_scan(
                self.db,symbol="EURUSD",current_document=changed,scan_at=SCAN)
        with self.assertRaisesRegex(ValueError,
                                     "current_price_store_not_original_document"):
            fingerprint.verify_scan(
                self.db,symbol="EURUSD",
                current_document=self.stored,scan_at=SCAN)

    def test_missing_or_invalid_utc_received_clock_fails_before_upsert(self):
        for receipt in (
            CHILD_STARTED-timedelta(seconds=1),
            INGEST_DONE+timedelta(seconds=1),
            PARENT_READ+timedelta(minutes=20),
            PARENT_READ.astimezone(timezone(timedelta(hours=1))),
            "2026-11-09T12:00:25Z",False
        ):
            with self.subTest(receipt=receipt):
                with self.assertRaises(ValueError):
                    record(self.db,self.child,received=receipt)
                self.assertEqual(self.total(),0)
        self.assertEqual(latest(self.db,"EURUSD"),self.stored)

    def test_duplicate_original_handoff_rolls_back_new_price_upsert(self):
        original=record(self.db,self.child)
        self.assertEqual(self.total(),1)
        baseline=latest(self.db,"EURUSD")
        again=record(self.db,self.child)
        self.assertNotIn("EURUSD",again["saved"])
        self.assertIn("EURUSD",again["errors"])
        self.assertEqual(self.total(),1)
        self.assertEqual(latest(self.db,"EURUSD"),baseline)

    def test_valid_ohlc_revision_at_child_is_persisted_only_on_success(self):
        child=copy.deepcopy(self.child)
        child["markets"]["EURUSD"]["timeframes"]["M15"][-4]["c"]+=.00001
        # A valid changed child close matches the *new* merged source;
        # this proves local self-consistency, NOT genuine broker origin.
        report=record(self.db,child)
        self.assertEqual(report["errors"],{})
        self.assertEqual(self.total(),1)
        self.assertNotEqual(latest(self.db,"EURUSD"),self.stored)
        self.assertFalse(fingerprint.verify_scan(
            self.db,symbol="EURUSD",current_document=latest(self.db,"EURUSD"),
            scan_at=SCAN)["brokerSignedOrExternallyTimestamped"])

    def test_failed_market_proof_rolls_back_price_upsert_not_old_evidence(self):
        report=record(self.db,self.child)
        self.assertEqual(report["errors"],{})
        current=latest(self.db,"EURUSD")
        self.db.execute(f"""CREATE TRIGGER block_future_local_witness
            BEFORE INSERT ON {fingerprint.TABLE}
            BEGIN SELECT RAISE(ABORT,'synthetic_fingerprint_storage_failed'); END""")
        self.db.commit()
        altered=copy.deepcopy(self.child)
        altered["markets"]["EURUSD"]["timeframes"]["M15"][-3]["c"]+=.00001
        failed=record(self.db,altered,received=PARENT_READ+timedelta(seconds=2),
                      now=INGEST_DONE+timedelta(seconds=2))
        self.assertIn("EURUSD",failed["saved"] if False else failed["errors"])
        self.assertEqual(self.total(),1)
        self.assertEqual(latest(self.db,"EURUSD"),current)
        self.db.execute("DROP TRIGGER block_future_local_witness")
        self.db.commit()

    def test_pilot_market_filter_prevents_partial_34_market_proof(self):
        child=copy.deepcopy(self.child)
        child["markets"]["US500"]=dict(
            child["markets"]["EURUSD"],symbol="US500")
        with self.assertRaisesRegex(ValueError,
                                     "explicit_two_market_research_pilot_only"):
            record(self.db,child)
        self.assertEqual(self.total(),0)

    def test_scan_without_proof_or_later_stale_or_wrong_document_rejected(self):
        with self.assertRaisesRegex(
                ValueError,"original_ingest_first_seen_proof_absent"):
            fingerprint.verify_scan(
                self.db,symbol="EURUSD",current_document=self.stored,
                scan_at=SCAN)
        record(self.db,self.child)
        with self.assertRaisesRegex(
                ValueError,"source_receipt_not_available_at_scan"):
            fingerprint.verify_scan(
                self.db,symbol="EURUSD",current_document=self.stored,
                scan_at=SCAN+timedelta(minutes=10))
        with self.assertRaises(ValueError):
            fingerprint.verify_scan(
                self.db,symbol="XAUUSD",current_document=self.stored,
                scan_at=SCAN)

    def test_frozen_protocol_is_untouched(self):
        from scripts import shark_cvd_incremental_protocol as protocol
        self.assertEqual(protocol.protocol_sha256(),
                         protocol.FROZEN_PROTOCOL_SHA256)
        self.assertEqual(
            fingerprint.aggregate(self.db)["pilotMarketCount"],2)
        self.assertFalse(
            fingerprint.aggregate(self.db)["statisticalEdgeEstablished"])


if __name__=="__main__":
    unittest.main()
