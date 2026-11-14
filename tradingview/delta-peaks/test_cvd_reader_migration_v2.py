#!/usr/bin/env python3
# REMURA v0.8.80 LAB — 14/11/2026 18:30 CET — mock only
import unittest,json,sys
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_archive_preview_v2 as archive
import cvd_test_batch_reader_v2 as batch
import cvd_test_fold_reader_v2 as fold
from cvd_oos_protocol_preview_v2 import clock,digest
from cvd_telemetry_preview_v1 import M5
from test_cvd_batch_nonoverlap_preview_v1 import response
S=clock("2026-11-16");E=clock("2026-11-23")
class ReaderV2Tests(unittest.TestCase):
    def test_archive_withholds_partial_period(self):
        with patch.object(archive,"compare") as cmp,patch.object(archive,"summarize") as sm:
            r=archive.assemble([{"start_ms":S,"end_ms":S,"rows":[]}],as_of_ms=S+120000)
            cmp.assert_not_called();sm.assert_not_called()
        self.assertEqual(r["nonoverlap_benchmark"]["status"],"WITHHELD_REGISTERED_PERIOD")
        self.assertEqual(r["outcomes"]["status"],"WITHHELD_REGISTERED_PERIOD")
        self.assertEqual(r["prospective_folds"]["folds"]["DEVELOPMENT"]["status"],"PENDING_FIXED_END")
        self.assertEqual(r["protocol_sha256"],digest())
    def test_old_diagnostic_scope_is_v2(self):
        r=archive.assemble([{"start_ms":S-M5,"end_ms":S-M5,"rows":[]}],as_of_ms=S+120000)
        self.assertEqual(r["nonoverlap_benchmark"]["schema"],"remura.tv.cvd.nonoverlap.preview.v2")
    def test_batch_uses_v2_no_early_outcome(self):
        with patch.object(batch,"require_account_id",return_value="account"),patch.object(batch,"require_account_token",return_value="token"),patch.object(batch,"inspect_verified_inventory",return_value={batch.MAIN_DB:"main",batch.TEST_DB:"test"}),patch.object(batch,"api_request",side_effect=[{},response([],{"rows_read":1,"rows_written":0})]) as api:
            r=batch.read_batch("","",start=S,end=S,now=S+120000,explicit=True)
        self.assertEqual(api.call_count,2)
        self.assertEqual(r["protocol_sha256"],digest())
        self.assertEqual(r["outcomes"]["status"],"WITHHELD_REGISTERED_PERIOD")
        self.assertNotIn("raw_json",json.dumps(r))
    def test_fold_uses_v2_only_after_close(self):
        with patch.object(fold,"require_account_id",return_value="account"),patch.object(fold,"require_account_token",return_value="token"),patch.object(fold,"inspect_verified_inventory",return_value={fold.MAIN_DB:"main",fold.TEST_DB:"test"}),patch.object(fold,"api_request",return_value={}) as api,patch.object(fold,"fetch_page",return_value=response([],{"rows_read":2,"rows_written":0})) as page:
            with self.assertRaises(fold.AuditError):fold.read_fold("","",fold="DEVELOPMENT",now=E-1,explicit=True)
            api.assert_not_called();page.assert_not_called()
            r=fold.read_fold("","",fold="DEVELOPMENT",now=E,explicit=True)
            self.assertEqual(api.call_count,1);self.assertEqual(page.call_count,28)
            self.assertTrue(all(c.args[1]=="test" and c.args[-1]==E-1 for c in page.call_args_list))
        self.assertEqual(r["schema"],"remura.tv.cvd.fold.collection.preview.v2")
        self.assertEqual(r["protocol_sha256"],digest())
        self.assertEqual(r["fold_result"]["status"],"NO_OBSERVATIONS")
        self.assertEqual(r["collection"]["query_rows_read"],56)
        self.assertFalse(r["scientific_admission"])
    def test_fold_fails_on_usage_or_receipt(self):
        for reply in (response([],{"rows_read":100001,"rows_written":0}),response([]),response([{"received_at_ms":E}],{"rows_read":1,"rows_written":0})):
            with patch.object(fold,"require_account_id",return_value="account"),patch.object(fold,"require_account_token",return_value="token"),patch.object(fold,"inspect_verified_inventory",return_value={fold.MAIN_DB:"main",fold.TEST_DB:"test"}),patch.object(fold,"api_request",return_value={}),patch.object(fold,"fetch_page",return_value=reply) as page:
                with self.assertRaises(fold.AuditError):fold.read_fold("","",fold="DEVELOPMENT",now=E,explicit=True)
                self.assertEqual(page.call_count,1)
if __name__=="__main__":
    unittest.main()
