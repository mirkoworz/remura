"""Offline 16-file Watchdog release planning against the real branch checkout.

No LIVE, no network, no auth, no user paths and no executable installer.
"""
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from watchdog_release_blueprint import (
    PAGES, _legacy_files, preview_bundle, rehearse_bundle_transaction
)
from watchdog_staging_rehearsal import sha256


class WatchdogBundleBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.legacy = (ROOT / "deploy/oracle/release_v164.py").read_text("utf-8")
        cls.old_files = _legacy_files(cls.legacy)
        assert cls.old_files is not None
        cls.candidate = {
            name: (ROOT / name).read_bytes()
            for name in (*cls.old_files, "scripts/collector_watchdog.py")
        }

    def test_old_v164_is_15_files_without_watchdog(self):
        self.assertEqual(len(self.old_files), 15)
        self.assertNotIn("scripts/collector_watchdog.py", self.old_files)
        self.assertEqual(set(PAGES), {f for f in self.old_files if f.endswith(".html")})

    def test_actual_source_bytes_pass_blueprint_but_never_authorize_release(self):
        report = preview_bundle(self.legacy, self.candidate)
        self.assertEqual(report["state"], "OFFLINE_BLUEPRINT_ONLY_NO_DEPLOY")
        self.assertEqual(report["file_count"], 16)
        self.assertEqual(report["html_pages"], 9)
        self.assertEqual(report["ui_version_gate"], "V164_REFERENCE_NOT_A_NEW_RELEASE")
        self.assertFalse(report["release_authorized"])
        self.assertEqual(set(report["sha256"]), set(self.candidate))
        for name in self.candidate:
            self.assertEqual(report["sha256"][name], sha256(self.candidate[name]))

    def test_incomplete_or_extra_file_set_denied(self):
        for name in ("scripts/collector_watchdog.py", "scripts/private_server.py",
                     "impostazioni.html", "splash-mascot.webp"):
            with self.subTest(name=name):
                missing = dict(self.candidate)
                missing.pop(name)
                self.assertEqual(preview_bundle(self.legacy, missing)["state"], "MANIFEST_MISMATCH")
        extra = dict(self.candidate)
        extra["scripts/unknown.py"] = b"pass"
        self.assertEqual(preview_bundle(self.legacy, extra)["state"], "MANIFEST_MISMATCH")

    def test_wrong_legacy_manifest_refused(self):
        drift = self.legacy.replace("NEW_FILES = ()",
                                    "NEW_FILES = ('scripts/collector_watchdog.py',)")
        self.assertNotEqual(drift, self.legacy)
        self.assertEqual(preview_bundle(drift, self.candidate)["state"], "INVALID_LEGACY_INSTALLER")

    def test_legacy_list_shortening_refused(self):
        drift = self.legacy.replace('"splash.js", "splash.css", "splash-mascot.webp",',
                                    '"splash.js", "splash.css",')
        self.assertNotEqual(drift, self.legacy)
        self.assertEqual(preview_bundle(drift, self.candidate)["state"], "INVALID_LEGACY_INSTALLER")

    def test_server_or_module_bad_python_refused_even_with_matching_computed_hashes(self):
        for path in ("scripts/private_server.py", "scripts/collector_watchdog.py"):
            with self.subTest(path=path):
                broken = dict(self.candidate)
                broken[path] = b"def broken(:"
                report = preview_bundle(self.legacy, broken)
                self.assertEqual(report["state"], "DEPENDENCY_OR_DIGEST_INVALID")

    def test_preexisting_module_cannot_be_part_of_legacy_installer(self):
        drift = self.legacy.replace(
            '"scripts/private_server.py", "nav.js", "sw.js",',
            '"scripts/private_server.py", "scripts/collector_watchdog.py", "nav.js", "sw.js",'
        )
        self.assertNotEqual(drift, self.legacy)
        self.assertEqual(preview_bundle(drift, self.candidate)["state"], "INVALID_LEGACY_INSTALLER")

    def test_complete_staging_is_sandbox_only(self):
        report = rehearse_bundle_transaction(self.legacy, self.candidate)
        self.assertEqual(report["state"], "SYNTHETIC_ALL_FILES_STAGED_NO_LIVE")
        self.assertEqual(report["files_staged"], 16)
        self.assertFalse(report["release_authorized"])

    def test_failure_at_every_file_rolls_back_all_fifteen_and_removes_new_module(self):
        for index in range(16):
            with self.subTest(failure_after=index):
                report = rehearse_bundle_transaction(
                    self.legacy, self.candidate, fail_after=index)
                self.assertEqual(report["state"], "SYNTHETIC_ALL_FILES_ROLLBACK_VERIFIED")
                self.assertEqual(report["files_restored"], 15)
                self.assertTrue(report["new_module_removed"])
                self.assertFalse(report["release_authorized"])

    def test_unexpected_failure_injection_denied(self):
        for injected in (-1, 16, "1", True, 1.2):
            with self.subTest(fail_after=injected):
                self.assertEqual(rehearse_bundle_transaction(
                    self.legacy, self.candidate, fail_after=injected)["state"],
                    "INVALID_INJECTION")

    def test_no_live_installer_or_privileged_entrypoint_in_blueprint(self):
        source = (ROOT / "scripts/watchdog_release_blueprint.py").read_text("utf-8")
        tree = ast.parse(source)
        imports = [n.names[0].name for n in tree.body if isinstance(n, ast.Import)]
        self.assertEqual(imports, ["ast", "hashlib", "os", "tempfile"])
        for fragment in ("subprocess", "urllib", "socket.", "requests.", "systemctl",
                         "os.system(", "ssh ", "sudo ", "api.github.com",
                         "/opt/remura", "sqlite3.connect", "if __name__"):
            self.assertNotIn(fragment, source)
        self.assertTrue(all(n.name != "apply" for n in tree.body
                            if isinstance(n, ast.FunctionDef)))


if __name__ == "__main__":
    unittest.main()
