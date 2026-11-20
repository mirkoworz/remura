#!/usr/bin/env python3
# REMURA Worker Probe TEST v0.8.18 — 13/11/2026, ore 13:52 CET
# Synthetic metadata + mocks only; no network, Cloudflare, writes, tokens.
import contextlib
from io import StringIO
import unittest
from unittest.mock import patch

import worker_metadata_probe_v1 as p
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
TOKEN = "cfat_" + "A" * 44


def fixture(ingest="false", limiter=True):
    items = [
        {"name": "INGEST_ENABLED", "type": "plain_text", "text": ingest},
        {"name": "TELEMETRY_DB", "type": "d1",
         "id": "internal-sensitive-database-uuid"},
        {"name": "WEBHOOK_TOKEN_SHA256", "type": "secret_text",
         "text": "SECRET_MUST_NEVER_APPEAR"},
    ]
    if limiter:
        items.append({"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
                      "namespace_id": "123456789"})
    items.append({"name": "PRIVATE_OTHER", "type": "plain_text",
                  "text": "ANOTHER_SECRET_VALUE"})
    return {"success": True, "result": {"bindings": items,
            "compatibility_date": "2026-11-13"}}


class WorkerMetadataProbeTests(unittest.TestCase):
    def test_known_binding_flags_without_secret_values(self):
        res = p.inspect_settings(fixture())
        self.assertEqual(res, {
            "INGEST_FLAG": "OFF",
            "D1_BINDING": "PRESENT",
            "TOKEN_HASH_BINDING": "PRESENT",
            "RATE_LIMIT_BINDING": "PRESENT",
        })
        self.assertNotIn("SECRET_MUST", str(res))
        self.assertNotIn("PRIVATE_OTHER", str(res))
        self.assertNotIn("internal-sensitive", str(res))

    def test_enabled_flag_is_not_automatic_authorization(self):
        self.assertEqual(p.inspect_settings(fixture("true"))["INGEST_FLAG"],
                         "ON")

    def test_no_flag_is_absent_not_verification_of_runtime_off(self):
        data = fixture()
        data["result"]["bindings"] = [
            b for b in data["result"]["bindings"]
            if b["name"] != "INGEST_ENABLED"
        ]
        self.assertEqual(p.inspect_settings(data)["INGEST_FLAG"], "ABSENT")

    def test_missing_limiter_is_reported_not_invented(self):
        self.assertEqual(p.inspect_settings(fixture(limiter=False))
                         ["RATE_LIMIT_BINDING"], "ABSENT")

    def test_secret_binding_wrong_type_is_reported(self):
        data = fixture()
        data["result"]["bindings"][2]["type"] = "plain_text"
        self.assertEqual(p.inspect_settings(data)["TOKEN_HASH_BINDING"],
                         "UNEXPECTED_TYPE")

    def test_bad_shape_and_missing_bindings_fail_closed(self):
        for bad in ({}, {"success": True, "result": {}},
                    {"success": True, "result": {"bindings": {}}},
                    {"success": True, "result": {"bindings": [None]}}):
            with self.subTest(bad=bad), self.assertRaises(AuditError):
                p.inspect_settings(bad)

    def test_duplicate_name_is_rejected(self):
        data = fixture()
        data["result"]["bindings"].append(
            {"name": "INGEST_ENABLED", "type": "plain_text", "text": "true"}
        )
        with self.assertRaisesRegex(AuditError, "duplicate"):
            p.inspect_settings(data)

    def test_403_is_not_called_access_or_ingestion_disabled(self):
        code = p.classify_failure(AuditError("cloudflare_http_error_403"))
        self.assertEqual(code, "INCONCLUSIVE_HTTP_403")
        self.assertNotIn("ACCESS", code)
        self.assertNotIn("DISABLED", code)

    def test_authenticated_probe_has_two_get_and_no_public_edge_calls(self):
        paths = []
        def api(method, path, token):
            self.assertEqual(method, "GET")
            self.assertTrue(path.startswith("/accounts/" + ACCOUNT))
            self.assertNotIn("workers.dev", path)
            paths.append(path)
            if path.endswith("/tokens/verify"):
                return {"success": True, "result": {"status": "active"}}
            return fixture()
        with (patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "require_account_token", return_value=TOKEN),
              patch.object(p, "api_request", side_effect=api)):
            res = p.audit(ACCOUNT, TOKEN)
        self.assertEqual(res["INGEST_FLAG"], "OFF")
        self.assertEqual(len(paths), 2)
        self.assertEqual(paths[1], "/accounts/" + ACCOUNT +
                         "/workers/scripts/remura-tv-ingest-lab/settings")

    def test_denied_scope_returns_inconclusive_and_zero_exit(self):
        out = StringIO()
        with (patch.object(p, "audit",
                           side_effect=AuditError("cloudflare_http_error_403")),
              contextlib.redirect_stdout(out)):
            exit_code = p.main()
        self.assertEqual(exit_code, 0)
        self.assertIn("REMURA_WORKER_SETTINGS=INCONCLUSIVE_HTTP_403",
                      out.getvalue())
        self.assertNotIn("METADATA_READ_SUCCEEDED", out.getvalue())

    def test_success_output_is_allowlisted_and_redacted(self):
        out = StringIO()
        with (patch.object(p, "audit", return_value=p.inspect_settings(fixture())),
              contextlib.redirect_stdout(out)):
            self.assertEqual(p.main(), 0)
        text = out.getvalue()
        self.assertIn("METADATA_READ_SUCCEEDED", text)
        self.assertIn("D1_TARGET_UUID=UNVERIFIED", text)
        self.assertNotIn("SECRET_MUST", text)
        self.assertNotIn("internal-sensitive", text)
        self.assertNotIn("ANOTHER_SECRET", text)
        self.assertNotIn("cfat_", text)


if __name__ == "__main__":
    unittest.main()
