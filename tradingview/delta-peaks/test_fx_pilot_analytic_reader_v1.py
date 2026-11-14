#!/usr/bin/env python3
# REMURA v0.8.52 LAB — 14/11/2026 11:00 CET — synthetic/mock only.
import unittest
from pathlib import Path
import sys
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import fx_pilot_analytic_reader_v1 as m
from test_volume_features_v1 import fixture, changed
S=m.BTC_END+m.M5
E=S+2*m.M5
N=E+120000

def envelope(rows):
    return {"success":True,"result":[{"success":True,"results":rows}]}

def fx(t=S):
    def cfg(p):
        p["quality"].update(lower_tf="1",daily_anchor="HL2")
    return changed(fixture(t),cfg)

def report(rows):
    return m.aggregate(envelope(rows),S,E,N)

class FXReaderTests(unittest.TestCase):
    def test_complete_requested_window(self):
        r=report([fx(S),fx(S+m.M5),fx(E)])
        self.assertEqual(r["status"],"COMPLETE_REQUESTED_WINDOW")
        self.assertEqual(r["v1_config_matching_bars"],3)
        self.assertEqual(r["timely_bars"],3)
        self.assertFalse(r["scientific_admission"])
        self.assertFalse(r["effective_alert_inputs_attested"])

    def test_missing_not_market_outage(self):
        r=report([fx(S+m.M5)])
        self.assertEqual(r["unobserved_requested_slots"],2)
        self.assertEqual(r["status"],"INCOMPLETE_REQUESTED_WINDOW")
        self.assertEqual(r["coverage_basis"],"REQUESTED_SLOTS_NOT_MARKET_CALENDAR")

    def test_btc_and_outside_rejected(self):
        for r in (fixture(S,btc=True),fx(S-m.M5),dict(fx(),received_at_ms=N+1)):
            with self.assertRaises(m.AuditError):
                report([r])

    def test_config_mismatch(self):
        r=report([changed(fx(),lambda p:p["quality"].update(daily_anchor="POC FOOTPRINT"))])
        self.assertEqual(r["status"],"CONFIG_METADATA_MISMATCH")
        self.assertEqual(r["v1_config_difference_counts"],{"daily_anchor":1})

    def test_bad_and_conflict(self):
        self.assertEqual(report([dict(fx(),event_key="bad")])["status"],"INVALID_OR_CONFLICTING_ROWS")
        self.assertEqual(report([fx(),dict(fx(),received_at_ms=S+4000)])["quarantined_bars"],1)

    def test_empty_and_sentinel(self):
        self.assertEqual(report([])["status"],"NO_MATCHING_ROWS")
        with self.assertRaises(m.AuditError):
            report([fx()]*(m.LIMIT+1))

    def test_window_guard(self):
        for a,b,n in ((m.BTC_END-m.M5,E,N),(S,E,E+119999),(S,S+72*m.M5,S+73*m.M5),(S+1,E,N)):
            with self.assertRaises(m.AuditError):
                m.check_window(a,b,n)
        self.assertEqual(m.utc_ms("2026-11-16T00:05Z"),S)
        for s in ("2026-11-16T00:05", "2026-11-16T01:05+01:00"):
            with self.assertRaises(m.AuditError):
                m.utc_ms(s)

    def test_only_explicit_verified_test_query(self):
        with patch.object(m,"api_request") as api:
            with self.assertRaises(m.AuditError):
                m.read_live("","",start=S,end=E,now_ms=N)
            api.assert_not_called()
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="mock"),
              patch.object(m,"inspect_verified_inventory",return_value={m.TEST_DB:"test",m.MAIN_DB:"main"}),
              patch.object(m,"api_request",side_effect=[{},envelope([])]) as api):
            m.read_live("","",start=S,end=E,now_ms=N,explicit=True)
            self.assertEqual(api.call_count,2)
            method,path,token,body=api.call_args.args
            self.assertTrue(path.endswith("/test/query"))
            self.assertEqual(body["params"],[m.SYMBOL,"5",S,E,N,m.LIMIT+1])
            self.assertTrue(body["sql"].startswith("SELECT "))

if __name__=="__main__":
    unittest.main()
