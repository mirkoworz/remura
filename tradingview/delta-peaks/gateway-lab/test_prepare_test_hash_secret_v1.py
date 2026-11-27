#!/usr/bin/env python3
# REMURA v0.8.36 — 13/11/2026 CET — mocked only, no credentials or Cloudflare calls.
import contextlib
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_test_hash_secret_v1 as p
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
READ = "cfat_" + "r" * 48
EDITOR = "cfat_" + "e" * 48
MAIN_UUID = "00000000-0000-4000-8000-000000000001"
TEST_UUID = "00000000-0000-4000-8000-000000000002"
NS = "812345678901"
TEMPLATE = json.loads(p.EXAMPLE.read_text(encoding="utf-8"))


def inventory():
    return {"success": True, "result": [
        {"name": "remura-tv-lab", "uuid": MAIN_UUID, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": TEST_UUID, "jurisdiction": "eu"},
    ], "result_info": {"page": 1, "per_page": 100, "count": 2, "total_count": 2}}


def settings(on=False, secret=False, db=TEST_UUID):
    bindings = [
        {"name": "TELEMETRY_DB", "type": "d1", "id": db},
        {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
         "namespace_id": NS, "simple": {"limit": 20, "period": 60}},
        {"name": "INGEST_ENABLED", "type": "plain_text",
         "text": "true" if on else "false"},
    ]
    if secret:
        bindings.append({"name": "WEBHOOK_TOKEN_SHA256", "type": "secret_text"})
    return {"success": True, "result": {
        "name": "remura-tv-webhook-test", "bindings": bindings}}


class TestHashSecretPreparation(unittest.TestCase):
    def call(self, metadata=None, table=None):
        calls = []
        def d1(method, path, token):
            self.assertEqual(method, "GET")
            self.assertEqual(token, READ)
            self.assertNotIn("/query", path)
            calls.append("D1")
            return inventory() if table is None else table
        def worker(account, token, suffix):
            self.assertEqual((account, token, suffix), (ACCOUNT, EDITOR, "/settings"))
            calls.append("WORKER_TEST")
            return settings() if metadata is None else metadata
        with (patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "require_account_token", return_value=READ),
              patch.object(p, "choose_candidate_namespace", return_value=NS),
              patch.object(p, "api_request", side_effect=d1),
              patch.object(p, "api_get", side_effect=worker)):
            cfg = p.prepare(ACCOUNT, READ, EDITOR, TEMPLATE)
        return cfg, calls

    def test_hash_64_lower_hex_only(self):
        p.validate_hash_secret("0" * 64)
        p.validate_hash_secret("0123456789abcdef" * 4)
        for val in ("", "ab" * 31, "A" * 64, "g" * 64, None, 0, " " + "0" * 64):
            with self.subTest(val=val), self.assertRaises(AuditError):
                p.validate_hash_secret(val)

    def test_preflight_only_gets_and_test_off_secret_absent(self):
        cfg, calls = self.call()
        self.assertEqual(calls, ["D1", "WORKER_TEST"])
        self.assertEqual(cfg["name"], "remura-tv-webhook-test")
        self.assertEqual(cfg["d1_databases"][0]["database_id"], TEST_UUID)
        self.assertEqual(cfg["d1_databases"][0]["database_name"], "remura-tv-lab-test")
        self.assertEqual(cfg["vars"], {"INGEST_ENABLED": "false"})
        self.assertEqual(cfg["ratelimits"][0]["simple"], {"limit": 20, "period": 60})
        self.assertNotIn("WEBHOOK_TOKEN_SHA256", json.dumps(cfg))
        self.assertEqual(TEMPLATE["d1_databases"][0]["database_id"],
                         "REPLACE_WITH_D1_TEST_UUID")

    def test_rejects_on_or_secret_already_present(self):
        for state in (settings(on=True), settings(secret=True), settings(on=True, secret=True)):
            with self.subTest(state=state["result"]["bindings"][2]), self.assertRaises(AuditError):
                self.call(metadata=state)

    def test_rejects_main_database_or_unknown_worker(self):
        for val in (settings(db=MAIN_UUID),
                    {"success": True, "result": {"name": "remura-tv-ingest-lab",
                                                  "bindings": settings()["result"]["bindings"]}}):
            with self.assertRaises(AuditError):
                self.call(metadata=val)

    def test_rejects_no_editor_before_http_calls(self):
        with (patch.object(p, "require_account_id", return_value=ACCOUNT),
              patch.object(p, "api_request") as d1, patch.object(p, "api_get") as get):
            with self.assertRaises(AuditError):
                p.prepare(ACCOUNT, READ, "", TEMPLATE)
        d1.assert_not_called()
        get.assert_not_called()

    def test_no_hash_in_any_output_when_missing_runner(self):
        secret = "a1" * 32
        with (patch.dict(os.environ, {
                  p.GITHUB_SECRET_NAME: secret, "GITHUB_ENV": "", "RUNNER_TEMP": ""},
                  clear=False),
              patch.object(p, "api_request") as d1,
              contextlib.redirect_stdout(StringIO()) as out):
            self.assertEqual(p.main(), 2)
        self.assertNotIn(secret, out.getvalue())
        self.assertIn("BLOCKED_FAIL_CLOSED", out.getvalue())
        d1.assert_not_called()

    def test_failed_inventory_fails_without_synthetic_fallback(self):
        bad = inventory()
        bad["result"][1]["jurisdiction"] = "us"
        with self.assertRaises(AuditError):
            self.call(table=bad)

    def test_private_bundle_only_two_files_when_enabled(self):
        cfg, _ = self.call()
        with tempfile.TemporaryDirectory() as tmp:
            directory = p.create_ephemeral_bundle(cfg, tmp)
            self.assertEqual({x.name for x in directory.iterdir()},
                             {"worker.mjs", "wrangler.json"})
            self.assertNotIn("WEBHOOK_TOKEN_SHA256",
                             (directory / "wrangler.json").read_text())

    def test_source_never_sets_secret_or_deploys(self):
        source = Path(p.__file__).read_text(encoding="utf-8")
        self.assertNotIn("wrangler secret put", source)
        self.assertNotIn("wrangler deploy", source)
        self.assertNotIn("/workers/scripts/remura-tv-ingest-lab", source)
        self.assertNotIn("INSERT INTO", source)


if __name__ == "__main__":
    unittest.main()
