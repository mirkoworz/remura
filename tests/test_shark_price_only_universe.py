"""Synthetic PRICE-ONLY census tests using v1.62's ACTUAL price_view.

No COT table exists in these SQLite fixtures: proof of no COT preselection.
All timestamps, quotes and symbols are test data, never live broker data.
"""
from datetime import datetime,timedelta,timezone
import json
from pathlib import Path
import sqlite3
import sys
import unittest

# Production uses these as top-level modules from scripts/, so the offline
# test deliberately runs the SAME classifier with that compatible import path.
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from price_feed import market_document
from price_store import audit_market
from signals_monitor import price_exclusion, price_view

from scripts import shark_price_only_universe as universe
from test_shark_price_asof_evidence import prepare, END, OBS, NOW, SECRET, stamp


def original(db):
    row=db.execute("SELECT payload FROM prices WHERE symbol='EURUSD'").fetchone()
    return json.loads(row[0]) if row else None


def trend(db):
    """Monotonic genuine M15 bar sequence with coherent H1/H4 rollups."""
    m15=[]
    for i in range(1024):
        when=END-timedelta(minutes=15*(1024-i))
        op=1.01 + i*0.00004
        cl=op+0.000025
        m15.append({"t":stamp(when), "o":op, "c":cl,
                    "h":cl+0.00001, "l":op-0.00001,"v":101})
    doc=market_document("EURUSD","ctrader",SECRET,m15,OBS)
    db.execute("UPDATE prices SET payload=?,updated_at=? WHERE symbol='EURUSD'",
               (json.dumps(doc),doc["lastComplete"]))
    db.commit()
    return doc


def classify(doc,when=OBS):
    quality=audit_market(doc,when)
    candidate=price_view(doc,when,quality=quality) if doc else None
    reason=("price_present" if candidate is not None
            else price_exclusion(doc,when,quality=quality))
    return quality,candidate,reason


class PriceOnlyTests(unittest.TestCase):
    def setUp(self):
        self.db=prepare()
        universe.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()

    def record(self,*,doc=None,when=OBS,clock=NOW,symbol="EURUSD",
               qa=None,candidate="auto",reason="auto"):
        doc=original(self.db) if doc is None and symbol=="EURUSD" else doc
        actual_qa,actual_candidate,actual_reason=classify(doc,when)
        if qa is None: qa=actual_qa
        if candidate=="auto": candidate=actual_candidate
        if reason=="auto": reason=actual_reason
        with self.db:
            return universe.capture(
                self.db,symbol=symbol,scan_at=stamp(when),
                observed_document=doc,quality=qa,
                price_result=candidate,price_reason=reason,clock=clock)

    def test_registry_is_all_34_markets_and_does_not_need_cot_tables(self):
        self.assertEqual(len(universe.prices_monitored()),34)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM sqlite_master WHERE name='cot_reports'"
        ).fetchone()[0],0)
        status=self.record()
        self.assertEqual(status["status"],"PRICE_NO_TREND")
        self.assertTrue(status["noCotDataUsed"])
        self.assertEqual(universe.summary(self.db)["totalScans"],1)
        self.assertEqual(universe.summary(self.db)["byState"]["PRICE_NO_TREND"],1)
        self.assertEqual(status["newBrokerCalls"],0)

    def test_existing_live_price_view_supplies_independent_candidate(self):
        doc=trend(self.db)
        quality,candidate,reason=classify(doc)
        self.assertEqual(quality["integrity"],"verified")
        self.assertEqual(quality["freshness"],"recent")
        self.assertTrue(quality["ready"])
        self.assertIsNotNone(candidate)
        self.assertEqual(candidate["side"],1)
        self.assertEqual(reason,"price_present")
        result=self.record()
        self.assertEqual(result["status"],"PRICE_CONTEXT_READY")
        self.assertTrue(result["priceQualifiedWithoutCot"])
        self.assertTrue(result["last16TickVolumeComplete"])
        self.assertFalse(result["originalPriceDirectionReproducedIndependently"])
        self.assertFalse(result["independentCollectionTimeKnown"])
        self.assertEqual(universe.summary(self.db)["byState"]["PRICE_CONTEXT_READY"],1)
        safe=json.dumps(result)+json.dumps(universe.summary(self.db))
        self.assertNotIn(SECRET,safe)
        self.assertNotIn("1.01",safe)
        self.assertNotIn("099741",safe)
        self.assertFalse(result["alertsEnabled"])
        self.assertFalse(result["ordersEnabled"])

    def test_stale_h1_not_mislabelled_as_no_trend(self):
        doc=original(self.db)
        doc["timeframes"]["H1"]=doc["timeframes"]["H1"][:-2]
        self.db.execute("UPDATE prices SET payload=?", (json.dumps(doc),))
        self.db.commit()
        qa,candidate,reason=classify(doc)
        self.assertIsNone(candidate)
        self.assertEqual(reason,"prices_stale")
        result=self.record()
        self.assertEqual(result["status"],"PRICE_QUALITY_BLOCKED")
        self.assertFalse(result["priceQualifiedWithoutCot"])

    def test_missing_price_is_real_denominator_not_missing_event(self):
        report=self.record(symbol="XAUUSD")
        self.assertEqual(report["status"],"PRICE_QUALITY_BLOCKED")
        out=universe.summary(self.db)
        self.assertEqual(out["totalScans"],1)
        self.assertFalse(out["retrospectiveHistoryReconstructed"])

    def test_15min_slot_dedupe_preserves_original_snapshot(self):
        self.assertEqual(self.record()["newRows"],1)
        result=self.record(clock=NOW+timedelta(seconds=1))
        self.assertEqual(result["status"],"DUPLICATE_SCAN_SLOT")
        self.assertEqual(universe.summary(self.db)["totalScans"],1)

    def test_refuse_future_clock_or_historical_replay(self):
        with self.assertRaisesRegex(ValueError,"scan_not_happening_now"):
            self.record(clock=NOW+timedelta(minutes=3))
        with self.assertRaises(ValueError):
            self.record(clock=OBS-timedelta(seconds=1))
        self.assertEqual(universe.summary(self.db)["totalScans"],0)

    def test_in_memory_source_change_between_classification_and_write_fails(self):
        doc=original(self.db)
        source=json.loads(json.dumps(doc))
        source["timeframes"]["M15"][0]["c"]=1.017
        self.db.execute("UPDATE prices SET payload=?", (json.dumps(source),))
        self.db.commit()
        quality,px,reason=classify(doc)
        with self.assertRaisesRegex(ValueError,"price_document_race"):
            with self.db:
                universe.capture(
                    self.db,symbol="EURUSD",scan_at=stamp(OBS),
                    observed_document=doc,quality=quality,
                    price_result=px,price_reason=reason,clock=NOW)
        self.assertEqual(universe.summary(self.db)["totalScans"],0)

    def test_quality_never_accepts_fake_candidate_from_stale_bars(self):
        trend(self.db)
        doc=original(self.db)
        quality,candidate,reason=classify(doc)
        self.assertIsNotNone(candidate)
        with self.assertRaisesRegex(ValueError,
                                    "price_signal_from_stale_or_missing_quality"):
            self.record(qa={**quality,"freshness":"stale"},
                        candidate=candidate,reason="price_present")
        self.assertEqual(universe.summary(self.db)["totalScans"],0)

    def test_invalid_reason_not_accepted(self):
        with self.assertRaisesRegex(ValueError,"price_only_reason_not_allowlisted"):
            self.record(reason="cot_negative")

    def test_optional_keeps_real_monitoring_on_invalid_quality(self):
        doc=original(self.db)
        with self.db:
            out=universe.capture_optional(
                self.db,symbol="EURUSD",scan_at=stamp(OBS),
                observed_document=doc,quality={"ready":True},
                price_result=None,price_reason="price_no_direction",clock=NOW)
        self.assertEqual(out["status"],"PRICE_UNIVERSE_NOT_RECORDED")
        self.assertFalse(out["alertsEnabled"])
        self.assertEqual(universe.summary(self.db)["totalScans"],0)

    def test_sqlite_table_failure_propagates_and_never_hides_as_nd(self):
        self.db.execute("DROP TABLE research_price_only_universe")
        self.db.commit()
        doc=original(self.db)
        qa,px,reason=classify(doc)
        with self.assertRaises(sqlite3.OperationalError):
            with self.db:
                universe.capture_optional(
                    self.db,symbol="EURUSD",scan_at=stamp(OBS),
                    observed_document=doc,quality=qa,
                    price_result=px,price_reason=reason,clock=NOW)

    def test_immutable_table_and_capacity(self):
        self.record()
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM research_price_only_universe")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE research_price_only_universe "
                            "SET price_side=1")
        self.assertEqual(universe.summary(self.db)["totalScans"],1)


if __name__=="__main__":
    unittest.main()
