#!/usr/bin/env python3
# REMURA v0.8.57 LAB — 14/11/2026 11:47 CET; mocked inputs.
import sqlite3,sys,types,unittest
from unittest.mock import patch
from aux_source_coverage_preview_v1 import coverage,SCHEMA

class AuxiliaryTests(unittest.TestCase):
    def setUp(self):
        self.main,self.private=sqlite3.connect(":memory:"),sqlite3.connect(":memory:")
        for db in (self.main,self.private):
            db.execute("PRAGMA query_only=ON")
    def tearDown(self):
        self.main.close()
        self.private.close()
    def mock(self,report):
        p=types.ModuleType("scripts")
        p.shark_cvd_cot_price_triage=types.SimpleNamespace(audit=lambda *a,**k:report)
        with patch.dict(sys.modules,{"scripts":p}):
            return coverage(self.main,self.private,as_of_utc="2026-11-14T10:47:00Z",days=1,secret="mock")
    def test_missing_unknown(self):
        r=self.mock({"schema":SCHEMA,"status":"PRIVATE_CVD_LEDGER_UNAVAILABLE","validLocalCotPricePairs":5})
        self.assertIsNone(r["minimumSignalsWithVerifiedCVD"])
        self.assertFalse(r["missing_is_negative"])
    def test_aggregate_not_tv_pair(self):
        r=self.mock({"schema":SCHEMA,"status":"AUDITED","validLocalCotPricePairs":2,"minimumSignalsWithVerifiedCVD":1})
        self.assertEqual(r["minimumSignalsWithVerifiedCVD"],1)
        self.assertFalse(r["same_tv_decision_proven"])
    def test_denominator_guard(self):
        with self.assertRaises(ValueError):
            self.mock({"schema":SCHEMA,"status":"AUDITED","validLocalCotPricePairs":2,"minimumSignalsWithVerifiedCVD":3})
    def test_read_only_guard(self):
        self.private.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):
            self.mock({})
if __name__=="__main__":
    unittest.main()
