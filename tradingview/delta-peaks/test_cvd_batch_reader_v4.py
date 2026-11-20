#!/usr/bin/env python3
# REMURA v0.8.89 LAB — 16/11/2026 10:29 CET — synthetic only
import io,json,sys,unittest
from pathlib import Path
from unittest.mock import patch
from contextlib import ExitStack
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_test_batch_reader_v4 as b
import cvd_test_fold_reader_v2 as transport
from test_cvd_batch_nonoverlap_preview_v1 import triples,response
from test_cvd_telemetry_preview_v1 import T0,M5
from cvd_oos_protocol_preview_v2 import clock
UID="12345678-1234-1234-1234-123456789abc"
class Tests(unittest.TestCase):
    def call(self,reply,start=T0,end=T0,receipt=True,now=None):
        with ExitStack() as s:
            s.enter_context(patch.object(b,"require_account_id",return_value="account"))
            s.enter_context(patch.object(b,"require_account_token",return_value="token"))
            s.enter_context(patch.object(b,"inspect_verified_inventory",return_value={b.MAIN_DB:"main",b.TEST_DB:UID}))
            api=s.enter_context(patch.object(b,"api_request",return_value={}))
            page=s.enter_context(patch.object(b,"fetch_page",return_value=reply))
            try:return b.read_batch("","",start=start,end=end,now=end+120000 if now is None else now,explicit=True,receipt_only=receipt)
            finally:self.calls=(api.call_count,page.call_count)
    def test_receipt_no_benchmark(self):
        with patch.object(b,"assemble",side_effect=AssertionError("outcomes")):
            r=self.call(response([triples(1)[0][0]],{"rows_read":1,"rows_written":0}))
        self.assertEqual(r["status"],"COMPLETE_REQUESTED_WINDOW")
        self.assertEqual(r["schema"],"remura.tv.cvd.first.receipt.preview.v2")
        self.assertEqual(r["window"],{"start_close_ms":T0,"end_close_ms":T0,"as_of_ms":T0+120000})
        self.assertFalse(r["outcomes_computed"]);self.assertEqual(self.calls,(1,1))
        self.assertNotIn("raw_json",json.dumps(r))
    def test_empty_partial(self):
        r=self.call(response([],{"rows_read":0,"rows_written":0}))
        self.assertEqual(r["status"],"NO_MATCHING_ROWS")
        r=self.call(response([triples(1)[0][0]],{"rows_read":1,"rows_written":0}),end=T0+M5)
        self.assertEqual(r["status"],"PARTIAL_REQUESTED_WINDOW")
    def test_receipt_cap_before_network(self):
        with self.assertRaises(b.AuditError):self.call({},end=T0+12*M5)
        self.assertEqual(self.calls,(0,0))
    def test_unknown_and_over_budget_stop(self):
        for r in (response([]),response([],{"rows_read":20001,"rows_written":0}),response([],{"rows_read":1,"rows_written":1})):
            with self.assertRaises(b.AuditError):self.call(r,end=T0+72*M5,receipt=False)
            self.assertEqual(self.calls,(1,1))
    def test_normal_batch_keeps_blinding(self):
        start=clock("2026-11-16")
        r=self.call(response([],{"rows_read":1,"rows_written":0}),start=start,end=start,receipt=False)
        self.assertEqual(r["outcomes"]["status"],"WITHHELD_REGISTERED_PERIOD")
    def test_full_page_over_old_200k_cap(self):
        rows=[dict(r,raw_json=r["raw_json"]+" "*4000) for r,_,_ in triples(72)]
        raw=json.dumps(response(rows,{"rows_read":72,"rows_written":0})).encode()
        self.assertGreater(len(raw),200000)
        self.assertLess(len(raw),transport.MAX_RESPONSE_BYTES)
        with patch.object(transport,"build_opener") as op:
            op.return_value.open.return_value=io.BytesIO(raw)
            payload=transport.fetch_page("account",UID,"token",T0,T0+71*M5,T0+71*M5+120000)
        r=self.call(payload,end=T0+71*M5,receipt=False)
        self.assertEqual(r["valid_unique_bars"],72)
    def test_transport_oversize_fails(self):
        with patch.object(transport,"MAX_RESPONSE_BYTES",10),patch.object(transport,"build_opener") as op:
            op.return_value.open.return_value=io.BytesIO(b"x"*11)
            with self.assertRaises(transport.AuditError):transport.fetch_page("account",UID,"token",T0,T0,T0+120000)
if __name__=="__main__":unittest.main()
