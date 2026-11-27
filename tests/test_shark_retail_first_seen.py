"""Synthetic original Myfxbook first-seen, optional atomic local context, CVD UNKNOWN."""
from __future__ import annotations
import copy
from datetime import datetime,timedelta,timezone
import json
import sqlite3
import unittest
from scripts import shark_retail_first_seen as retail
from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_cvd_incremental_protocol as study
from scripts import shark_signal_ingest_decision_link as link
from test_shark_signal_ingest_decision_link import setup_case,NOW,OBS,SECRET
from test_shark_original_decision_atomic_gate import new_history
from update_myfxbook import snapshot as build_actual_myfxbook_row

UTC=timezone.utc
UPDATED="2026-11-09T11:55:00Z"
READ=datetime(2026,11,9,11,58,50,tzinfo=UTC)
RECORDED=READ+timedelta(seconds=5)


def original():
    row=build_actual_myfxbook_row(UPDATED,{
        "longPercentage":62.5,"shortPercentage":37.5,
        "longVolume":1200.5,"shortVolume":800.25,
        "longPositions":950,"shortPositions":725,
        "avgLongPrice":1.08,"avgShortPrice":1.075,
    })
    return {"status":"ok","source":"Myfxbook Community Outlook",
            "updatedAt":UPDATED,"symbols":{"EURUSD":row}}


class RetailWitnessTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.doc=setup_case()
        retail.ensure_schema(self.db)
        self.snap=original()

    def tearDown(self):
        self.db.close()

    def first(self,**kwargs):
        values={"symbol":"EURUSD","original_snapshot":self.snap,
                "file_read_at":READ,"clock":RECORDED}
        values.update(kwargs)
        return retail.capture(self.db,**values)

    def original_signal(self,**kwargs):
        values={"insert_history":new_history,
                "original_document":self.doc,"clock":NOW,
                "original_retail_snapshot":self.snap}
        values.update(kwargs)
        return atomic.record_new(self.db,**values)

    def count(self):
        return self.db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0]

    def test_valid_original_retail_context_not_an_original_signal_input(self):
        self.first()
        result=self.original_signal()
        self.assertEqual(result["retailFirstSeen"],
                         "LOCAL_PRIOR_CONTEXT_NOT_SIGNAL_INPUT")
        self.assertFalse(result["retailUsedByOriginalSqualincomeSignal"])
        self.assertEqual(self.count(),1)
        self.assertEqual(retail.aggregate(self.db)["localFirstSeenSnapshots"],1)
        self.assertEqual(retail.aggregate(self.db)["localOriginalSignalContextLinks"],1)
        self.assertFalse(retail.aggregate(self.db)["cvdScansAdmitted"])
        self.assertFalse(result["statisticalEdgeEstablished"])
        safe=json.dumps(result)+json.dumps(retail.aggregate(self.db))
        for secret in ("EURUSD",SECRET,UPDATED,"62.5","1200.5"):
            self.assertNotIn(secret,safe)

    def test_default_original_decision_stays_unknown(self):
        result=self.original_signal(original_retail_snapshot=None)
        self.assertEqual(result["retailFirstSeen"],"UNKNOWN")
        self.assertEqual(result["cvdCoverage"],"UNKNOWN")
        self.assertEqual(retail.aggregate(self.db)["localOriginalSignalContextLinks"],0)

    def test_missing_local_prior_receipt_causes_total_strict_rollback(self):
        with self.assertRaisesRegex(ValueError,
                                    "original_retail_local_receipt_missing"):
            self.original_signal()
        self.assertEqual(self.count(),0)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)
        self.assertEqual(retail.aggregate(self.db)["localOriginalSignalContextLinks"],0)

    def test_different_retail_values_cannot_be_backfilled(self):
        self.first()
        later=copy.deepcopy(self.snap)
        later["symbols"]["EURUSD"]["lPct"]=72
        later["symbols"]["EURUSD"]["sPct"]=28
        with self.assertRaisesRegex(ValueError,
                                    "retail_source_not_known_at_original_signal"):
            self.original_signal(original_retail_snapshot=later)
        self.assertEqual(self.count(),0)

    def test_retail_receipt_after_signal_must_not_be_retro_eligible(self):
        self.first(file_read_at=OBS+timedelta(seconds=1),
                   clock=OBS+timedelta(seconds=2))
        with self.assertRaisesRegex(ValueError,
                                    "retail_source_not_known_at_original_signal"):
            self.original_signal()
        self.assertEqual(self.count(),0)

    def test_stale_duplicate_and_future_source_rejected(self):
        stale=copy.deepcopy(self.snap)
        stale["updatedAt"]="2026-11-09T11:00:00Z"
        stale["symbols"]["EURUSD"]["t"]=stale["updatedAt"]
        with self.assertRaisesRegex(ValueError,
                                    "retail_local_first_seen_not_causal_or_fresh"):
            self.first(original_snapshot=stale)
        future=copy.deepcopy(self.snap)
        future["updatedAt"]="2026-11-09T11:59:00Z"
        future["symbols"]["EURUSD"]["t"]=future["updatedAt"]
        with self.assertRaises(ValueError):
            self.first(original_snapshot=future)
        self.first()
        with self.assertRaisesRegex(ValueError,
                                    "duplicate_or_backfilled_retail_snapshot"):
            self.first()
        self.assertEqual(retail.aggregate(self.db)["localFirstSeenSnapshots"],1)

    def test_fake_numeric_or_source_does_not_create_proof(self):
        for value in (-1,120,float("nan"),None):
            with self.subTest(value=str(value)):
                invalid=copy.deepcopy(self.snap)
                invalid["symbols"]["EURUSD"]["lPct"]=value
                with self.assertRaises(ValueError):
                    self.first(original_snapshot=invalid)
        extra=copy.deepcopy(self.snap)
        extra["password"]="private"
        with self.assertRaises(ValueError):
            self.first(original_snapshot=extra)
        self.assertEqual(retail.aggregate(self.db)["localFirstSeenSnapshots"],0)

    def test_explicit_local_utc_clock_not_from_updated_at(self):
        with self.assertRaisesRegex(ValueError,
                                    "explicit_real_utc_runtime_clock_required"):
            self.first(file_read_at=UPDATED)
        with self.assertRaises(ValueError):
            self.first(file_read_at=READ.astimezone(
                timezone(timedelta(hours=1))))
        self.assertEqual(retail.aggregate(self.db)["localFirstSeenSnapshots"],0)

    def test_sqlite_append_only_retail_and_context(self):
        self.first()
        self.original_signal()
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.db:
                self.db.execute(f"UPDATE {retail.TABLE} SET symbol='XAUUSD'")
        with self.assertRaisesRegex(sqlite3.IntegrityError,"append_only"):
            with self.db:
                self.db.execute(f"DELETE FROM {retail.LINK}")
        self.assertEqual(self.count(),1)

    def test_context_schema_missing_causes_rollback_but_preserves_source(self):
        self.first()
        self.db.execute(f"DROP TABLE {retail.LINK}")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            self.original_signal()
        self.assertEqual(self.count(),0)
        self.assertEqual(link.aggregate(self.db)["locallyJoined"],0)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0],1)

    def test_frozen_study_and_private_cvd_unaffected(self):
        self.first()
        out=self.original_signal()
        self.assertEqual(study.protocol_sha256(),study.FROZEN_PROTOCOL_SHA256)
        self.assertEqual(out["cvdCoverage"],"UNKNOWN")
        self.assertFalse(out["actualProspectiveOutcomesMeasured"])


if __name__=="__main__":
    unittest.main()
