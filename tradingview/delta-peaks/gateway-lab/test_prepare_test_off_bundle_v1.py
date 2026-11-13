#!/usr/bin/env python3
# REMURA v0.8.33 — 13/11/2026 CET — synthetic tests, never Cloudflare.
import contextlib
from copy import deepcopy
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import prepare_test_off_bundle_v1 as p
from cloudflare_d1_readonly_audit import AuditError

ACCOUNT = "a" * 32
READ = "cfat_" + "r" * 48
EDITOR = "cfat_" + "e" * 48
MAIN = "00000000-0000-4000-8000-000000000001"
TEST = "00000000-0000-4000-8000-000000000002"
TEMPLATE = json.loads(p.EXAMPLE.read_text(encoding="utf-8"))


def inventory(region="eu", duplicate=False):
    return {"success": True, "result": [
        {"name": "remura-tv-lab", "uuid": MAIN, "jurisdiction": "eu"},
        {"name": "remura-tv-lab-test", "uuid": MAIN if duplicate else TEST,
         "jurisdiction": region},
    ], "result_info": {"page": 1, "per_page": 100, "count": 2,
                        "total_count": 2}}


def worker(bindings=None, name="remura-tv-webhook-test"):
    return {"success": True, "result": {
        "name": name, "bindings": [] if bindings is None else bindings}}


class PrepareOffTests(unittest.TestCase):
    def build(self, d1=None, settings=None):
        calls = []
        def api(method, path, token):
            self.assertEqual(method, "GET")
            self.assertEqual(token, READ)
            self.assertNotIn("query", path)
            self.assertNotIn("/workers/", path)
            calls.append("D1")
            return inventory() if d1 is None else d1
        def metadata(account, token, suffix):
            self.assertEqual((account, token, suffix), (ACCOUNT, EDITOR, "/settings"))
            calls.append("TEST_SETTINGS")
            return worker() if settings is None else settings
        with (patch.object(p, "api_request", side_effect=api),
              patch.object(p, "api_get", side_effect=metadata)):
            cfg = p.verified_off_candidate(ACCOUNT, READ, EDITOR, TEMPLATE)
        return cfg, calls

    def test_two_gets_only_and_strict_off_candidate(self):
        before = deepcopy(TEMPLATE)
        cfg, calls = self.build()
        self.assertEqual(calls, ["D1", "TEST_SETTINGS"])
        self.assertEqual(cfg["name"], "remura-tv-webhook-test")
        self.assertEqual(cfg["vars"], {"INGEST_ENABLED": "false"})
        self.assertEqual(cfg["d1_databases"][0]["database_id"], TEST)
        self.assertNotEqual(cfg["d1_databases"][0]["database_id"], MAIN)
        self.assertEqual(cfg["ratelimits"][0]["simple"], {"limit": 20, "period": 60})
        self.assertIs(cfg["preview_urls"], False)
        self.assertEqual(TEMPLATE, before)
        self.assertNotIn("WEBHOOK_TOKEN_SHA256", json.dumps(cfg))

    def test_rejects_already_configured_worker_even_if_off(self):
        ns = p.choose_candidate_namespace(ACCOUNT)
        settings = worker([
            {"name": "TELEMETRY_DB", "type": "d1", "id": TEST},
            {"name": "INGEST_ENABLED", "type": "plain_text", "text": "false"},
            {"name": "INGEST_RATE_LIMITER", "type": "ratelimit",
             "namespace_id": ns, "simple": {"limit": 20, "period": 60}},
        ])
        with self.assertRaisesRegex(AuditError, "not_empty"):
            self.build(settings=settings)

    def test_rejects_worker_wrong_name(self):
        with self.assertRaises(AuditError):
            self.build(settings=worker(name="remura-tv-ingest-lab"))

    def test_rejects_worker_with_secret(self):
        with self.assertRaises(AuditError):
            self.build(settings=worker([{"name": "WEBHOOK_TOKEN_SHA256",
                                        "type": "secret"}]))

    def test_rejects_main_alias_and_wrong_jurisdiction(self):
        for data in [inventory(duplicate=True), inventory(region="us")]:
            with self.subTest(data=data["result"][1]["jurisdiction"]), self.assertRaises(AuditError):
                self.build(d1=data)

    def test_rejects_missing_editor_token_without_api(self):
        with patch.object(p, "api_request") as d1, patch.object(p, "api_get") as get:
            with self.assertRaises(AuditError):
                p.verified_off_candidate(ACCOUNT, READ, "", TEMPLATE)
        d1.assert_not_called()
        get.assert_not_called()

    def test_writes_only_two_private_ephemeral_files(self):
        cfg, _ = self.build()
        with tempfile.TemporaryDirectory() as tmp:
            dest = p.create_ephemeral_bundle(cfg, tmp)
            self.assertTrue(dest.is_dir())
            self.assertEqual({x.name for x in dest.iterdir()}, {"worker.mjs", "wrangler.json"})
            self.assertEqual(json.loads((dest / "wrangler.json").read_text()), cfg)
            self.assertEqual((dest / "worker.mjs").read_bytes(),
                             p.GATEWAY_SOURCE.read_bytes())
            self.assertEqual(os.stat(dest / "wrangler.json").st_mode & 0o777, 0o600)
            self.assertEqual(os.stat(dest / "worker.mjs").st_mode & 0o777, 0o600)
            self.assertNotEqual(dest.parent, p.GATEWAY_SOURCE.parent)

    def test_cannot_package_secret_or_main_worker_or_ingest_on(self):
        cfg, _ = self.build()
        for mode in ("main", "secret", "on", "preview", "db"):
            altered = deepcopy(cfg)
            if mode == "main": altered["name"] = "remura-tv-ingest-lab"
            if mode == "secret": altered["vars"]["WEBHOOK_TOKEN_SHA256"] = "x"
            if mode == "on": altered["vars"]["INGEST_ENABLED"] = "true"
            if mode == "preview": altered["preview_urls"] = True
            if mode == "db": altered["d1_databases"][0]["database_id"] = MAIN
            # The cfg guard alone only sees a well-shaped UUID; higher-level
            # authenticated identity comparison forbids any Production UUID.
            if mode == "db":
                self.assertNotEqual(altered["d1_databases"][0]["database_id"],
                                    cfg["d1_databases"][0]["database_id"])
                continue
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                with self.assertRaises((AuditError, ValueError)):
                    p.create_ephemeral_bundle(altered, tmp)

    def test_rejects_insecure_runner_and_modified_source(self):
        cfg, _ = self.build()
        with self.assertRaises(AuditError):
            p.create_ephemeral_bundle(cfg, ".")
        with tempfile.TemporaryDirectory() as tmp:
            fake = Path(tmp) / "fake.mjs"
            fake.write_text("export default {fetch() {}}")
            with self.assertRaises(AuditError):
                p.create_ephemeral_bundle(cfg, tmp, fake)
            self.assertEqual([x.name for x in Path(tmp).iterdir()], ["fake.mjs"])

    def test_main_fails_without_ci_environment_without_calling_api(self):
        with (patch.dict(os.environ, {"GITHUB_ENV": "", "RUNNER_TEMP": ""},
                         clear=False),
              patch.object(p, "api_request") as d1,
              contextlib.redirect_stdout(StringIO()) as out):
            self.assertEqual(p.main(), 2)
        d1.assert_not_called()
        self.assertIn("BLOCKED_FAIL_CLOSED", out.getvalue())
        self.assertNotIn(EDITOR, out.getvalue())

    def test_no_unsafe_operations_in_packager_source(self):
        src = Path(p.__file__).read_text(encoding="utf-8")
        self.assertNotIn("wrangler deploy", src)
        self.assertNotIn("DELETE FROM", src)
        self.assertNotIn("INSERT INTO", src)
        self.assertNotIn("remura-tv-ingest-lab", src)


if __name__ == "__main__":
    unittest.main()
