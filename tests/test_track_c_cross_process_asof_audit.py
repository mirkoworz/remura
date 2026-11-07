"""Track C2c-d dual-market synthetic CFTC/cTrader/Myfxbook -> Squalincome.

Original Track B modules are imported ONLY from an exact pinned checkout.
The COT HTTP clock ledger is a separate synthetic temporary SQLite database;
the B science database uses memory ONLY. No GET/API, oracle, credentials,
positions, real source timestamps, trading or notifications.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
B_ROOT = ROOT / "track-b-pinned"
if not (B_ROOT / "scripts/shark_retail_first_seen.py").is_file():
    raise RuntimeError("exact_pinned_original_track_b_required")
sys.path.insert(0, str(B_ROOT / "tests"))
sys.path.insert(0, str(B_ROOT / "scripts"))
sys.path.insert(0, str(B_ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

from scripts import track_c_cross_process_asof_audit as cross
from scripts import track_c_cot_atomic_b_witness as cbridge
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_signal_ingest_decision_link as link
from scripts import shark_cot_asof_witness as witness
import cot_monitor as collector
from price_feed import market_document, iso
from price_store import connect, ingest, latest
from test_shark_signal_ingest_decision_link import (
    setup_case, START, READ as PRICE_READ, INGEST, OBS, NOW, CLOSE, SECRET,
)
from test_shark_retail_receipt_handoff import original_pair
from test_shark_retail_first_seen import READ as RETAIL_READ, RECORDED
from test_shark_original_decision_atomic_gate import new_history

UTC = timezone.utc
COT_CLOCK = datetime(2026, 11, 9, 12, 0, tzinfo=UTC)
COT_CLOCKS = [COT_CLOCK + timedelta(seconds=x) for x in (1,3,5,6,8,10)]
PILOT = {"tff": "099741", "disagg": "088691"}


def gold_history(db):
    """One *new* XAUUSD original synthetic observation, not replay/backfill."""
    return db.execute(
        "INSERT INTO squalincome_history "
        "(symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("XAUUSD", "aligned", 1, 1, 1, 1, 1, "confirmed",
         "2026-10-27", iso(CLOSE), iso(OBS), 5.0, "update"),
    )


class TwoMarketOriginalBAndCotReceiptTests(unittest.TestCase):
    def setUp(self):
        # The fixture actually uses B's REAL original price_store.ingest and
        # exact COT source witness, not fabricated source-link return values.
        self.db, self.eur_child, self.eur_doc = setup_case()
        retail.ensure_schema(self.db)
        numeric.ensure_schema(self.db)

        # Gold is ingested independently with the same B merger/first-seen
        # path; no source store or scientific model is cloned.
        original_bars = self.eur_child["markets"]["EURUSD"]["timeframes"]["M15"]
        gold_market = market_document(
            "XAUUSD", "ctrader", "SYNTHETIC-ORIGINAL-GOLD", original_bars, START
        )
        gold_child = {"schema": "remura-price-v1",
                      "generatedAt": iso(START),
                      "markets": {"XAUUSD": gold_market}}
        report = ingest(self.db, gold_child, now=INGEST,
                        research_parent_read_at=PRICE_READ)
        self.assertEqual(report["errors"], {})
        self.assertEqual(set(report["saved"]), {"XAUUSD"})
        self.gold_doc = latest(self.db, "XAUUSD")
        self.assertIsNotNone(self.gold_doc)

        self.retail = original_pair()
        prior = retail.capture_pair(
            self.db, original_snapshot=self.retail,
            file_read_at=RETAIL_READ, clock=RECORDED,
            research_numeric_features=True,
        )
        self.assertEqual(prior["pilotCount"], 2)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0], 2)

        self.temporary = tempfile.TemporaryDirectory(prefix="track-c-asof-")
        self.cot_file = Path(self.temporary.name) / cbridge.FILE_NAME
        db = connect(self.cot_file)
        collector.ensure_table(db)
        witness.ensure_schema(db)
        cbridge.ensure_schema(db, mode=cbridge.MODE)
        db.close()

        # This simulated HTTP response is derived from the same synthetic B
        # COT fixture. Therefore equality proves software handoff only,
        # NOT independent source authenticity.
        def mocked_fetch(dataset, t):
            self.assertEqual(t, COT_CLOCK)
            code = PILOT[dataset]
            fields = collector.DATASETS[dataset]["keys"]
            records = []
            for week, oi, long1, short1, long2, short2 in self.db.execute(
                "SELECT report_date,oi,first_long,first_short,"
                "second_long,second_short FROM cot_reports "
                "WHERE dataset=? AND code=? ORDER BY report_date",
                (dataset, code)
            ).fetchall():
                payload = {
                    "report_date_as_yyyy_mm_dd": week + "T00:00:00",
                    "cftc_contract_market_code": code,
                    "open_interest_all": oi,
                }
                payload.update(dict(zip(fields, (long1,short1,long2,short2))))
                records.append(payload)
            return records

        self.cot_calls=[]
        def capture_fetch(dataset,t):
            self.cot_calls.append(dataset)
            return mocked_fetch(dataset,t)
        with patch.object(collector,"utcnow",side_effect=COT_CLOCKS):
            out = collector.collect_once(
                self.cot_file, now=COT_CLOCK, fetch=capture_fetch,
                research_atomic_witness=cbridge.OriginalBAtomicWitness(
                    mode=cbridge.MODE),
            )
        self.assertEqual(out["errors"], {})
        self.assertEqual(self.cot_calls, ["tff","disagg"])

        self.ids = {}
        first = atomic.record_new(
            self.db, insert_history=new_history,
            original_document=self.eur_doc, clock=NOW,
            research_retail_inbox=True,
        )
        self.assertTrue(first["wholeTransactionCommittedTogether"])
        self.ids["EURUSD"]=self.db.execute(
            "SELECT id FROM squalincome_history WHERE symbol='EURUSD'"
        ).fetchone()[0]
        second = atomic.record_new(
            self.db, insert_history=gold_history,
            original_document=self.gold_doc, clock=NOW,
            research_retail_inbox=True,
        )
        self.assertTrue(second["wholeTransactionCommittedTogether"])
        self.ids["XAUUSD"]=self.db.execute(
            "SELECT id FROM squalincome_history WHERE symbol='XAUUSD'"
        ).fetchone()[0]

        self.cot = sqlite3.connect(
            "file:" + str(self.cot_file) + "?mode=ro", uri=True
        )
        self.cot.execute("PRAGMA query_only=ON")
        self.db.execute("PRAGMA query_only=ON")

    def tearDown(self):
        self.cot.close()
        self.db.close()
        self.temporary.cleanup()

    def run_audit(self, **kw):
        options = dict(original_history_ids=self.ids,mode=cross.MODE)
        options.update(kw)
        return cross.audit(self.cot, self.db, **options)

    def test_two_real_B_decisions_and_four_original_local_source_chains(self):
        evidence=self.run_audit()
        self.assertEqual(evidence["researchMarketsValidated"],2)
        self.assertEqual(evidence["localHttpDatasetReceipts"],2)
        self.assertEqual(evidence["originalBDecisionLinksValidated"],2)
        self.assertTrue(evidence["distinctDbTransactions"])
        self.assertFalse(evidence["crossDatabaseAtomicityProven"])
        self.assertFalse(evidence["localClockProviderSigned"])
        self.assertFalse(evidence["sourceWasActualRetailSignalInput"])
        self.assertFalse(evidence["realEdgeEstablished"])
        self.assertFalse(evidence["liveEnabled"])
        self.assertFalse(evidence["actualMarketData"])
        self.assertFalse(evidence["actualOOSOutcomes"])
        self.assertEqual(evidence["additionalApiCalls"],0)
        self.assertEqual(evidence["cvd"],"UNKNOWN")
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {link.TABLE}").fetchone()[0],2)
        safe=json.dumps(evidence)
        for forbidden in ("EURUSD","XAUUSD","62.5",SECRET,
                          "099741","088691","2026-11-09"):
            self.assertNotIn(forbidden,safe)

    def test_one_missing_original_decision_is_not_both_markets(self):
        with self.assertRaisesRegex(ValueError,"exact_two_new_original"):
            self.run_audit(original_history_ids={"EURUSD":self.ids["EURUSD"]})
        with self.assertRaisesRegex(ValueError,"original_history_id_or_symbol"):
            self.run_audit(original_history_ids={
                "EURUSD":self.ids["XAUUSD"],
                "XAUUSD":self.ids["EURUSD"],
            })

    def test_drift_in_cot_http_original_does_not_qualify(self):
        self.cot.execute("PRAGMA query_only=OFF")
        self.cot.execute(
            "UPDATE cot_reports SET first_long=first_long+1 "
            "WHERE dataset='tff' AND code='099741' AND report_date='2026-10-27'"
        )
        self.cot.commit()
        self.cot.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,
                                   "cot_source_and_http_witness_mismatch"):
            self.run_audit()

    def test_drift_in_original_B_cot_source_does_not_qualify(self):
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute(
            "UPDATE cot_reports SET first_long=first_long+1 "
            "WHERE dataset='disagg' AND code='088691' "
            "AND report_date='2026-10-27'"
        )
        self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,
                                   "cross_process_original_cot_values_differ"):
            self.run_audit()

    def test_missing_gold_merged_source_is_not_filled_with_eur(self):
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute("DELETE FROM prices WHERE symbol='XAUUSD'")
        self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
        with self.assertRaisesRegex(ValueError,
                                   "original_merged_cTrader_document_missing"):
            self.run_audit()

    def test_not_read_only_is_rejected(self):
        self.db.execute("PRAGMA query_only=OFF")
        with self.assertRaisesRegex(ValueError,"read_only_connection_required"):
            self.run_audit()

    def test_explicit_mode_and_event_identity_are_required(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline_cross_process"):
            self.run_audit(mode=None)
        with self.assertRaisesRegex(ValueError,"exact_two_new_original"):
            self.run_audit(original_history_ids={
                "EURUSD": True,"XAUUSD":self.ids["XAUUSD"]})

    def test_unavailable_late_http_receipt_cannot_be_backfilled(self):
        self.cot.execute("PRAGMA query_only=OFF")
        # Ledger itself prevents changes even in synthetic DB.
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.cot:
                self.cot.execute(
                    "UPDATE research_track_c_cot_http_receipts "
                    "SET response_received_at='2099-01-01T00:00:00Z'")
        self.cot.execute("PRAGMA query_only=ON")
        self.assertEqual(self.run_audit()["researchMarketsValidated"],2)


if __name__ == "__main__":
    unittest.main()
