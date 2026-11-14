#!/usr/bin/env python3
# REMURA v0.8.63 — 14/11/2026 CET — synthetic only.
import unittest
from unittest.mock import patch
from test_prepare_test_ingest_on_v1 import ACCOUNT,READ,EDITOR,MAIN,TEST,NS,worker,inventory
import cvd_transition_preflight_v1 as m
from cvd_transition_bundle_v1 import StopUnsafe,CVD_FLAG

class PreflightTests(unittest.TestCase):
    def run_check(self,settings):
        with (patch.object(m,"require_account_id",return_value=ACCOUNT),
              patch.object(m,"require_account_token",return_value=READ),
              patch.object(m,"choose_candidate_namespace",return_value=NS),
              patch.object(m,"api_request",return_value=inventory()) as api,
              patch.object(m,"api_get",return_value=settings) as get):
            result=m.preflight(ACCOUNT,READ,EDITOR)
            api.assert_called_once_with("GET",f"/accounts/{ACCOUNT}/d1/database?page=1&per_page=100",READ)
            get.assert_called_once_with(ACCOUNT,EDITOR,"/settings")
            return result
    def test_expected_legacy_only(self):
        self.assertEqual(self.run_check(worker(flag="true")),"LEGACY_TEST_ON_VERIFIED_NO_MUTATION")
    def test_blocks_off_missing_secret_or_main(self):
        for p in (worker(flag="false"),worker(flag="true",secret=False),worker(flag="true",db=MAIN)):
            with self.assertRaises(StopUnsafe):
                self.run_check(p)
    def test_blocks_already_migrated(self):
        p=worker(flag="true")
        p["result"]["bindings"].append({"name":CVD_FLAG,"type":"plain_text","text":"true"})
        with self.assertRaises(StopUnsafe):
            self.run_check(p)
if __name__=="__main__":
    unittest.main()
