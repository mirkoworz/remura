#!/usr/bin/env python3
# REMURA v0.8.70 LAB — 14/11/2026 16:53 CET synthetic only
import json,unittest
from unittest.mock import patch
from test_cvd_telemetry_preview_v1 import fixture,T0,M5
from test_cvd_squalincome_asof_preview_v1 import coherent
from cvd_telemetry_preview_v1 import validate
from cvd_nonoverlap_preview_v1 import compare
from cvd_archive_preview_v1 import assemble
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/'gateway-lab'))
import cvd_test_batch_reader_v1 as batch

def triples(n=44,events=(0,1,14),missing=()):
    out=[]
    for i in range(n):
        if i in missing:
            continue
        t=T0+i*M5
        r=coherent();e=json.loads(r["raw_json"]);p=e["snapshot"];c=e["cvd"]
        p.update(bar_close_ms=t,bar_open_ms=t-M5,sent_clock_ms=t+1000)
        for k,x in p["level_origin_ms"].items():
            if x is not None: p["level_origin_ms"][k]=x+i*M5
        c.update(price_bull=i in events,cvd_bull=i==0 and i in events,
                 pivot_close_ms=t-2*M5 if i in events else None)
        v=validate(e,received_ms=t+5000)
        r.update(bar_close_ms=t,received_at_ms=t+5000,event_key=v["event_key"],raw_json=json.dumps(e))
        out.append((r,e,v))
    return out
def response(rows,meta=None):
    return {"success":True,"result":[{"success":True,"results":rows,"meta":meta}]}
class BenchTests(unittest.TestCase):
    def test_nonoverlap_and_control_once(self):
        r=compare(triples(),as_of_ms=T0+43*M5+120000)
        h=r["horizons"]["60"]
        self.assertEqual(h["counts"]["OVERLAP_EXCLUDED"],1)
        self.assertEqual(h["comparisons"]["CVD"]["matched_pairs"],1)
        self.assertEqual(h["comparisons"]["CVD"]["mean_difference_pips"],0)
        self.assertEqual(h["comparisons"]["CVD"]["hypothetical_net_means_pips"]["2"]["positive"],-2)
        self.assertFalse(r["actual_execution_costs_available"])
    def test_missing_does_not_replace_earliest(self):
        h=compare(triples(missing=(4,)),as_of_ms=T0+43*M5+120000)["horizons"]["60"]
        self.assertEqual(h["counts"]["MISSING_BAR"],1)
        self.assertEqual(h["counts"]["OVERLAP_EXCLUDED"],1)
        self.assertEqual(h["comparisons"]["CVD"]["matched_pairs"],0)
    def test_entry_after_receipt_and_maturity(self):
        h=compare(triples(14),as_of_ms=T0+12*M5+120000)["horizons"]["60"]
        self.assertEqual(h["counts"]["PENDING_MATURITY"],1)
        self.assertIsNone(h["comparisons"]["CVD"]["mean_difference_pips"])
    def test_empty_unknown(self):
        r=compare([],as_of_ms=T0)
        self.assertEqual(r["status"],"NO_OBSERVATIONS")
        self.assertIsNone(r["horizons"]["1440"]["comparisons"]["CVD"]["mean_difference_pips"])
    def test_archive_includes_benchmark(self):
        r=assemble([{"start_ms":T0,"end_ms":T0,"rows":[coherent()]}],as_of_ms=T0+120000)
        self.assertIn("nonoverlap_benchmark",r)
class CollectionTests(unittest.TestCase):
    def test_plan_and_cap(self):
        self.assertEqual(batch.plan(T0,T0+72*M5,T0+72*M5+120000),[(T0,T0+71*M5),(T0+72*M5,T0+72*M5)])
        with self.assertRaises(batch.AuditError):
            batch.plan(T0,T0+576*M5,T0+576*M5+120000)
    def test_mocks_only_test_and_query_metadata(self):
        with (patch.object(batch,"require_account_id",return_value="account"),
              patch.object(batch,"require_account_token",return_value="token"),
              patch.object(batch,"inspect_verified_inventory",return_value={batch.MAIN_DB:"main",batch.TEST_DB:"test"}),
              patch.object(batch,"api_request",side_effect=[{},response([coherent()],{"rows_read":2,"rows_written":0}),response([],{"rows_read":3,"rows_written":0})]) as api):
            r=batch.read_batch("","",start=T0,end=T0+72*M5,now=T0+72*M5+120000,explicit=True)
            self.assertEqual(r["collection"]["query_rows_read"],5)
            self.assertIsNone(r["collection"]["account_quota_utilization"])
            self.assertEqual(api.call_count,3)
            for call in api.call_args_list[1:]:
                self.assertTrue(call.args[1].endswith("/test/query"))
                self.assertTrue(call.args[3]["sql"].startswith("SELECT "))
            self.assertNotIn("raw_json",json.dumps(r))
    def test_explicit_and_sentinel(self):
        with patch.object(batch,"api_request") as api:
            with self.assertRaises(batch.AuditError):
                batch.read_batch("","",start=T0,end=T0,now=T0+120000)
            api.assert_not_called()
        for bad in (response([{}]*101),response([],{"rows_written":1})):
            with self.assertRaises(batch.AuditError):
                batch.unpack(bad)
        self.assertEqual(batch.unpack(response([]))[1],[None,None])
if __name__=="__main__":
    unittest.main()
