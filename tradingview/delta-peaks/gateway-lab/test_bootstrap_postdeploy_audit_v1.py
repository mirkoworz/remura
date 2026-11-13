#!/usr/bin/env python3
# REMURA v0.8.31 — 13/11/2026 ore 21:00 CET — TEST OFFLINE ONLY
import contextlib
from io import StringIO
import json
import unittest
from unittest.mock import patch, MagicMock
import bootstrap_postdeploy_audit_v1 as a


def version(bindings=None):
    return {"success": True, "result": {
        "id": a.EXPECTED_VERSION,
        "resources": {"bindings": [] if bindings is None else bindings},
    }}


def settings(bindings=None):
    return {"success": True, "result": {
        "bindings": [] if bindings is None else bindings
    }}


class ReadOnlyAfterDeploy(unittest.TestCase):
    def test_expected_version_and_no_bindings(self):
        self.assertEqual(a.verify_version(version()), "EXPECTED_VERSION_NO_BINDINGS")
        self.assertEqual(a.verify_current_settings(settings()),
                         "CURRENT_SETTINGS_NO_BINDINGS")

    def test_unexpected_version_and_no_resource_report_fail(self):
        for data in ({}, {"success": False}, {"success": True, "result": {}},
                     {"success": True, "result": {"id": "other"}},
                     {"success": True, "result": {"id": a.EXPECTED_VERSION}}):
            with self.subTest(data=data), self.assertRaises(a.AuditFailure):
                a.verify_version(data)

    def test_binding_secret_d1_and_limiter_all_block(self):
        for kind in ("d1", "secret_text", "ratelimit", "plain_text"):
            item = {"name": "UNEXPECTED", "type": kind}
            with self.subTest(kind=kind):
                with self.assertRaises(a.AuditFailure):
                    a.verify_version(version([item]))
                with self.assertRaises(a.AuditFailure):
                    a.verify_current_settings(settings([item]))

    def test_unknown_settings_fail_closed(self):
        for value in ({}, {"success": True, "result": {}},
                      {"success": True, "result": {"bindings": None}},
                      {"success": True, "result": {"bindings": {}}}):
            with self.subTest(value=value), self.assertRaises(a.AuditFailure):
                a.verify_current_settings(value)

    def test_exact_GET_only_targets_test_worker_and_known_version(self):
        calls = []
        def fake_get(account, token, suffix):
            calls.append(suffix)
            self.assertEqual(account, "a" * 32)
            self.assertEqual(token, "test-secret")
            self.assertTrue(suffix.startswith("/versions/") or suffix == "/settings")
            return version() if suffix.startswith("/versions/") else settings()
        with patch.object(a, "api_get", side_effect=fake_get):
            out = a.audit("a" * 32, "test-secret")
        self.assertEqual(calls, ["/versions/" + a.EXPECTED_VERSION, "/settings"])
        self.assertEqual(out["CURRENT_TRAFFIC_ALLOCATION"], "NOT_VERIFIED")
        self.assertEqual(out["EDGE_HEALTH"], "NOT_VERIFIED")
        self.assertEqual(out["D1"], "NOT_QUERIED")

    def test_api_get_is_GET_and_url_is_worker_test_only(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = json.dumps(version()).encode()
        response.__enter__.return_value = response
        with patch.object(a, "urlopen", return_value=response) as client:
            out = a.api_get("a" * 32, "test" * 10,
                            "/versions/" + a.EXPECTED_VERSION)
        self.assertEqual(out["success"], True)
        req = client.call_args.args[0]
        self.assertEqual(req.method, "GET")
        self.assertIn("/workers/scripts/remura-tv-webhook-test/versions/", req.full_url)
        self.assertNotIn("remura-tv-ingest-lab", req.full_url)
        self.assertNotIn("test" * 10, req.full_url)
        self.assertNotIn("/query", req.full_url)

    def test_missing_token_no_http_call(self):
        with patch.object(a, "urlopen") as client:
            with self.assertRaises(a.AuditFailure):
                a.api_get("a" * 32, "", "/settings")
            client.assert_not_called()

    def test_any_failure_scrubs_outputs(self):
        output = StringIO()
        with patch.object(a, "audit",
                          side_effect=a.AuditFailure("token=must_not_print")):
            with contextlib.redirect_stdout(output):
                self.assertEqual(a.main(), 2)
        self.assertNotIn("must_not_print", output.getvalue())
        self.assertIn("INCONCLUSIVE_FAIL_CLOSED", output.getvalue())


if __name__ == "__main__":
    unittest.main()
