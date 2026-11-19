"""REMURA Track B P0b: actual local price_store.ingest during research snapshot.

Unlike the existing synthetic UPDATE-race tests, this invokes the SAME
price_store.ingest API as the existing cTrader collector uses. There is no
broker connection: both prices and the SQLite file are synthetic. The first
attempt MUST abort without recording an invalid COT/price observation; the
later fresh retry can seal a genuine new research snapshot, without any
fabricated time or retrospective repair.
"""
from __future__ import annotations

from datetime import timedelta
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from price_feed import market_document
from price_store import connect, ingest, latest
import signals_monitor as scanner
from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_only_compact as compact
from test_shark_staging_scan import fixture, clone, standard_state, NOW, END, stamp


class RealIngestRaceTests(unittest.TestCase):
    def test_full_scan_rejects_concurrent_real_ingest_and_fresh_retry(self):
        with tempfile.TemporaryDirectory(prefix="remura-real-ingest-race-") as td:
            root=Path(td)
            baseline=root/"baseline.sqlite"
            staged=root/"staged.sqlite"
            # 34 synthetic markets, and one synthetic COT report series;
            # proves both price-only denominator and real Squalincome
            # candidate are guarded from old source mix.
            fixture(baseline,with_cot=True,all_priced=True,m15_count=1024)
            clone(baseline,staged)
            expected=standard_state(staged)
            with sqlite3.connect(staged) as db:
                original=latest(db,"EURUSD")
            last=original["timeframes"]["M15"][-1]
            self.assertEqual(last["t"],stamp(END-timedelta(minutes=15)))
            # One new synthetic *closed* M15, no HTTP/broker call.
            op=float(last["c"])
            cl=op+0.000025
            newest={"t":stamp(END),"o":op,"h":cl+0.00001,
                    "l":op-0.00001,"c":cl,"v":103}
            incoming=market_document(
                "EURUSD","ctrader",original["providerSymbol"],[newest],NOW)
            packet={"schema":"remura-price-v1",
                    "generatedAt":stamp(NOW),"markets":{"EURUSD":incoming}}
            original_classify=scanner.classify
            imported=[False]

            def ingest_while_scanner_holds_read_snapshot(cot,price):
                if not imported[0]:
                    # This is the actual application price ingest function,
                    # using a distinct connection. WAL permits the writer
                    # to commit during the scanner's read snapshot.
                    db=connect(staged,timeout=1.0)
                    try:
                        outcome=ingest(db,packet,now=NOW)
                    finally:
                        db.close()
                    self.assertEqual(outcome["errors"],{})
                    self.assertIn("EURUSD",outcome["saved"])
                    imported[0]=True
                return original_classify(cot,price)

            with patch.object(witness,"_clock",
                              return_value=NOW+timedelta(seconds=2)):
                with patch.object(
                        scanner,"classify",
                        side_effect=ingest_while_scanner_holds_read_snapshot):
                    with self.assertRaisesRegex(
                            sqlite3.OperationalError,
                            "research_source_changed_before_atomic_commit"):
                        scanner.scan_once_with_compact_price_only_research(
                            staged,NOW)
            self.assertTrue(imported[0])
            self.assertEqual(standard_state(staged),expected)
            with sqlite3.connect(staged) as db:
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM research_price_only_batches"
                ).fetchone()[0],0)
                updated=latest(db,"EURUSD")
                self.assertEqual(updated["timeframes"]["M15"][-1]["t"],
                                 stamp(END))
                self.assertNotEqual(updated,original)
                self.assertEqual(db.execute(
                    "PRAGMA integrity_check").fetchone()[0],"ok")
            # Independent later scan uses the NEW source version; previous
            # failed slot is not backfilled or labelled as a trading event.
            with patch.object(witness,"_clock",
                              return_value=NOW+timedelta(seconds=2)):
                recovered=scanner.scan_once_with_compact_price_only_research(
                    staged,NOW)
            self.assertEqual(recovered["priceOnlyResearch"]["storedMarkets"],34)
            self.assertEqual(
                recovered["priceOnlyResearch"]["batchStatus"],
                "COMPACT_BATCH_SEALED")
            with sqlite3.connect(staged) as db:
                result=compact.verify(
                    db,scan_slot=stamp(
                        NOW.replace(minute=15,second=0,microsecond=0)))
                self.assertEqual(result["status"],"ARCHIVE_VERIFIED")
                self.assertEqual(result["marketObservations"],34)
                self.assertEqual(db.execute(
                    "PRAGMA integrity_check").fetchone()[0],"ok")

if __name__=="__main__":
    unittest.main()
