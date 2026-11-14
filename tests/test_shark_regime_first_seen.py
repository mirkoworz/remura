"""Synthetic SQLite tests for offline first-seen regime witness. No market data."""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from scripts import shark_market_regime_context as classifier
from scripts import shark_price_asof_evidence as price
from scripts import shark_regime_first_seen as regime

UTC=timezone.utc
CLOSE=datetime(2026,11,9,11,0,tzinfo=UTC)
OBS=CLOSE+timedelta(minutes=1)
NOW=OBS+timedelta(seconds=2)
RECEIVED=CLOSE+timedelta(seconds=20)
FAKE_BROKER="FAKE_PRIVATE_BROKER_NEVER_EXPOSE"


def stamp(d):
    return d.isoformat().replace("+00:00","Z")


def fixture():
    db=sqlite3.connect(":memory:")
    db.executescript("""
        CREATE TABLE prices(symbol TEXT PRIMARY KEY,source TEXT,
            broker_symbol TEXT,updated_at TEXT,payload TEXT);
        CREATE TABLE squalincome_history(
            id INTEGER PRIMARY KEY AUTOINCREMENT, symbol TEXT,
            state TEXT,cot_side INTEGER,price_side INTEGER,h4_side INTEGER,
            h1_side INTEGER,m15_side INTEGER,price_state TEXT,
            report_date TEXT,price_time TEXT,observed_at TEXT,
            cot_weekly REAL,origin TEXT,
            UNIQUE(symbol,report_date,price_time));
    """)
    bars=[]
    for i in range(1024):
        t=CLOSE-timedelta(minutes=15*(1024-i))
        c=round(1.0+i*.00001,8)
        o=round(1.0+max(0,i-1)*.00001,8)
        bars.append({"t":stamp(t),"o":o,
                     "h":max(o,c)+.00001,"l":min(o,c)-.00001,
                     "c":c,"v":100})
    def rollup(duration):
        groups={}
        for bar in bars:
            t=datetime.fromisoformat(bar["t"].replace("Z","+00:00"))
            key=datetime.fromtimestamp(
                int(t.timestamp())//duration*duration,tz=UTC)
            groups.setdefault(key,[]).append(bar)
        result=[]
        n=duration//900
        for key,group in sorted(groups.items()):
            if len(group)!=n:
                continue
            result.append({"t":stamp(key),
                           "o":group[0]["o"],
                           "h":max(x["h"] for x in group),
                           "l":min(x["l"] for x in group),
                           "c":group[-1]["c"],
                           "v":sum(x["v"] for x in group)})
        return result
    doc={"symbol":"EURUSD","provider":"ctrader",
         "providerSymbol":FAKE_BROKER,"timezone":"UTC",
         "sourceTimeframe":"M15","lastComplete":bars[-1]["t"],
         "timeframes":{"M15":bars,"H1":rollup(3600),
                       "H4":rollup(14400)}}
    db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",
               ("EURUSD","ctrader",FAKE_BROKER,bars[-1]["t"],json.dumps(doc)))
    db.commit()
    price.ensure_schema(db)
    regime.ensure_schema(db)
    return db,doc


def insert(db):
    return db.execute(
        "INSERT INTO squalincome_history("
        "symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin)"
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("EURUSD","aligned",1,1,1,1,1,"confirmed","2026-11-03",
         stamp(CLOSE),stamp(OBS),5.,"update")
    ).lastrowid


def capture(db,doc,*,receipt=None,clock=NOW,verify_price=True):
    with db:
        hid=insert(db)
        if verify_price:
            price.capture(db,history_id=hid,observed_document=doc,clock=clock)
        result=regime.capture(
            db,history_id=hid,observed_document=doc,
            source_received_at=stamp(receipt or RECEIVED),clock=clock)
    return hid,result


class RegimeFirstSeenTests(unittest.TestCase):
    def setUp(self):
        self.db,self.doc=fixture()

    def tearDown(self):
        self.db.close()

    def test_real_price_asof_witness_and_regime_in_one_synthetic_transaction(self):
        hid,out=capture(self.db,self.doc)
        self.assertEqual(hid,1)
        self.assertEqual(out["status"],
                         "LOCALLY_WITNESSED_REGIME_RESEARCH_ONLY")
        self.assertEqual(out["regime"],"DIRECTIONAL_UP")
        self.assertEqual(classifier.classify({
            "symbol":"EURUSD","observedAtUtc":stamp(OBS),
            "firstRecordedAtUtc":stamp(OBS),
            "sourceReceivedAtUtc":stamp(RECEIVED),
            "originalDocumentSha256":classifier._digest(self.doc),
            "document":self.doc},as_of=stamp(NOW))["state"],
            "DIRECTIONAL_UP")
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],1)
        proof=self.db.execute(
            "SELECT source_document_sha256,state,efficiency_ratio "
            "FROM research_squalincome_regime_first_seen"
        ).fetchone()
        self.assertEqual(proof[0],classifier._digest(self.doc))
        self.assertEqual(proof[1],"DIRECTIONAL_UP")
        self.assertEqual(proof[2],1.0)
        output=json.dumps(out)+json.dumps(regime.aggregate(self.db))
        self.assertNotIn(FAKE_BROKER,output)
        self.assertNotIn("EURUSD",output)
        self.assertNotIn("2026-11-09T11",output)
        self.assertFalse(out["statisticalEdgeEstablished"])
        self.assertFalse(out["sourceReceiptIndependentlyAuthenticated"])
        self.assertFalse(regime.aggregate(self.db)["liveRecorderWired"])
        self.assertEqual(out["brokerCalls"],0)

    def test_missing_original_price_proof_cannot_record_or_commit(self):
        with self.assertRaisesRegex(ValueError,
                                    "matching_original_price_evidence_missing"):
            capture(self.db,self.doc,verify_price=False)
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],0)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history")
                   .fetchone()[0],0)

    def test_later_price_document_change_after_asof_capture_fails_rollback(self):
        later=copy.deepcopy(self.doc)
        later["timeframes"]["M15"][0]["c"]+=.0001
        with self.assertRaisesRegex(ValueError,"price_evidence_original_document_sha_mismatch"):
            with self.db:
                hid=insert(self.db)
                price.capture(self.db,history_id=hid,
                              observed_document=self.doc,clock=NOW)
                regime.capture(self.db,history_id=hid,
                               observed_document=later,
                               source_received_at=stamp(RECEIVED),clock=NOW)
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],0)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history")
                   .fetchone()[0],0)

    def test_impossible_receipt_and_late_write_refused(self):
        for receipt,clock in [
            (CLOSE-timedelta(seconds=1), NOW),
            (OBS+timedelta(seconds=1), NOW),
            (RECEIVED, OBS+timedelta(seconds=31)),
        ]:
            with self.subTest(receipt=receipt,clock=clock):
                with self.assertRaises(ValueError):
                    capture(self.db,self.doc,receipt=receipt,clock=clock)
                self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],0)

    def test_original_history_must_be_fresh_after_protocol_start(self):
        earlier=OBS-timedelta(days=1)
        # The *price* witness also refuses an old observation clock, so
        # exercise the new regime's independent protocol-start gate directly.
        with self.assertRaisesRegex(ValueError,
                                    "frozen_protocol_or_prospective_start_invalid"):
            with self.db:
                hid=insert(self.db)
                regime.capture(self.db,history_id=hid,
                    observed_document=self.doc,
                    source_received_at=stamp(RECEIVED),clock=earlier)
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],0)
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history")
                   .fetchone()[0],0)

    def test_rebinding_and_update_delete_are_impossible(self):
        hid,_=capture(self.db,self.doc)
        with self.db:
            # sqlite3 "with connection" alone does NOT start a transaction.
            self.db.execute("BEGIN")
            with self.assertRaisesRegex(ValueError,
                       "regime_evidence_cannot_be_rebound_or_backfilled"):
                regime.capture(self.db,history_id=hid,
                    observed_document=self.doc,
                    source_received_at=stamp(RECEIVED),clock=NOW)
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(
                    "UPDATE research_squalincome_regime_first_seen "
                    "SET state='LATERAL' WHERE history_id=?",(hid,))
        with self.assertRaisesRegex(sqlite3.DatabaseError,"append_only"):
            with self.db:
                self.db.execute(
                    "DELETE FROM research_squalincome_regime_first_seen "
                    "WHERE history_id=?",(hid,))
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],1)
        self.assertEqual(regime.aggregate(self.db)["byRegime"]["LATERAL"],0)

    def test_wrong_schema_or_no_transaction_cannot_be_mistaken_for_capture(self):
        with self.assertRaisesRegex(ValueError,
                                    "same_original_observation_transaction_required"):
            regime.capture(self.db,history_id=1,observed_document=self.doc,
                           source_received_at=stamp(RECEIVED),clock=NOW)
        with self.assertRaises(ValueError):
            regime.capture(None,history_id=1,observed_document=self.doc,
                           source_received_at=stamp(RECEIVED),clock=NOW)
        with self.db:
            self.db.execute("BEGIN")
            with self.assertRaisesRegex(ValueError,"new_history_id_required"):
                regime.capture(self.db,history_id=True,
                               observed_document=self.doc,
                               source_received_at=stamp(RECEIVED),clock=NOW)
        self.assertEqual(regime.aggregate(self.db)["locallyRecorded"],0)

    def test_no_price_source_spoof_in_summary_or_return(self):
        _,out=capture(self.db,self.doc)
        self.assertEqual(out["ordersEnabled"],False)
        self.assertEqual(out["notificationsEnabled"],False)
        summary=json.dumps(regime.aggregate(self.db))
        self.assertNotIn(self.doc["providerSymbol"],summary)
        self.assertNotIn(classifier._digest(self.doc),summary)
        self.assertNotIn("2026-11",summary)
        self.assertFalse(regime.aggregate(self.db)["outcomesOrCostedReturnsPresent"])


if __name__=="__main__":
    unittest.main()
