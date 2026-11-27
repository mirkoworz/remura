#!/usr/bin/env python3
# REMURA v0.8.32 TEST — 13/11/2026 ore 21:07 CET — mocked only
import contextlib
from io import StringIO
import unittest
from unittest.mock import patch
import worker_rollback_preflight_v1 as w
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
TOKEN = "cfat_" + "x" * 48
EDITOR = "cfat_" + "b" * 48
MAIN_ID = "00000000-0000-4000-8000-000000000001"
TEST_ID = "00000000-0000-4000-8000-000000000002"


def inventory():
    return {"success": True, "result": [
        {"name": "remura-tv-lab", "uuid": MAIN_ID, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": TEST_ID, "jurisdiction": "eu"},
    ], "result_info": {"page": 1, "per_page": 100, "count": 2, "total_count": 2}}


def settings(bindings=None):
    return {"success": True, "result": {
        "name": "remura-tv-webhook-test",
        "bindings": [] if bindings is None else bindings}}


class RollbackPreflightTests(unittest.TestCase):
    def context(self, settings_response):
        calls = []
        def d1(method, path, token):
            self.assertEqual(method, "GET")
            self.assertNotIn("/query", path)
            self.assertNotIn("/workers/", path)
            self.assertEqual(token, TOKEN)
            calls.append(("D1_INVENTORY", path))
            return inventory()
        def worker(account, token, suffix):
            self.assertEqual(account, ACCOUNT)
            self.assertEqual(token, EDITOR)
            self.assertEqual(suffix, "/settings")
            calls.append(("TEST_WORKER_SETTINGS", suffix))
            return settings_response
        return calls, d1, worker

    def test_empty_bootstrap_safe(self):
        calls, d1, worker = self.context(settings())
        with (patch.object(w, "require_account_id", return_value=ACCOUNT),
              patch.object(w, "require_account_token", return_value=TOKEN),
              patch.object(w, "api_request", side_effect=d1),
              patch.object(w, "api_get", side_effect=worker)):
            self.assertEqual(w.preflight(ACCOUNT, TOKEN, EDITOR),
                             "BOOTSTRAP_ALREADY_EMPTY")
        self.assertEqual(len(calls), 2)

    def test_strict_off_test_gateway_safe(self):
        ns = w.choose_candidate_namespace(ACCOUNT)
        b = [
            {"name": "TELEMETRY_DB", "type": "d1", "id": TEST_ID},
            {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
             "namespace_id": ns, "simple": {"limit": 20, "period": 60}},
            {"name": "INGEST_ENABLED", "type": "plain_text", "text": "false"},
        ]
        calls, d1, worker = self.context(settings(b))
        with (patch.object(w, "require_account_id", return_value=ACCOUNT),
              patch.object(w, "require_account_token", return_value=TOKEN),
              patch.object(w, "api_request", side_effect=d1),
              patch.object(w, "api_get", side_effect=worker)):
            self.assertEqual(w.preflight(ACCOUNT, TOKEN, EDITOR),
                             "TEST_GATEWAY_OFF_STRICT_NO_SECRET")
        self.assertEqual(len(calls), 2)

    def test_main_db_rejected(self):
        b = [{"name": "TELEMETRY_DB", "type": "d1", "id": MAIN_ID},
             {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
              "namespace_id": w.choose_candidate_namespace(ACCOUNT),
              "simple": {"limit": 20, "period": 60}},
             {"name": "INGEST_ENABLED", "type": "plain_text", "text": "false"}]
        _, d1, worker = self.context(settings(b))
        with (patch.object(w, "require_account_id", return_value=ACCOUNT),
              patch.object(w, "require_account_token", return_value=TOKEN),
              patch.object(w, "api_request", side_effect=d1),
              patch.object(w, "api_get", side_effect=worker)):
            with self.assertRaisesRegex(AuditError, "unsafe"):
                w.preflight(ACCOUNT, TOKEN, EDITOR)

    def test_missing_editor_token_stops_before_any_http(self):
        with (patch.object(w, "require_account_id", return_value=ACCOUNT),
              patch.object(w, "require_account_token", return_value=TOKEN),
              patch.object(w, "api_request") as d1,
              patch.object(w, "api_get") as worker):
            with self.assertRaises(AuditError):
                w.preflight(ACCOUNT, TOKEN, "")
        d1.assert_not_called()
        worker.assert_not_called()

    def test_api_error_does_not_echo_secret(self):
        with (patch.object(w, "preflight",
                           side_effect=AuditError("sensitive="+EDITOR)),
              contextlib.redirect_stdout(StringIO()) as output):
            code = w.main()
            captured = output.getvalue()
        self.assertEqual(code, 2)
        self.assertNotIn(EDITOR, captured)
        self.assertIn("BLOCKED_FAIL_CLOSED", captured)

    def test_script_has_no_network_to_production_worker(self):
        source = open(w.__file__, encoding="utf-8").read()
        self.assertNotIn("/workers/scripts/remura-tv-ingest-lab", source)
        self.assertNotIn("DELETE FROM", source)
        self.assertNotIn("wrangler deploy", source)


if __name__ == "__main__":
    unittest.main()
