#!/usr/bin/env python3
# REMURA v0.8.62 — synthetic only, 14/11/2026 12:52 CET.
import json,tempfile,unittest
from copy import deepcopy
from test_prepare_test_ingest_on_v1 import worker,TEMPLATE,MAIN,TEST,NS
from cvd_transition_bundle_v1 import build_pair,inspect_state,CVD_FLAG,HERE,StopUnsafe,AuditError,ManifestError

def config():
    c=deepcopy(TEMPLATE)
    c["d1_databases"][0]["database_id"]=TEST
    c["ratelimits"][0]["namespace_id"]=NS
    return c
def state(p):
    return inspect_state(p,test_uuid=TEST,namespace=NS)
def cvd_worker():
    p=worker(flag="true")
    p["result"]["bindings"].append({"name":CVD_FLAG,"type":"plain_text","text":"true"})
    return p
class TransitionTests(unittest.TestCase):
    def test_old_and_new_states(self):
        self.assertEqual(state(worker(flag="true")),("TEST_GATEWAY_ON_WITH_HASH_SECRET","LEGACY"))
        self.assertEqual(state(cvd_worker()),("TEST_GATEWAY_ON_WITH_HASH_SECRET","CVD_TRUE"))
    def test_wrong_cvd_flag_and_database_rejected(self):
        for bad in ({"type":"secret_text"},{"text":"yes"}):
            p=cvd_worker();p["result"]["bindings"][-1].update(bad)
            with self.assertRaises(StopUnsafe):
                state(p)
        p=cvd_worker();p["result"]["bindings"][0]["id"]=MAIN
        with self.assertRaises(StopUnsafe):
            state(p)
    def test_unknown_extra_binding_and_flag_duplicate_rejected(self):
        for b in ({"name":"UNKNOWN","type":"plain_text","text":"true"},{"name":CVD_FLAG,"type":"plain_text","text":"true"}):
            p=cvd_worker();p["result"]["bindings"].append(b)
            with self.assertRaises(StopUnsafe):
                state(p)
    def test_safe_bundles_default_off(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=build_pair(config(),tmp)
            for folder,source in ((a,"worker_cvd_candidate.mjs"),(b,"worker.mjs")):
                m=json.loads((folder/"wrangler.json").read_text())
                self.assertEqual(m["vars"]["INGEST_ENABLED"],"false")
                self.assertEqual(m["name"],"remura-tv-webhook-test")
                self.assertEqual(m["d1_databases"][0]["database_id"],TEST)
                self.assertFalse(m["preview_urls"])
                self.assertNotIn("WEBHOOK_TOKEN_SHA256",json.dumps(m))
                self.assertEqual((folder/"worker.mjs").read_bytes(),(HERE/source).read_bytes())
            self.assertEqual(json.loads((a/"wrangler.json").read_text())["vars"][CVD_FLAG],"false")
            self.assertNotIn(CVD_FLAG,json.loads((b/"wrangler.json").read_text())["vars"])
    def test_explicit_synthetic_on_and_rollback_preserves_legacy(self):
        with tempfile.TemporaryDirectory() as tmp:
            a,b=build_pair(config(),tmp,enable_cvd=True)
            self.assertEqual(json.loads((a/"wrangler.json").read_text())["vars"],{"INGEST_ENABLED":"true",CVD_FLAG:"true"})
            self.assertEqual(json.loads((b/"wrangler.json").read_text())["vars"],{"INGEST_ENABLED":"true"})
    def test_unresolved_and_wrong_target_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(AuditError,"unsafe_bundle_inputs"):
                build_pair(TEMPLATE,tmp)
            c=config();c["name"]="remura-tv-ingest-lab"
            with self.assertRaisesRegex(ManifestError,"test_worker_name_mismatch"):
                build_pair(c,tmp)
if __name__=="__main__":
    unittest.main()
