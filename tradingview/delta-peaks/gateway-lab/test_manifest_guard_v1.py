#!/usr/bin/env python3
# REMURA Manifest Safety TESTS v0.8.31 — 13/11/2026, ore 21:06 CET
# Pure synthetic offline tests. No Cloudflare tokens, deploy or network.
import copy
import json
from pathlib import Path
import unittest
import predeploy_test_manifest_guard_v1 as guard
from predeploy_test_manifest_guard_v1 import ManifestError

EXAMPLE = Path(__file__).with_name("wrangler.webhook-test.EXAMPLE.json")


def example():
    return json.loads(EXAMPLE.read_text(encoding="utf-8"))


def resolved():
    cfg = example()
    cfg["d1_databases"][0]["database_id"] = "cf6b4c40-9090-4a0e-ac48-7c14e8b5a06f"
    cfg["ratelimits"][0]["namespace_id"] = "43210"
    return cfg


class ManifestTests(unittest.TestCase):
    def test_committed_example_cannot_be_deployed(self):
        self.assertEqual(guard.verify_manifest(example()),
                         "EXAMPLE_BLOCKED_BY_UNRESOLVED_IDS")
        self.assertEqual(guard.main(), 0)

    def test_resolved_synthetic_structure_is_not_live_authorization(self):
        self.assertEqual(guard.verify_manifest(resolved()),
                         "STRUCTURALLY_READY_OFFLINE_ONLY")

    def test_no_real_prod_db_in_test_manifest(self):
        cfg = resolved()
        cfg["d1_databases"][0]["database_name"] = "remura-tv-lab"
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_ingest_enabled_is_forbidden(self):
        for state in ("true", True, 1, ""):
            cfg = resolved()
            cfg["vars"]["INGEST_ENABLED"] = state
            with self.subTest(state=state), self.assertRaises(ManifestError):
                guard.verify_manifest(cfg)

    def test_secret_inline_variable_forbidden(self):
        cfg = resolved()
        cfg["vars"]["WEBHOOK_TOKEN_SHA256"] = "SECRET_DO_NOT_STORE"
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_preview_urls_must_be_explicitly_disabled(self):
        cfg = resolved()
        self.assertIs(cfg["preview_urls"], False)
        for value in (True, "false", None, 0, 1):
            bad = copy.deepcopy(cfg)
            bad["preview_urls"] = value
            with self.subTest(value=value), self.assertRaises(ManifestError):
                guard.verify_manifest(bad)
        missing = copy.deepcopy(cfg)
        del missing["preview_urls"]
        with self.assertRaises(ManifestError):
            guard.verify_manifest(missing)

    def test_unauthorized_routes_forbidden(self):
        cfg = resolved()
        cfg["routes"] = ["example.com/*"]
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_wrong_worker_name_forbidden(self):
        cfg = resolved()
        cfg["name"] = "remura-tv-ingest-lab"
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_extra_d1_binding_forbidden(self):
        cfg = resolved()
        cfg["d1_databases"].append(copy.deepcopy(cfg["d1_databases"][0]))
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_limiter_missing_or_weakened_forbidden(self):
        cfg = resolved()
        cfg["ratelimits"] = []
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)
        cfg = resolved()
        cfg["ratelimits"][0]["simple"]["limit"] = 10_000
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)

    def test_namespace_invalid_type_and_placeholder_mismatch(self):
        for invalid in (None, -1, 0, 5, "0", "-5", "not-a-number", "00001"):
            cfg = resolved()
            cfg["ratelimits"][0]["namespace_id"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ManifestError):
                guard.verify_manifest(cfg)

    def test_uuid_invalid_or_template_half_filled(self):
        for invalid in (None, "remura-tv-lab", "", "REPLACE_WITH_D1_TEST_UUID"):
            cfg = resolved()
            cfg["d1_databases"][0]["database_id"] = invalid
            with self.subTest(invalid=invalid), self.assertRaises(ManifestError):
                guard.verify_manifest(cfg)

    def test_change_main_script_forbidden(self):
        cfg = resolved()
        cfg["main"] = "different-worker.mjs"
        with self.assertRaises(ManifestError):
            guard.verify_manifest(cfg)


if __name__ == "__main__":
    unittest.main()
