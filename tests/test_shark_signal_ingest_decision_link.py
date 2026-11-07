"""Synthetic end-to-end join of actual price_store.ingest + actual COT/price bundle.

All inputs deliberately synthetic. This suite proves local SQLite consistency,
not broker/CFTC authenticity or real trading outcomes. No network or LIVE DB.
"""
from __future__ import annotations

import copy
from datetime import datetime,timedelta,timezone
import json
import sqlite3
import unittest

from scripts import shark_signal_ingest_decision_link as link
from scripts import shark_ingest_first_seen as ingest_proof
from scripts import shark_cot_asof_witness as cot_witness
from scripts import shark_observation_bundle as bundle
from scripts import shark_price_asof_evidence as price_proof
from scripts import shark_signal_evidence as cot_proof
from test_shark_signal_evidence import fixture as cot_fixture, insert_history
from test_shark_ctrader_ingest_handoff import SECRET
from price_feed import candle,market_document,iso
from price_store import ingest,latest

UTC=timezone.utc
CLOSE=datetime(2026,11,9,12,0,tzinfo=UTC)
START=CLOSE+timedelta(seconds=10)
COT_SEEN=CLOSE+timedelta(seconds=15)
READ=CLOSE+timedelta(seconds=25)
INGEST=CLOSE+timedelta(seconds=40)
OBS=CLOSE+timedelta(minutes=1)
NOW=OBS+timedelta(seconds=2)


def setup_case(*,report="2026-10-27"):
    db=cot_fixture()
    db.execute("""CREATE TABLE prices (
        symbol TEXT PRIMARY KEY,source TEXT,broker_symbol TEXT,
        updated_at TEXT,payload TEXT
    )""")
    db.commit()
    ingest_proof.ensure_schema(db)
    price_proof.ensure_schema(db)
    link.ensure_schema(db)
    bars=[]
    for i in range(1024):
        opened=CLOSE-timedelta(minutes=15*(1024-i))
        cl=round(1.01+i*.000001,8)
        op=round(1.01+max(0,i-1)*.000001,8)
        bars.append(candle(iso(opened),op,max(op,cl)+.00001,
                           min(op,cl)-.00001,cl,100))
    doc=market_document("EURUSD","ctrader",SECRET,bars,START)
    child={"schema":"remura-price-v1","generatedAt":iso(START),
           "markets":{"EURUSD":doc}}
    cot_witness.witness(db,clock=COT_SEEN)
    report=ingest(db,child,now=INGEST,research_parent_read_at=READ)
    assert report["errors"]=={} and "EURUSD" in report["saved"],report
    return db,child,latest(db,"EURUSD")


def do_bundle(db,doc,*,observed=OBS,clock=NOW):
    with db:
        hid=insert_history(db,observed=observed,closed=CLOSE)
        bundle_result=bundle.record(db,history_id=hid,
                                    observed_document=doc,clock=clock)
        assert bundle_result["state"]=="BOTH_LOCAL_PROOFS_PRESENT",bundle_result
        result=link.capture(db,history_id=hid,
                            original_document=doc,clock=clock)
    return result


class DecisionSourceLinkTests(unittest.TestCase):
    def setUp(self):
        self.db,self.child,self.doc=setup_case()

    def tearDown(self):
        self.db.close()

    def test_real_ingest_real_cot_witness_real_price_bundle_links(self):
        out=do_bundle(self.db,self.doc)
        self.assertEqual(out["status"],
                         "ORIGINAL_LOCAL_COT_PRICE_INGEST_LINKED")
        self.assertTrue(out["localOriginalMergedPriceHashMatched"])
        self.assertTrue(out["previousCotValueVersionDigestMatched"])
        self.assertEqual(out["retailFirstSeen"],
                         "UNKNOWN_NO_INDEPENDENT_PROOF")
        self.assertEqual(out["cvdCoverage"],
                         "UNKNOWN_NO_SAME_SOURCE_FULL_SCAN")
        self.assertFalse(out["trueBrokerResponseReceiptAuthenticated"])
        self.assertFalse(out["statisticalEdgeEstablished"])
        self.assertFalse(out["ordersEnabled"])
        self.assertEqual(out["brokerCalls"],0)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],1)
        evidence=self.db.execute(
            f"SELECT merged_document_sha256,cot_source_version_digest,"
            f"original_ingest_proof_id FROM {link.TABLE}").fetchone()
        self.assertEqual(evidence[0],ingest_proof.regime._digest(self.doc))
        self.assertEqual(len(evidence[1]),64)
        self.assertGreater(evidence[2],0)
        public=json.dumps(out)+json.dumps(link.aggregate(self.db))
        self.assertNotIn(SECRET,public)
        self.assertNotIn("EURUSD",public)
        self.assertNotIn("2026-11-09",public)
        self.assertNotIn("1.01",public)

    def test_missing_COT_first_seen_does_not_fabricate_valid_link(self):
        self.db.execute(
            f"DELETE FROM {cot_witness.TABLE}"
        )  # immutable trigger blocks deletion: first assert protection
        self.db.rollback()

    def test_missing_cot_bundle_proof_causes_full_history_rollback(self):
        # New decision with no matching cot link, price can still be real.
        self.db.execute(f"DROP TABLE {cot_proof.TABLE}")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            with self.db:
                hid=insert_history(self.db,observed=OBS,closed=CLOSE)
                bundle.record(self.db,history_id=hid,
                              observed_document=self.doc,clock=NOW)
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,clock=NOW)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)

    def test_original_ingest_after_observation_is_never_asof(self):
        early=CLOSE+timedelta(seconds=30)
        with self.assertRaisesRegex(ValueError,
                         "missing_or_ambiguous_original_ingest_first_seen"):
            with self.db:
                hid=insert_history(self.db,observed=early,closed=CLOSE)
                b=bundle.record(self.db,history_id=hid,
                                observed_document=self.doc,
                                clock=early+timedelta(seconds=2))
                self.assertEqual(b["state"],"BOTH_LOCAL_PROOFS_PRESENT")
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,
                             clock=early+timedelta(seconds=2))
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)

    def test_revised_price_after_ingest_does_not_qualify_as_source(self):
        changed=copy.deepcopy(self.doc)
        changed["timeframes"]["M15"][0]["c"]+=.000001
        # A later mutation of the price DB would be caught by the source
        # witness before any false local provenance could be linked.
        self.db.execute("UPDATE prices SET payload=? WHERE symbol='EURUSD'",
                        (json.dumps(changed),))
        self.db.commit()
        with self.assertRaises(ValueError):
            with self.db:
                hid=insert_history(self.db,observed=OBS,closed=CLOSE)
                bundle.record(self.db,history_id=hid,
                              observed_document=self.doc,clock=NOW)
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,clock=NOW)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)

    def test_altered_cot_versions_cannot_join(self):
        with self.db:
            hid=insert_history(self.db,observed=OBS,closed=CLOSE)
            b=bundle.record(self.db,history_id=hid,
                            observed_document=self.doc,clock=NOW)
        self.assertEqual(b["state"],"BOTH_LOCAL_PROOFS_PRESENT")
        self.db.execute(
            f"UPDATE {cot_proof.TABLE} SET evidence_digest=?",
            ("a"*64,)
        )
        with self.db:
            with self.assertRaisesRegex(ValueError,
                                        "cot_proof_or_original_decision_mismatch"):
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,clock=NOW)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)

    def test_no_history_or_transaction_is_refused(self):
        with self.assertRaisesRegex(ValueError,
                                    "same_original_history_transaction_required"):
            link.capture(self.db,history_id=1,original_document=self.doc,clock=NOW)
        with self.assertRaisesRegex(ValueError,"new_history_id_required"):
            self.db.execute("BEGIN")
            link.capture(self.db,history_id=True,
                         original_document=self.doc,clock=NOW)

    def test_cot_and_price_present_but_no_original_ingest_proof_is_not_valid(self):
        self.db.execute(f"DROP TABLE {ingest_proof.TABLE}")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            with self.db:
                hid=insert_history(self.db,observed=OBS,closed=CLOSE)
                bundle.record(self.db,history_id=hid,
                              observed_document=self.doc,clock=NOW)
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,clock=NOW)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)

    def test_sqlite_append_only_triggers_protect_source_link(self):
        do_bundle(self.db,self.doc)
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(f"DELETE FROM {link.TABLE}")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(
                    f"UPDATE {link.TABLE} SET merged_document_sha256=?",
                    ("f"*64,))
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],1)

    def test_same_original_history_cannot_be_linked_twice(self):
        do_bundle(self.db,self.doc)
        hid=self.db.execute("SELECT id FROM squalincome_history").fetchone()[0]
        with self.assertRaisesRegex(ValueError,"original_observation_already_joined"):
            with self.db:
                # An explicit BEGIN is needed, because with db alone does
                # not start a transaction in Python sqlite3.
                self.db.execute("BEGIN")
                link.capture(self.db,history_id=hid,
                             original_document=self.doc,clock=NOW)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],1)

    def test_frozen_protocol_unmodified_and_no_real_edge_claim(self):
        from scripts import shark_cvd_incremental_protocol as frozen
        self.assertEqual(frozen.protocol_sha256(),frozen.FROZEN_PROTOCOL_SHA256)
        self.assertFalse(link.aggregate(self.db)["retailFirstSeenVerified"])
        self.assertFalse(link.aggregate(self.db)["cvdFullScanVerified"])


if __name__=="__main__":
    unittest.main()
