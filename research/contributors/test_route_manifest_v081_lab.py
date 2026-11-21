# REMURA Contributors v0.81 LAB — NEW route/role/asset tests only.
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from tempfile import TemporaryDirectory
from shutil import copy2

sys.path.insert(0, str(Path(__file__).resolve().parent))
import route_manifest_v081_lab as m
from staging_source_lock_v079_lab import ROOT, LOCKED_BLOBS

ROUTER = (ROOT / "research/contributors/private_worker_router_v078_lab.mjs").read_text(encoding="utf-8")
BUNDLE = (ROOT / "research/contributors/private_assets_v078_lab.mjs").read_text(encoding="utf-8")

class NewRouteManifestTests(unittest.TestCase):
    def test_01_real_offline_review(self):
        r = m.review()
        self.assertEqual(r["decision"], "NO_GO")
        self.assertEqual(r["pages"], 4)
        self.assertEqual(r["source_status"], "PINNED_GIT_BLOBS_MATCH")
        self.assertEqual(r["api_allowlist_entries"], 17)
        self.assertFalse(r["runtime_policy_attested"])
        self.assertFalse(r["automatic_deploy_allowed"])

    def test_02_exact_routes_and_roles(self):
        self.assertEqual(m.parse_routes(ROUTER), m.EXPECTED_ROUTES)

    def test_03_fail_closed_role_flip(self):
        bad = ROUTER.replace("role:'OWNER'", "role:'CONTRIBUTOR'", 1)
        with self.assertRaises(m.ManifestError):
            m.parse_routes(bad)

    def test_04_fail_closed_extra_route(self):
        bad = ROUTER.replace("Object.freeze({\n '/contributors/':", "Object.freeze({\n '/public/': {file:'fake.html',role:'OWNER'},\n '/contributors/':")
        with self.assertRaises(m.ManifestError):
            m.parse_routes(bad)

    def test_05_fail_closed_invalid_route_token(self):
        bad = ROUTER.replace("'/owner/':", "'/owner/' /* hidden */:")
        with self.assertRaises(m.ManifestError):
            m.parse_routes(bad)

    def test_06_area_exact(self):
        self.assertEqual(m.parse_areas(ROUTER), m.EXPECTED_AREAS)

    def test_07_owner_asset_restriction_guard(self):
        bad = ROUTER.replace("match[1]!=='owner'", "match[1]!=='contributors'")
        with self.assertRaises(m.ManifestError):
            m.parse_areas(bad)

    def test_08_area_missing_asset(self):
        bad = ROUTER.replace("'amendment_client_v063_lab.mjs'", "'wrong.mjs'")
        with self.assertRaises(m.ManifestError):
            m.parse_areas(bad)

    def test_09_api_exact(self):
        self.assertEqual(m.parse_api(ROUTER), m.EXPECTED_API)

    def test_10_api_extra_endpoint(self):
        bad = ROUTER.replace("'/owner/review'", "'/owner/review','/api/public'")
        with self.assertRaises(m.ManifestError):
            m.parse_api(bad)

    def test_11_api_duplicate(self):
        bad = ROUTER.replace("'/api/profile'", "'/api/profile','/api/profile'")
        with self.assertRaises(m.ManifestError):
            m.parse_api(bad)

    def test_12_bundle_exact(self):
        files = m.parse_asset_bundle(BUNDLE, m.EXPECTED_ROUTES, m.EXPECTED_AREAS)
        self.assertEqual(len(files), len(set(files)))
        self.assertGreater(len(files), 4)

    def test_13_bundle_missing_member(self):
        bad = BUNDLE.replace("contributors_recovery_v078_private_lab.html", "unexpected.html", 1)
        with self.assertRaises(m.ManifestError):
            m.parse_asset_bundle(bad, m.EXPECTED_ROUTES, m.EXPECTED_AREAS)

    def test_14_bundle_invalid_json(self):
        with self.assertRaises(m.ManifestError):
            m.parse_asset_bundle("export const privateAssetFilesV078=Object.freeze({x:2});", m.EXPECTED_ROUTES, m.EXPECTED_AREAS)

    def test_15_no_root_type_bypass(self):
        with self.assertRaises(m.ManifestError):
            m.review(".")

    def test_16_source_lock_cannot_be_bypassed_by_review(self):
        with patch.object(m, "verify_contract", side_effect=m.SourceLockError("changed")):
            with self.assertRaises(m.ManifestError):
                m.review()

    def test_17_clean_output_no_sensitive_data(self):
        s = str(m.review())
        for secret in ("@gmail", "cloudflare_token", "account_id", "password", "email"):
            self.assertNotIn(secret, s.lower())

    def test_18_cli_bad_arguments_fail_closed(self):
        self.assertEqual(m.main([]), 2)

    def test_19_cli_good_still_no_go(self):
        self.assertEqual(m.main(["--check"]), 0)

    def test_20_blob_drift_detected_in_isolated_copy(self):
        with TemporaryDirectory() as temp:
            root = Path(temp)
            for name in LOCKED_BLOBS:
                target = root / name
                target.parent.mkdir(parents=True, exist_ok=True)
                copy2(ROOT / name, target)
            path = root / "research/contributors/private_worker_router_v078_lab.mjs"
            path.write_bytes(path.read_bytes() + b"\n// drift")
            with self.assertRaises(m.ManifestError):
                m.review(root)

if __name__ == "__main__":
    unittest.main()
