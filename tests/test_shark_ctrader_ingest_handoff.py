"""Synthetic tests using the REAL price_store.ingest() and price_feed.

Mocks neither broker prices nor secret services; all test OHLC is fabricated.
No production paths or SQLite on a VPS are accessed.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

from price_feed import candle, market_document, iso
from price_store import ingest, latest
from scripts import shark_ctrader_ingest_handoff as gate

UTC=timezone.utc
CLOSE=datetime(2026,11,9,12,0,tzinfo=UTC)
CHILD_STARTED=CLOSE+timedelta(seconds=10)
PARENT_READ=CLOSE+timedelta(seconds=25)
INGEST_DONE=CLOSE+timedelta(seconds=40)
STAGED=CLOSE+timedelta(seconds=45)
SCAN=CLOSE+timedelta(minutes=1)
SECRET="FAKE_PRIVATE_ACCOUNT_BROKER_DO_NOT_PUBLISH"


def fixture(symbol="EURUSD"):
    bars=[]
    for i in range(128):
        opened=CLOSE-timedelta(minutes=15*(128-i))
        cl=round(1.0+0.0001*i,7)
        op=round(1.0+0.0001*max(0,i-1),7)
        bars.append(candle(iso(opened),op,max(op,cl)+.00002,
                           min(op,cl)-.00002,cl,100))
    market=market_document(symbol,"ctrader",SECRET,bars,CHILD_STARTED)
    child={"schema":"remura-price-v1",
           "generatedAt":iso(CHILD_STARTED),
           "purpose":"private-local-import","intervalAlignment":"UTC",
           "markets":{symbol:market},"errors":{}}
    db=sqlite3.connect(":memory:")
    db.execute("""CREATE TABLE prices(
        symbol TEXT PRIMARY KEY,source TEXT,broker_symbol TEXT,
        updated_at TEXT,payload TEXT)""")
    report=ingest(db,child,now=PARENT_READ)
    assert symbol in report["saved"] and not report["errors"], report
    return db,child,latest(db,symbol)


def stage(child,doc,**kwargs):
    args={"symbol":"EURUSD","parent_read_at":PARENT_READ,
          "ingest_finished_at":INGEST_DONE,"staged_at":STAGED}
    args.update(kwargs)
    return gate.stage(child,doc,**args)


class CTraderHandoffTests(unittest.TestCase):
    def setUp(self):
        self.db,self.child,self.stored=fixture()

    def tearDown(self):
        self.db.close()

    def test_real_ingest_merge_and_separate_scan_verify_local_only(self):
        ctx=stage(self.child,self.stored)
        out=gate.check_scan(ctx,self.stored,scan_at=SCAN)
        self.assertEqual(out["regimeCandidate"],"DIRECTIONAL_UP")
        self.assertTrue(out["fullMergedDocumentUnchangedAtScan"])
        self.assertFalse(out["persistentFirstSeenIngestReceiptExists"])
        self.assertFalse(out["actualBrokerResponseReceiptVerified"])
        self.assertFalse(out["independentTrustedTimeOrSource"])
        self.assertFalse(out["statisticalEdgeEstablished"])
        self.assertFalse(out["liveCollectorIntegrationEnabled"])
        self.assertEqual((out["brokerCalls"],out["writes"]),(0,0))
        public=json.dumps(out)
        self.assertNotIn(SECRET,public)
        self.assertNotIn("EURUSD",public)
        self.assertNotIn("0.0001",public)
        self.assertNotIn("2026-11-09T",public)
        # Real price_store stores candle OPEN as updated_at, never receipt.
        stored_open=self.db.execute(
            "SELECT updated_at FROM prices WHERE symbol='EURUSD'").fetchone()[0]
        self.assertEqual(stored_open,iso(CLOSE-timedelta(minutes=15)))
        self.assertNotEqual(stored_open,iso(PARENT_READ))

    def test_child_market_is_not_necessarily_same_full_json_as_merged(self):
        ctx=stage(self.child,self.stored)
        self.assertIsInstance(ctx["mergedSha256"],str)
        self.assertEqual(len(ctx["mergedSha256"]),64)
        self.assertIsInstance(ctx["childSha256"],str)
        self.assertEqual(len(ctx["childSha256"]),64)
        self.assertFalse(ctx["immutableIngestReceiptRecorded"])

    def test_changed_child_bar_or_broker_at_ingest_is_rejected(self):
        altered=copy.deepcopy(self.child)
        # A valid but different close must pass OHLC validation first,
        # then fail the *same-source* cross-stage equality test.
        altered["markets"]["EURUSD"]["timeframes"]["M15"][-4]["c"]+=.00001
        with self.assertRaisesRegex(ValueError,
                                     "child_to_merged_last33_candles_changed"):
            stage(altered,self.stored)
        altered=copy.deepcopy(self.child)
        altered["markets"]["EURUSD"]["providerSymbol"]="OTHER_BROKER"
        with self.assertRaisesRegex(ValueError,
                                     "broker_mapping_changed_between_processes"):
            stage(altered,self.stored)

    def test_overwritten_stored_source_after_ingest_fails_scan(self):
        ctx=stage(self.child,self.stored)
        revised=copy.deepcopy(self.stored)
        revised["timeframes"]["M15"][0]["c"]+=.00001
        self.db.execute(
            "UPDATE prices SET payload=? WHERE symbol=?",
            (json.dumps(revised),"EURUSD"))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                     "original_price_store_revised_after_handoff"):
            gate.check_scan(ctx,latest(self.db,"EURUSD"),scan_at=SCAN)

    def test_child_generated_at_is_collection_start_not_response_receipt(self):
        wrong=copy.deepcopy(self.child)
        wrong["generatedAt"]=iso(PARENT_READ+timedelta(seconds=1))
        with self.assertRaisesRegex(ValueError,
                                     "noncausal_process_handoff_clocks"):
            stage(wrong,self.stored)
        # The only way to stage is an additional explicit parent READ clock:
        # never default to bundle.generatedAt or prices.updated_at.
        with self.assertRaisesRegex(ValueError,"explicit_actual_local_utc_clocks_required"):
            gate.stage(self.child,self.stored,symbol="EURUSD",
                       parent_read_at=None,ingest_finished_at=INGEST_DONE,
                       staged_at=STAGED)

    def test_bad_timezones_and_stale_scans_fail_closed(self):
        with self.assertRaises(ValueError):
            stage(self.child,self.stored,
                  parent_read_at=PARENT_READ.astimezone(
                      timezone(timedelta(hours=1))))
        ctx=stage(self.child,self.stored)
        with self.assertRaisesRegex(ValueError,
                                     "scan_cannot_join_stale_or_future_receipt"):
            gate.check_scan(ctx,self.stored,scan_at=SCAN+timedelta(minutes=5))
        with self.assertRaisesRegex(ValueError,
                                     "scan_cannot_join_stale_or_future_receipt"):
            gate.check_scan(ctx,self.stored,scan_at=STAGED-timedelta(seconds=1))

    def test_no_remapped_pair_or_unclosed_future_candle(self):
        altered=copy.deepcopy(self.stored)
        altered["lastComplete"]=iso(CLOSE)
        with self.assertRaisesRegex(ValueError,"last_complete_is_not_last_open"):
            stage(self.child,altered)
        other=copy.deepcopy(self.stored)
        other["symbol"]="GBPUSD"
        with self.assertRaisesRegex(ValueError,"source_mapping_unverifiable"):
            stage(self.child,other)
        with self.assertRaisesRegex(ValueError,"outside_research_universe"):
            stage(self.child,self.stored,symbol="INVALID")

    def test_noncontiguous_m15_and_missing_source_do_not_become_unknown_negatives(self):
        broken=copy.deepcopy(self.child)
        broken["markets"]["EURUSD"]["timeframes"]["M15"].pop(-5)
        with self.assertRaisesRegex(ValueError,"noncontiguous_original_m15"):
            stage(broken,self.stored)
        with self.assertRaisesRegex(ValueError,
                                     "original_child_export_required"):
            stage({},self.stored)
        with self.assertRaises(ValueError):
            stage(self.child,None)

    def test_protocol_window_begins_only_after_09_nov_utc(self):
        from scripts import shark_cvd_incremental_protocol as study
        self.assertEqual(study.protocol_sha256(),
                         study.FROZEN_PROTOCOL_SHA256)
        with self.assertRaisesRegex(ValueError,
                                     "noncausal_process_handoff_clocks"):
            stage(self.child,self.stored,
                  staged_at=datetime(2026,11,8,23,59,tzinfo=UTC))
        self.assertFalse(gate.check_scan(
            stage(self.child,self.stored),self.stored,scan_at=SCAN)
            ["cotAndRetailProofsIncluded"])


if __name__ == "__main__":
    unittest.main()
