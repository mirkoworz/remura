#!/usr/bin/env python3
# REMURA v0.8.37 — 14/11/2026 ore 01:56 CET — mocked safety tests only.
import contextlib
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_test_ingest_on_v1 as a
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
READ = "cfat_" + "r" * 48
EDITOR = "cfat_" + "e" * 48
MAIN = "00000000-0000-4000-8000-000000000001"
TEST = "00000000-0000-4000-8000-000000000002"
NS = "812345678901"
TEMPLATE = json.loads(a.EXAMPLE.read_text(encoding="utf-8"))


def inventory():
    return {"success": True, "result": [
        {"name": "remura-tv-lab", "uuid": MAIN, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": TEST, "jurisdiction": "eu"},
    ], "result_info": {"page": 1, "per_page": 100, "count": 2,
                       "total_count": 2}}


def worker(flag="false", secret=True, db=TEST, name="remura-tv-webhook-test"):
    bindings = [
        {"name": "TELEMETRY_DB", "type": "d1", "id": db},
        {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
         "namespace_id": NS, "simple": {"limit": 20, "period": 60}},
        {"name": "INGEST_ENABLED", "type": "plain_text", "text": flag},
    ]
    if secret:
        bindings.append({"name": "WEBHOOK_TOKEN_SHA256", "type": "secret_text"})
    return {"success": True, "result": {"name": name, "bindings": bindings}}


class IngestOnSafetyTests(unittest.TestCase):
    def prepare(self, settings=None, d1=None):
        observed = []
        def api(method, path, token):
            self.assertEqual(method, "GET")
            self.assertEqual(token, READ)
            self.assertIn("/d1/database?", path)
            self.assertNotIn("/query", path)
            observed.append("D1")
            return inventory() if d1 is None else d1
        def get(account, token, suffix):
            self.assertEqual((account,token,suffix),(ACCOUNT,EDITOR,"/settings"))
            observed.append("TEST")
            return worker() if settings is None else settings
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=READ),
              patch.object(a, "choose_candidate_namespace", return_value=NS),
              patch.object(a, "api_request", side_effect=api),
              patch.object(a, "api_get", side_effect=get)):
            cfg = a.build_on_candidate(ACCOUNT,READ,EDITOR,TEMPLATE)
        return cfg, observed

    def test_prepared_on_only_if_secret_present_and_receiver_off(self):
        template_before = deepcopy(TEMPLATE)
        cfg, calls = self.prepare()
        self.assertEqual(calls, ["D1", "TEST"])
        self.assertEqual(cfg["vars"], {"INGEST_ENABLED":"true"})
        self.assertEqual(cfg["name"], "remura-tv-webhook-test")
        self.assertEqual(cfg["d1_databases"][0]["database_id"], TEST)
        self.assertNotEqual(cfg["d1_databases"][0]["database_id"],MAIN)
        self.assertFalse(cfg["preview_urls"])
        self.assertEqual(cfg["ratelimits"][0]["simple"],{"limit":20,"period":60})
        self.assertEqual(TEMPLATE,template_before)
        self.assertNotIn("WEBHOOK_TOKEN_SHA256",json.dumps(cfg))

    def test_refuses_if_worker_already_on_or_missing_secret(self):
        for settings in (worker(flag="true",secret=True),
                         worker(flag="false",secret=False),
                         worker(flag="true",secret=False)):
            with self.subTest(settings=settings["result"]["bindings"][2]), self.assertRaises(AuditError):
                self.prepare(settings=settings)

    def test_refuses_main_db_and_other_worker(self):
        for settings in (worker(db=MAIN),
                         worker(name="remura-tv-ingest-lab")):
            with self.assertRaises(AuditError):
                self.prepare(settings=settings)

    def test_refuses_unexpected_bindings_and_broken_rate_limit(self):
        settings=worker()
        settings["result"]["bindings"].append({"name":"SUSPECT","type":"secret_text"})
        with self.assertRaises(AuditError):
            self.prepare(settings=settings)
        settings=worker()
        settings["result"]["bindings"][1]["simple"]["limit"]=999
        with self.assertRaises(AuditError):
            self.prepare(settings=settings)

    def test_refuses_non_eu_or_duplicated_d1(self):
        for variant in ("non_eu","duplicate"):
            d1=inventory()
            if variant=="non_eu": d1["result"][1]["jurisdiction"]="us"
            else: d1["result"][1]["uuid"]=MAIN
            with self.subTest(variant=variant), self.assertRaises(AuditError):
                self.prepare(d1=d1)

    def test_rejects_editor_missing_before_any_live_get(self):
        with (patch.object(a,"require_account_id",return_value=ACCOUNT),
              patch.object(a,"api_request") as api,
              patch.object(a,"api_get") as get):
            with self.assertRaises(AuditError):
                a.build_on_candidate(ACCOUNT,READ,"",TEMPLATE)
        api.assert_not_called()
        get.assert_not_called()

    def test_manifest_change_must_be_only_off_to_on(self):
        cfg,_=self.prepare()
        runtime=a.validate_on_candidate(cfg)
        self.assertNotIn("$comment",runtime)
        self.assertEqual(runtime["vars"],{"INGEST_ENABLED":"true"})
        self.assertEqual(runtime["main"],"worker.mjs")
        self.assertEqual(runtime["name"],"remura-tv-webhook-test")
        for mode in ("worker","db","preview","secret","flag","routes","limiter"):
            change=deepcopy(cfg)
            if mode=="worker": change["name"]="remura-tv-ingest-lab"
            if mode=="db": change["d1_databases"][0]["database_name"]="remura-tv-lab"
            if mode=="preview": change["preview_urls"]=True
            if mode=="secret": change["vars"]["WEBHOOK_TOKEN_SHA256"]="fake_hash"
            if mode=="flag": change["vars"]={"INGEST_ENABLED":"false"}
            if mode=="routes": change["routes"]=["example.com/*"]
            if mode=="limiter": change["ratelimits"][0]["simple"]["limit"]=5000
            with self.subTest(mode=mode),self.assertRaises((AuditError,ValueError)):
                a.validate_on_candidate(change)

    def test_bundle_ephemeral_private_and_no_hash_in_code_config(self):
        cfg,_=self.prepare()
        with tempfile.TemporaryDirectory() as tmp:
            folder=a.make_private_on_bundle(cfg,tmp)
            self.assertEqual({x.name for x in folder.iterdir()},{"wrangler.json","worker.mjs"})
            runtime=json.loads((folder/"wrangler.json").read_text())
            self.assertNotIn("$comment",runtime)
            self.assertEqual(runtime["vars"],{"INGEST_ENABLED":"true"})
            self.assertNotIn("WEBHOOK_TOKEN_SHA256",json.dumps(runtime))
            self.assertEqual((folder/"worker.mjs").read_bytes(),
                             a.create_ephemeral_bundle.__globals__["GATEWAY_SOURCE"].read_bytes())
            self.assertEqual(os.stat(folder/"wrangler.json").st_mode & 0o777,0o600)
            self.assertEqual(os.stat(folder/"worker.mjs").st_mode & 0o777,0o600)

    def test_does_not_write_when_main_not_running_under_github_actions(self):
        with (patch.dict(os.environ,{"GITHUB_ENV":"","RUNNER_TEMP":""}),
              patch.object(a,"api_request") as api,
              contextlib.redirect_stdout(StringIO()) as out):
            self.assertEqual(a.main(),2)
        api.assert_not_called()
        self.assertIn("BLOCKED_FAIL_CLOSED",out.getvalue())

    def test_source_never_modifies_cloudflare_or_database(self):
        src=Path(a.__file__).read_text()
        self.assertNotIn("wrangler deploy",src)
        self.assertNotIn("wrangler secret put",src)
        self.assertNotIn("DELETE FROM",src)
        self.assertNotIn("INSERT INTO",src)
        self.assertNotIn("/workers/scripts/remura-tv-ingest-lab",src)


if __name__=="__main__":
    unittest.main()
