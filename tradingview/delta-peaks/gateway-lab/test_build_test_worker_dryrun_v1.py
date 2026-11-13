#!/usr/bin/env python3
# REMURA v0.8.23 TEST — 13/11/2026, 15:28:19 Europe/Rome
# Pure temporary local files. No npm, Cloudflare, network or deploy.
from __future__ import annotations
import copy
import json
from pathlib import Path
import tempfile
import unittest

from build_test_worker_dryrun_v1 import (
    FAKE_LIMITER_NAMESPACE, FAKE_TEST_UUID, DryRunError, make_bundle,
)
from predeploy_test_manifest_guard_v1 import verify_manifest


class TestSyntheticDryRun(unittest.TestCase):
    def test_materialization_uses_only_synthetic_target_and_off(self):
        with tempfile.TemporaryDirectory() as root:
            destination = Path(root) / "dryrun"
            config_path = make_bundle(destination)
            cfg = json.loads(config_path.read_text(encoding="utf-8"))
            self.assertEqual(cfg["name"], "remura-tv-webhook-test")
            self.assertEqual(cfg["vars"], {"INGEST_ENABLED": "false"})
            self.assertEqual(cfg["d1_databases"][0]["database_name"],
                             "remura-tv-lab-test")
            self.assertEqual(cfg["d1_databases"][0]["database_id"], FAKE_TEST_UUID)
            self.assertEqual(cfg["ratelimits"][0]["namespace_id"],
                             FAKE_LIMITER_NAMESPACE)
            self.assertEqual(set(destination.iterdir()), {
                destination / "wrangler.json", destination / "worker.mjs"
            })
            self.assertNotIn("$comment", cfg)
            self.assertTrue((destination / "worker.mjs").is_file())
            self.assertNotIn("CLOUDFLARE_API_TOKEN",
                             config_path.read_text(encoding="utf-8"))
            self.assertNotIn("WEBHOOK_TOKEN_SHA256",
                             config_path.read_text(encoding="utf-8"))

    def test_existing_directory_rejected_before_writing(self):
        with tempfile.TemporaryDirectory() as root:
            dest = Path(root) / "dryrun"
            dest.mkdir()
            (dest / "keep.txt").write_text("DO_NOT_TOUCH")
            with self.assertRaises(DryRunError):
                make_bundle(dest)
            self.assertEqual((dest / "keep.txt").read_text(), "DO_NOT_TOUCH")
            self.assertEqual(len(list(dest.iterdir())), 1)

    def test_invalid_template_cannot_be_bundled(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            bad = json.loads(
                (Path(__file__).parent / "wrangler.webhook-test.EXAMPLE.json")
                .read_text(encoding="utf-8")
            )
            for change in [
                lambda c: c["vars"].update({"INGEST_ENABLED": "true"}),
                lambda c: c["d1_databases"][0].update(
                    {"database_name": "remura-tv-lab"}),
                lambda c: c.update({"name": "remura-tv-ingest-lab"}),
                lambda c: c.update({"routes": ["example.org/*"]}),
                lambda c: c["ratelimits"].clear(),
            ]:
                cfg = copy.deepcopy(bad)
                change(cfg)
                invalid_json = p / "invalid.json"
                invalid_json.write_text(json.dumps(cfg), encoding="utf-8")
                target = p / "out"
                with self.subTest(change=str(change)), self.assertRaises(
                    (DryRunError, ValueError)
                ):
                    make_bundle(target, example_path=invalid_json)
                self.assertFalse(target.exists())

    def test_partial_realistic_id_resolution_is_forbidden(self):
        with tempfile.TemporaryDirectory() as root:
            p = Path(root)
            raw = json.loads((Path(__file__).parent /
                "wrangler.webhook-test.EXAMPLE.json").read_text())
            raw["d1_databases"][0]["database_id"] = FAKE_TEST_UUID
            source = p / "not_example.json"
            source.write_text(json.dumps(raw))
            with self.assertRaises(DryRunError):
                make_bundle(p / "out", example_path=source)

    def test_synthetic_generated_config_is_structurally_valid_only(self):
        with tempfile.TemporaryDirectory() as root:
            cfg = json.loads(make_bundle(Path(root) / "out").read_text())
            template = json.loads((Path(__file__).parent /
                "wrangler.webhook-test.EXAMPLE.json").read_text())
            cfg["$comment"] = template["$comment"]
            self.assertEqual(verify_manifest(cfg),
                             "STRUCTURALLY_READY_OFFLINE_ONLY")
            self.assertNotIn("LIVE", json.dumps(cfg))


if __name__ == "__main__":
    unittest.main()
