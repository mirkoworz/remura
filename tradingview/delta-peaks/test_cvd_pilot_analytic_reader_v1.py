#!/usr/bin/env python3
# REMURA v0.8.61 LAB — 14/11/2026 CET
import json,sys,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_pilot_analytic_reader_v1 as m
from test_cvd_telemetry_preview_v1 import fixture,T0,VERSION,SYMBOL
from cvd_telemetry_preview_v1 import validate

def row():
    e=fixture();v=validate(e,received_ms=T0+5000)
    return {"event_key":v["event_key"],"received_at_ms":T0+5000,"bar_close_ms":T0,
        "symbol":SYMBOL,"timeframe":"5","version":VERSION,"event_type":e["snapshot"]["event_type"],
        "is_timely":0,"raw_json":json.dumps(e)}
def envelope(rows):
    return {"success":True,"result":[{"success":True,"results":rows}]}
def run(rows):
    return m.aggregate(envelope(rows),T0,T0,T0+120000)

class ReaderTests(unittest.TestCase):
    def test_complete(self):
        r=run([row()])
        self.assertEqual(r["status"],"COMPLETE_REQUESTED_WINDOW")
        self.assertEqual(r["event_counts"]["cvd_bull"],1)
        self.assertEqual(r["delta_exact_matches"],1)
        self.assertFalse(r["scientific_admission"])
        self.assertFalse(r["raw_json_logged"])
    def test_cvd_window_uses_actual_deployment_not_btc_expiry(self):
        start=m.utc_ms("2026-11-14T12:40Z")
        m.check_window(start,start,start+120000)
        sunday=m.utc_ms("2026-11-15T22:05Z")
        m.check_window(sunday,sunday,sunday+120000)
        with self.assertRaises(m.AuditError):
            m.check_window(start-m.M5,start,start+120000)
        with self.assertRaises(m.AuditError):
            m.check_window(start,start,start+119999)
    def test_empty(self):
        self.assertEqual(run([])["status"],"NO_MATCHING_ROWS")
    def test_invalid(self):
        self.assertEqual(run([dict(row(),is_timely=1)])["status"],"INVALID_OR_CONFLICTING_ROWS")
        with self.assertRaises(m.AuditError):
            run([dict(row(),symbol="FXCM:EURUSD")])
    def test_conflict_and_duplicate(self):
        self.assertEqual(run([row(),row()])["row_counts"]["duplicate_rows"],1)
        self.assertEqual(run([row(),dict(row(),received_at_ms=T0+6000)])["row_counts"]["conflicted_bars"],1)
    def test_explicit_and_test_db_only(self):
        with patch.object(m,"api_request") as req:
            with self.assertRaises(m.AuditError):
                m.read_live("","",start=T0,end=T0,now=T0+120000)
            req.assert_not_called()
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="mock"),
              patch.object(m,"inspect_verified_inventory",return_value={m.MAIN_DB:"main",m.TEST_DB:"test"}),
              patch.object(m,"api_request",side_effect=[{},envelope([])]) as req):
            m.read_live("","",start=T0,end=T0,now=T0+120000,explicit=True)
            self.assertEqual(req.call_count,2)
            self.assertTrue(req.call_args.args[1].endswith("/test/query"))
            self.assertEqual(req.call_args.args[3]["params"],[SYMBOL,"5",VERSION,T0,T0,T0+120000,m.LIMIT+1])
if __name__=="__main__":
    unittest.main()
