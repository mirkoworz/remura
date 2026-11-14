#!/usr/bin/env python3
# REMURA v0.8.55 LAB — 14/11/2026 11:44 CET — synthetic only.
import unittest
from datetime import datetime,timezone
from fx_m15_decision_preview_v1 import preview,ALGORITHM
from test_fx_asof_handoff_v1 import good
from test_volume_features_v1 import fixture
from test_telemetry_v1 import T0
from volume_features_v1 import M5

def stamp(t):
    return datetime.fromtimestamp(t/1000,tz=timezone.utc).isoformat().replace("+00:00","Z")

def link():
    return {"history_id":1,"symbol":"EURUSD","cot_report_date":"2026-11-10",
            "price_closed_at_utc":stamp(T0),"observed_at_utc":stamp(T0+6000),
            "linked_at_utc":stamp(T0+7000),"original_ingest_proof_id":1,
            "merged_document_sha256":"a"*64,"cot_source_version_digest":"b"*64,
            "algorithm":ALGORITHM}

def run(rows,b=None,asof=T0+8000):
    return preview(link() if b is None else b,rows,audit_asof_utc=stamp(asof))

class DecisionPreviewTests(unittest.TestCase):
    def test_exact_close_candidate_only(self):
        r=run([good()])
        self.assertTrue(r["tv_candidate"])
        self.assertFalse(r["track_b_connected"])
        self.assertFalse(r["institutional_admissible"])
        self.assertFalse(r["cot_values_verified"])

    def test_no_prior_bar_fallback(self):
        self.assertFalse(run([fixture(T0-M5)])["tv_candidate"])

    def test_no_future_receipt(self):
        r=run([dict(good(),received_at_ms=T0+6500)])
        self.assertFalse(r["tv_candidate"])
        self.assertEqual(r["tv_excluded_counts"]["NOT_KNOWN_AT_DECISION"],1)

    def test_later_link_not_available_before_audit(self):
        with self.assertRaises(ValueError):
            run([good()],asof=T0+6500)

    def test_bad_cohort_and_hash(self):
        for b in (dict(link(),symbol="XAUUSD"),dict(link(),merged_document_sha256="x")):
            with self.assertRaises(ValueError):
                run([good()],b)

    def test_noncausal_time_or_alignment(self):
        for b in (dict(link(),observed_at_utc=stamp(T0-1)),
                  dict(link(),price_closed_at_utc=stamp(T0-M5)),
                  dict(link(),linked_at_utc=stamp(T0+40000))):
            with self.assertRaises(ValueError):
                run([good()],b,asof=T0+50000)

if __name__=="__main__":
    unittest.main()
