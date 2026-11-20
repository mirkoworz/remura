#!/usr/bin/env python3
# REMURA v0.8.72 LAB — 14/11/2026 16:59 CET — synthetic only.
import unittest,json
from unittest.mock import patch
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_test_fold_reader_v1 as m
from cvd_oos_protocol_preview_v1 import clock
from test_cvd_batch_nonoverlap_preview_v1 import response
S=clock("2026-11-16"); E=clock("2026-11-23")
class FoldReaderTests(unittest.TestCase):
    def test_exact_plan(self):
        end,pages=m.plan("DEVELOPMENT",E)
        self.assertEqual(end,E);self.assertEqual(len(pages),28)
        self.assertEqual(pages[0][0],S);self.assertEqual(pages[-1][1],E-m.M5)
        self.assertEqual(sum((b-a)//m.M5+1 for a,b in pages),2016)
        self.assertTrue(all(a==prev+m.M5 for (_,prev),(a,_) in zip(pages,pages[1:])))
    def test_no_early_or_arbitrary_window(self):
        for name,now in (("DEVELOPMENT",E-1),("OTHER",E),("HOLDOUT_1",E)):
            with self.assertRaises(m.AuditError):m.plan(name,now)
    def run_mock(self,reply,now=E):
        with (patch.object(m,"require_account_id",return_value="account"),
              patch.object(m,"require_account_token",return_value="token"),
              patch.object(m,"inspect_verified_inventory",return_value={m.MAIN_DB:"main",m.TEST_DB:"test"}),
              patch.object(m,"api_request",return_value={}) as api,
              patch.object(m,"fetch_page",return_value=reply) as page):
            r=m.read_fold("","",fold="DEVELOPMENT",now=now,explicit=True)
            self.assertEqual(api.call_count,1);self.assertEqual(page.call_count,28)
            self.assertTrue(all(c.args[1]=="test" and c.args[-1]==E-1 for c in page.call_args_list))
            return r
    def test_full_empty_not_edge(self):
        r=self.run_mock(response([],{"rows_read":2,"rows_written":0}),E+1000000)
        self.assertEqual(r["fold_result"]["status"],"NO_OBSERVATIONS")
        self.assertEqual(r["coverage"]["missing_requested_slots"],2016)
        self.assertEqual(r["collection"]["query_rows_read"],56)
        self.assertNotIn("raw_json",json.dumps(r));self.assertFalse(r["scientific_admission"])
    def test_budget_and_unknown_and_future_fail(self):
        for reply in (response([],{"rows_read":100001,"rows_written":0}),response([]),
                      response([{"received_at_ms":E}],{"rows_read":1,"rows_written":0})):
            with self.assertRaises(m.AuditError):self.run_mock(reply)
    def test_no_explicit_no_network(self):
        with patch.object(m,"api_request") as api:
            with self.assertRaises(m.AuditError):
                m.read_fold("","",fold="DEVELOPMENT",now=E)
            api.assert_not_called()
    def test_http_cap_no_redirect(self):
        with self.assertRaises(m.AuditError):
            m.fetch_page("account","wrong","token",S,S,E-1)
        with patch.object(m,"build_opener") as op:
            stream=op.return_value.open.return_value.__enter__.return_value
            stream.read.return_value=b"x"*(m.MAX_RESPONSE_BYTES+1)
            with self.assertRaises(m.AuditError):
                m.fetch_page("account","a"*36,"token",S,S,E-1)
            self.assertIsInstance(op.call_args.args[0],m.NoRedirect)
            stream.read.assert_called_once_with(m.MAX_RESPONSE_BYTES+1)
if __name__=="__main__":
    unittest.main()
