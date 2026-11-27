#!/usr/bin/env python3
# REMURA TEST TARGET PREFLIGHT TESTS v0.8.22 — 13/11/2026, ore 15:22 CET
# Dati completamente sintetici, simulazione API GET, mai contatto rete.
import contextlib
import copy
from io import StringIO
import json
from pathlib import Path
import unittest
from unittest.mock import patch

import d1_test_target_preflight_v1 as p
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
TOKEN = "cfat_" + "x" * 48
MAIN_UUID = "00000000-0000-4000-8000-000000000001"
TEST_UUID = "00000000-0000-4000-8000-000000000002"
TEMPLATE = json.loads(p.TEMPLATE.read_text(encoding="utf-8"))


def inventory(rows=None, count=None, page=1):
    default = [
        {"name": "remura-tv-lab", "uuid": MAIN_UUID, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": TEST_UUID, "jurisdiction": "eu"},
    ]
    result = default if rows is None else rows
    return {
        "success": True, "result": result,
        "result_info": {"page": page, "per_page": 100, "count": len(result),
                        "total_count": len(result) if count is None else count},
    }


class TestD1Preflight(unittest.TestCase):
    def test_inventory_distinguishes_main_and_test(self):
        ids = p.inspect_verified_inventory(inventory())
        self.assertEqual(ids["remura-tv-lab"], MAIN_UUID)
        self.assertEqual(ids["remura-tv-lab-test"], TEST_UUID)
        self.assertNotEqual(ids["remura-tv-lab"], ids["remura-tv-lab-test"])

    def test_manifest_intentionally_blocked_by_placeholders(self):
        ids = p.inspect_verified_inventory(inventory())
        self.assertEqual(p.inspect_template(copy.deepcopy(TEMPLATE), ids),
                         "VERIFIED_ISOLATED_BUT_UNRESOLVED")
        self.assertEqual(TEMPLATE["d1_databases"][0]["database_id"],
                         "REPLACE_WITH_D1_TEST_UUID")

    def test_live_data_not_logged_in_output(self):
        calls = []
        def fake_api(method, path, token):
            calls.append((method, path))
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            if path.endswith("?page=1&per_page=100"):
                return inventory()
            raise AssertionError("unexpected endpoint")
        with (patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "require_account_token", return_value=TOKEN),
              patch.object(p, "api_request", side_effect=fake_api),
              patch.dict(p.os.environ, {
                  "REMURA_CF_ACCOUNT_ID": ACCOUNT,
                  "REMURA_CF_D1_READ_TOKEN": TOKEN,
              })):
            out = StringIO()
            with contextlib.redirect_stdout(out):
                status = p.main()
        self.assertEqual(status, 0)
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(m == "GET" and "workers.dev" not in path
                            and "/query" not in path for m, path in calls))
        text = out.getvalue()
        self.assertIn("VERIFIED_TEST_DB_IDENTITY_ONLY", text)
        self.assertIn("WORKER_DEPLOY=NOT_AUTHORIZED", text)
        self.assertNotIn(MAIN_UUID, text)
        self.assertNotIn(TEST_UUID, text)
        self.assertNotIn(TOKEN, text)

    def test_ambiguous_pagination_is_unknown(self):
        for bad in (inventory(count=3), inventory(page=2)):
            with self.assertRaises(AuditError):
                p.inspect_verified_inventory(bad)

    def test_missing_test_db_is_unknown(self):
        rows = inventory()["result"][:1]
        with self.assertRaises(AuditError):
            p.inspect_verified_inventory(inventory(rows))

    def test_jurisdiction_mismatch_fails_closed(self):
        rows = inventory()["result"]
        rows[1]["jurisdiction"] = "us"
        with self.assertRaises(AuditError):
            p.inspect_verified_inventory(inventory(rows))

    def test_duplicate_id_or_name_fails_closed(self):
        for field in ("uuid", "name"):
            rows = inventory()["result"]
            rows[1][field] = rows[0][field]
            with self.subTest(field=field), self.assertRaises(AuditError):
                p.inspect_verified_inventory(inventory(rows))

    def test_reject_wrong_database_target_even_without_network(self):
        cfg = copy.deepcopy(TEMPLATE)
        cfg["d1_databases"][0]["database_name"] = "remura-tv-lab"
        with patch.object(p, "api_request") as api:
            with self.assertRaises(AuditError):
                p.preflight(ACCOUNT, TOKEN, cfg)
            api.assert_not_called()

    def test_reject_partial_resolution(self):
        cfg = copy.deepcopy(TEMPLATE)
        cfg["d1_databases"][0]["database_id"] = TEST_UUID
        with self.assertRaises(AuditError):
            p.inspect_template(cfg, {"remura-tv-lab": MAIN_UUID,
                                     "remura-tv-lab-test": TEST_UUID})

    def test_absent_token_fails_without_network(self):
        with patch.object(p, "api_request") as api:
            with self.assertRaises(AuditError):
                p.preflight(ACCOUNT, "", TEMPLATE)
            api.assert_not_called()

    def test_disallowed_http_post_or_sql_never_issued(self):
        methods = []
        def fake(method, path, token):
            methods.append(method)
            self.assertEqual(method, "GET")
            self.assertNotIn("/query", path)
            return ({"success": True, "result": {"status": "active"}}
                    if path.endswith("/tokens/verify") else inventory())
        with (patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "require_account_token", return_value=TOKEN),
              patch.object(p, "api_request", side_effect=fake)):
            status = p.preflight(ACCOUNT, TOKEN, TEMPLATE)
        self.assertEqual(methods, ["GET", "GET"])
        self.assertEqual(status["WORKER_INGEST"], "NOT_ENABLED")
        self.assertEqual(status["TEST_WORKER_MANIFEST"], "BLOCKED_UNRESOLVED_IDS")

    def test_fail_closed_api_denial_does_not_print_sensitive_context(self):
        with (patch.object(p, "api_request",
                           side_effect=AuditError("cloudflare_http_error_403")),
              patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "require_account_token", return_value=TOKEN),
              patch.dict(p.os.environ, {
                  "REMURA_CF_ACCOUNT_ID": ACCOUNT,
                  "REMURA_CF_D1_READ_TOKEN": TOKEN,
              })):
            buffer = StringIO()
            with contextlib.redirect_stdout(buffer):
                code = p.main()
        self.assertEqual(code, 2)
        self.assertIn("UNKNOWN_FAIL_CLOSED", buffer.getvalue())
        self.assertNotIn(ACCOUNT, buffer.getvalue())
        self.assertNotIn(TOKEN, buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
