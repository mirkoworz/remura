#!/usr/bin/env python3
# REMURA v0.8.31 — 13/11/2026, ore 21:09 CET — mock API only
import contextlib
from copy import deepcopy
from io import StringIO
import json
import unittest
from unittest.mock import patch

import gateway_off_candidate_v1 as a
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
MAIN_UUID = "00000000-0000-4000-8000-000000000001"
TEST_UUID = "00000000-0000-4000-8000-000000000002"
TOKEN = "cfat_" + "q" * 48
TEMPLATE = json.loads(a.EXAMPLE.read_text(encoding="utf-8"))


def inventory():
    return {"success": True, "result": [
        {"name": a.MAIN_DB, "uuid": MAIN_UUID, "jurisdiction": "eu"},
        {"name": a.TEST_DB, "uuid": TEST_UUID, "jurisdiction": "eu"},
    ], "result_info": {
        "page": 1, "per_page": 100, "count": 2, "total_count": 2,
    }}


class TestOffCandidate(unittest.TestCase):
    def test_candidate_is_strict_test_only_off_and_preview_disabled(self):
        cfg = a.make_candidate(TEMPLATE, {a.MAIN_DB: MAIN_UUID,
                                          a.TEST_DB: TEST_UUID}, ACCOUNT)
        self.assertEqual(cfg["name"], "remura-tv-webhook-test")
        self.assertEqual(cfg["d1_databases"][0]["database_name"], a.TEST_DB)
        self.assertEqual(cfg["d1_databases"][0]["database_id"], TEST_UUID)
        self.assertEqual(cfg["vars"], {"INGEST_ENABLED": "false"})
        self.assertIs(cfg["preview_urls"], False)
        self.assertEqual(cfg["ratelimits"][0]["simple"], {"limit": 20, "period": 60})
        self.assertEqual(len(cfg["ratelimits"][0]["namespace_id"]), 12)
        self.assertNotIn("WEBHOOK_TOKEN_SHA256", json.dumps(cfg))
        self.assertNotIn("routes", cfg)
        self.assertNotIn("route", cfg)

    def test_template_remains_unresolved_and_untouched(self):
        snapshot = deepcopy(TEMPLATE)
        a.make_candidate(TEMPLATE, {a.MAIN_DB: MAIN_UUID, a.TEST_DB: TEST_UUID}, ACCOUNT)
        self.assertEqual(TEMPLATE, snapshot)
        self.assertEqual(TEMPLATE["d1_databases"][0]["database_id"],
                         "REPLACE_WITH_D1_TEST_UUID")

    def test_same_namespace_for_same_account_but_not_synthetic(self):
        ns = a.choose_candidate_namespace(ACCOUNT)
        self.assertEqual(ns, a.choose_candidate_namespace(ACCOUNT))
        self.assertNotEqual(ns, "987654321")
        self.assertNotEqual(ns, a.choose_candidate_namespace("b" * 32))
        self.assertTrue(ns.isdigit())
        self.assertNotEqual(ns[0], "0")

    def test_main_db_alias_is_rejected(self):
        with self.assertRaises(AuditError):
            a.make_candidate(TEMPLATE, {a.MAIN_DB: MAIN_UUID,
                                        a.TEST_DB: MAIN_UUID}, ACCOUNT)

    def test_missing_database_target_is_rejected(self):
        with self.assertRaises(AuditError):
            a.make_candidate(TEMPLATE, {a.MAIN_DB: MAIN_UUID}, ACCOUNT)

    def test_ingest_on_or_untrusted_worker_rejected_before_api(self):
        for change in ("ingest", "worker", "preview", "db", "limiter", "secret"):
            t = deepcopy(TEMPLATE)
            if change == "ingest": t["vars"]["INGEST_ENABLED"] = "true"
            if change == "worker": t["name"] = "remura-tv-ingest-lab"
            if change == "preview": t["preview_urls"] = True
            if change == "db": t["d1_databases"][0]["database_name"] = a.MAIN_DB
            if change == "limiter": t["ratelimits"] = []
            if change == "secret": t["vars"]["WEBHOOK_TOKEN_SHA256"] = "sensitive"
            with self.subTest(change=change), self.assertRaises(AuditError):
                a.make_candidate(t, {a.MAIN_DB: MAIN_UUID,
                                     a.TEST_DB: TEST_UUID}, ACCOUNT)

    def test_only_two_get_calls_no_deploy_or_sql(self):
        paths = []
        def fake(method, path, token):
            paths.append((method, path))
            self.assertEqual(method, "GET")
            self.assertNotIn("/workers/", path)
            self.assertNotIn("/query", path)
            return ({"success": True, "result": {"status": "active"}}
                    if path.endswith("/tokens/verify") else inventory())
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=TOKEN),
              patch.object(a, "api_request", side_effect=fake)):
            result = a.audit(ACCOUNT, TOKEN, TEMPLATE)
        self.assertEqual(len(paths), 2)
        self.assertEqual(result["DATA_WRITES"], "NONE")
        self.assertEqual(result["DEPLOY"], "NOT_AUTHORIZED")
        self.assertEqual(result["WEBHOOK_SECRET"], "NOT_ATTACHED")

    def test_incomplete_inventory_fail_closed_no_success(self):
        data = inventory()
        data["result"][1]["jurisdiction"] = "us"
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=TOKEN),
              patch.object(a, "api_request", side_effect=lambda m, p, t:
                  {"success": True, "result": {"status": "active"}}
                  if p.endswith("/tokens/verify") else data)):
            with self.assertRaises(AuditError):
                a.audit(ACCOUNT, TOKEN, TEMPLATE)

    def test_no_id_or_token_printed(self):
        def api(method, path, token):
            return ({"success": True, "result": {"status": "active"}}
                    if path.endswith("/tokens/verify") else inventory())
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=TOKEN),
              patch.object(a, "api_request", side_effect=api),
              patch.dict(a.os.environ, {
                  "REMURA_CF_ACCOUNT_ID": ACCOUNT,
                  "REMURA_CF_D1_READ_TOKEN": TOKEN
              })):
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(a.main(), 0)
        self.assertIn("VERIFIED_IN_MEMORY_ONLY", buf.getvalue())
        self.assertNotIn(ACCOUNT, buf.getvalue())
        self.assertNotIn(TOKEN, buf.getvalue())
        self.assertNotIn(TEST_UUID, buf.getvalue())
        self.assertNotIn(MAIN_UUID, buf.getvalue())

    def test_api_failure_hidden_without_leak(self):
        with (patch.object(a, "require_account_id", return_value=ACCOUNT),
              patch.object(a, "require_account_token", return_value=TOKEN),
              patch.object(a, "api_request",
                           side_effect=AuditError("secret-"+TOKEN)),
              patch.dict(a.os.environ, {
                  "REMURA_CF_ACCOUNT_ID": ACCOUNT,
                  "REMURA_CF_D1_READ_TOKEN": TOKEN
              })):
            buf = StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(a.main(), 2)
        self.assertIn("BLOCKED_FAIL_CLOSED", buf.getvalue())
        self.assertNotIn(TOKEN, buf.getvalue())


if __name__ == "__main__":
    unittest.main()
