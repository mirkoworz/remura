"""Offline-only negative tests for v1.65 SHA/tree and mock CI preflight."""
from __future__ import annotations

import ast
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import unittest
from copy import deepcopy

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "deploy/oracle"
sys.path.insert(0, str(DIR))
import v165_pinned_preflight_lab as m


class PinnedPreflightLabTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.sources = m.preview.read_sources(ROOT)
        cls.time = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)

    def fixture(self):
        return m.synthetic_metadata()

    def reject(self, evidence, error):
        with self.assertRaisesRegex(m.FixtureRejected, "STOP_" + error):
            m.verify_synthetic_pins(evidence)

    def test_fixture_is_never_actual_attestation(self):
        report = m.evaluate(self.fixture(), self.sources,
                            simulated_install_time=self.time)
        self.assertEqual(report["sourceFilesPinnedAndPreviewed"], 14)
        self.assertEqual(report["ninePagesPreparedInMemory"], 9)
        self.assertTrue(report["syntheticFixtureCiMatches"])
        for key in ("actualPushMainCiVerified", "installedLiveV164Attested",
                    "realSqliteBackupAndRestoreVerified", "realRollbackVerified",
                    "realReleaseAuthorized", "actualDateStampedOnLivePages",
                    "newModulesInstalled", "autoUpdaterReconciled",
                    "realVpsContacted", "researchC5Enabled"):
            self.assertFalse(report[key], key)
        self.assertEqual(report["operationalDecision"], m.NO_GO)

    def test_exact_pin_to_preparatory_commit(self):
        self.assertTrue(m.verify_synthetic_pins(self.fixture()))
        self.assertEqual(m.SOURCE_COMMIT,
                         "3819fe1450980c046533e400d283b25f37a67bd3")
        self.assertEqual(set(m.preview.SOURCE_BLOBS), m.protocol.FILE_SET)

    def test_wrong_mode_or_missing_flag_rejected(self):
        for mode in ("REAL", None, False, "PRODUCTION", 1):
            with self.subTest(mode=mode):
                e = self.fixture()
                e["mode"] = mode
                self.reject(e, "SYNTHETIC_MODE_REQUIRED")

    def test_unexpected_secret_or_missing_field_rejected(self):
        for mutate in ("extra", "missing"):
            e = self.fixture()
            if mutate == "extra":
                e["privateToken"] = "do-not-accept"
            else:
                del e["sourceTree"]
            self.reject(e, "STRICT_FIXTURE_FIELDS")

    def test_baseline_pin_cannot_be_reused_as_installed_sha(self):
        e = self.fixture()
        e["baseMainSha"] = "2" * 40
        self.reject(e, "BASE_MAIN_CHANGED")

    def test_source_commit_replaced_rejected(self):
        e = self.fixture()
        e["sourceCommit"] = "3" * 40
        self.reject(e, "SOURCE_COMMIT_CHANGED")

    def test_target_not_baseline_and_valid_lowercase_sha(self):
        for value in ("x" * 40, "A" * 40, "short",
                      m.preview.BASE_MAIN_SHA, m.SOURCE_COMMIT, None, True):
            with self.subTest(value=value):
                e = self.fixture()
                e["futureMainSha"] = value
                self.reject(e, "FICTIONAL_TARGET_INVALID")

    def test_main_moves_after_first_ci_fetch(self):
        e = self.fixture()
        e["mainAtCheckSha"] = "4" * 40
        self.reject(e, "MAIN_MOVED")

    def test_tree_missing_extra_or_wrong_blob_rejected(self):
        for mutation in ("missing", "extra", "sha", "type"):
            e = self.fixture()
            if mutation == "missing":
                del e["sourceTree"]["nav.js"]
            elif mutation == "extra":
                e["sourceTree"]["private/remura.env"] = "0" * 40
            elif mutation == "sha":
                e["sourceTree"]["nav.js"] = "0" * 40
            else:
                e["sourceTree"]["nav.js"] = 12
            self.reject(e, "SOURCE_TREE_UNPINNED")

    def test_duplicate_workflow_rejected(self):
        e = self.fixture()
        e["ciRuns"][1] = deepcopy(e["ciRuns"][0])
        self.reject(e, "CI_WORKFLOW_MISSING_OR_DUPLICATE")

    def test_missing_or_extra_ci_run_rejected(self):
        for runs in ([], self.fixture()["ciRuns"][:1],
                     self.fixture()["ciRuns"] * 2, None):
            e = self.fixture()
            e["ciRuns"] = runs
            self.reject(e, "CI_RUN_COUNT")

    def test_forged_workflow_or_extra_field_rejected(self):
        e = self.fixture()
        e["ciRuns"][0]["workflow"] = "other.yml"
        self.reject(e, "CI_WORKFLOW_MISSING_OR_DUPLICATE")
        e = self.fixture()
        e["ciRuns"][0]["authorization"] = True
        self.reject(e, "CI_RUN_FIELDS")

    def test_only_push_main_of_matching_target_accepted(self):
        for field, value in (("head_sha", "2" * 40),
                             ("head_branch", "release/draft"),
                             ("event", "pull_request"),
                             ("event", "workflow_dispatch"),
                             ("status", "queued"),
                             ("conclusion", "failure"),
                             ("conclusion", "cancelled")):
            with self.subTest(field=field, value=value):
                e = self.fixture()
                e["ciRuns"][0][field] = value
                self.reject(e, "CI_NOT_GREEN_PUSH_MAIN")

    def test_blob_tampering_rejected(self):
        sources = dict(self.sources)
        sources["nav.js"] += b"\n// modified"
        with self.assertRaisesRegex(ValueError, "STOP_SOURCE_BLOB_DIVERGED"):
            m.preview_manifest(sources, self.time)

    def test_missing_or_extra_file_rejected(self):
        for mutation in ("extra", "missing"):
            sources = dict(self.sources)
            if mutation == "extra":
                sources["private/remura-prices.sqlite3"] = b"not-a-db"
            else:
                del sources["scripts/storage_cache_v165.py"]
            with self.assertRaisesRegex(ValueError, "STOP_UNREVIEWED_SOURCE_FILE_SET"):
                m.preview_manifest(sources, self.time)

    def test_naive_time_rejected(self):
        with self.assertRaisesRegex(m.FixtureRejected, "STOP_AWARE_SIMULATED_TIME_REQUIRED"):
            m.preview_manifest(self.sources, datetime(2026, 11, 8, 10, 0))

    def test_deterministic_preview_digest_and_module_kinds(self):
        first = m.preview_manifest(self.sources, self.time)
        second = m.preview_manifest(self.sources, self.time)
        self.assertEqual(first, second)
        self.assertEqual(len(first["files"]), 14)
        self.assertEqual(sum(x["kind"] == "new" for x in first["files"].values()), 2)
        self.assertEqual(first["simulatedTimeOnly"], "08/11/2026 13:00 (Italia)")
        self.assertFalse(first["realLiveRollbackHashesKnown"])
        self.assertNotIn("oldLiveSha256", str(first))

    def test_dst_preview_changes_digest_but_never_live(self):
        summer = datetime(2026, 7, 8, 12, 0, tzinfo=timezone.utc)
        a = m.preview_manifest(self.sources, self.time)
        b = m.preview_manifest(self.sources, summer)
        self.assertEqual(b["simulatedTimeOnly"], "08/07/2026 14:00 (Italia)")
        self.assertNotEqual(a["previewBundleSha256"], b["previewBundleSha256"])

    def test_cli_only_offline_and_without_production_dependencies(self):
        src = (DIR / "v165_pinned_preflight_lab.py").read_text()
        for arg in ("--apply", "--deploy", "--rollback-dir", "--database",
                    "--release", "--target"):
            self.assertNotIn('add_argument("' + arg + '"', src)
        imports = {x.name.partition(".")[0] for n in ast.walk(ast.parse(src))
                   if isinstance(n, ast.Import) for x in n.names}
        self.assertTrue(imports.isdisjoint(
            {"sqlite3", "subprocess", "urllib", "requests", "socket", "os"}))
        result = subprocess.run(
            [sys.executable, str(DIR / "v165_pinned_preflight_lab.py"),
             "--check-fixture-offline"],
            cwd=ROOT, capture_output=True, text=True, timeout=10,
            check=True)
        self.assertIn('"actualPushMainCiVerified": false', result.stdout)
        self.assertIn(m.NO_GO, result.stdout)


if __name__ == "__main__":
    unittest.main()
