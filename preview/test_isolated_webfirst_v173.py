#!/usr/bin/env python3
"""REMURA v1.73.1: fresh preview packaging safety checks; zero external calls."""
import hashlib
import importlib.util
import json
from pathlib import Path
import unittest
import zipfile

MODULE = Path(__file__).with_name("build_isolated_webfirst_v173.py")
spec = importlib.util.spec_from_file_location("remura_preview_packager", MODULE)
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class IsolatedPreviewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        builder.build()
        cls.zip_bytes = builder.OUT.read_bytes()
        with zipfile.ZipFile(builder.OUT) as z:
            cls.data = {name: z.read(name) for name in z.namelist()}
        cls.manifest = json.loads(cls.data["REMURA-PREVIEW-MANIFEST.json"])

    def test_01_real_cockpit_and_home_are_packaged_unchanged(self):
        self.assertIn("shark-cockpit.html", self.data)
        self.assertIn("index.html", self.data)
        self.assertIn("data/myfxbook/latest.json", self.data)
        self.assertIn("shark-focus-ui.js", self.data)
        for name in ("index.html", "shark-cockpit.html", "shark-cockpit.js"):
            self.assertEqual(self.data[name], (builder.ROOT / name).read_bytes())
        self.assertIn(b"v1.73.1", self.data["shark-cockpit.html"])
        self.assertIn(b"href=\"./shark-cockpit.html\"", self.data["index.html"])

    def test_02_no_protected_or_deployment_files(self):
        forbidden = (".github/", "research/", "deploy/", "scripts/", "tests/",
                     "private-api/", ".env", "secret", "wrangler", "token")
        self.assertNotIn("sw.js", self.data)
        for p in self.data:
            self.assertFalse(p.startswith(forbidden), p)
            self.assertNotIn("../", p)
        self.assertFalse(any(p.endswith(".toml") for p in self.data))

    def test_03_firebase_disabled_in_preview_only(self):
        cfg = self.data["capital-cloud-config.js"].decode("utf-8")
        self.assertIn("REMURA isolated preview", cfg)
        self.assertIn("window.REMURA_FIREBASE_CONFIG = null;", cfg)
        self.assertNotIn("apiKey", cfg)
        self.assertNotEqual(self.data["capital-cloud-config.js"],
                            (builder.ROOT / "capital-cloud-config.js").read_bytes())
        self.assertTrue(self.manifest["firebase_production_disabled"])
        self.assertTrue(self.manifest["service_worker_excluded"])

    def test_04_snapshot_is_public_source_with_own_timestamp_not_guessed_live(self):
        snapshot = json.loads(self.data["data/myfxbook/latest.json"])
        self.assertEqual(snapshot.get("source"), "Myfxbook Community Outlook")
        self.assertIsInstance(snapshot.get("updatedAt"), str)
        self.assertFalse(self.manifest["private_api_available"])
        self.assertFalse(self.manifest["offline_cockpit_supported"])
        self.assertFalse(self.manifest["deployed"])

    def test_05_immutable_contents_and_deterministic_rebuild(self):
        for path, sha in self.manifest["files_sha256"].items():
            self.assertEqual(hashlib.sha256(self.data[path]).hexdigest(), sha, path)
        builder.build()
        self.assertEqual(builder.OUT.read_bytes(), self.zip_bytes)
        self.assertEqual(self.manifest["mode"], "ISOLATED_WEB_FIRST_PREVIEW_ONLY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
