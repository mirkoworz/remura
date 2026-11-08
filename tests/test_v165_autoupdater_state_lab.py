"""v1.65 offline autoupdater state/candidate split: all evidence synthetic."""
from __future__ import annotations

import ast
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "deploy" / "oracle"
sys.path.insert(0, str(SCRIPTS))
import v165_autoupdater_state_lab as m


class V165AutoupdaterStateLabTests(unittest.TestCase):
    def simulate(self, fault=None):
        return m.rehearse(mode=m.MODE, fault=fault)

    def test_mock_success_requires_separate_state_reconcile(self):
        report = self.simulate()
        self.assertEqual(report["state"], "FAKE_STATE_ONLY_RECONCILED_NOT_LIVE")
        self.assertTrue(report["fakeUpdaterStateReconciledSeparately"])
        self.assertFalse(report["fakeUpdaterStateChangedByCodeInstall"])

    def test_all_production_proof_flags_false(self):
        r = self.simulate()
        self.assertTrue(r["mockedGithubCiNotRealEvidence"])
        self.assertTrue(r["fakeFilesystemOnly"])
        for key in (
            "realVpsAccess", "actualLiveVersionAttested",
            "realGitHubPushMainCiVerified", "realAutoupdaterChanged",
            "realSqliteBackupRestored", "offhostRollbackVerified",
            "productionAuthorization", "researchC5Enabled"
        ):
            self.assertFalse(r[key], key)
        self.assertEqual(r["operationalDecision"], m.NO_GO)

    def test_stop_after_install_never_reconciles(self):
        r = self.simulate("stop_before_reconcile")
        self.assertEqual(r["state"], "FAKE_PENDING_NOT_RECONCILED")
        self.assertFalse(r["fakeUpdaterStateReconciledSeparately"])

    def test_rollback_before_reconcile_preserves_old_state(self):
        r = self.simulate("rollback_before_reconcile")
        self.assertTrue(r["fakeRollbackVerified"])
        self.assertFalse(r["fakeUpdaterStateReconciledSeparately"])
        self.assertEqual(r["state"],
                         "FAKE_ROLLBACK_BEFORE_RECONCILE_STATE_INTACT")

    def test_rollback_after_reconcile_requires_new_separate_operation(self):
        r = self.simulate("rollback_after_reconcile")
        self.assertTrue(r["fakeRollbackVerified"])
        self.assertTrue(r["fakeUpdaterStateReconciledSeparately"])
        self.assertEqual(r["state"],
                         "FAKE_INVERSE_RECONCILE_REQUIRED_NO_AUTO_FIX")

    def test_main_moved_rejects_reconcile(self):
        self.assertEqual(self.simulate("main_moved")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_pr_ci_cannot_pose_as_push_main_ci(self):
        self.assertEqual(self.simulate("bad_ci_event")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_updater_busy_rejects(self):
        self.assertEqual(self.simulate("updater_busy")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_missing_fake_lock_rejects(self):
        self.assertEqual(self.simulate("no_lock")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_missing_health_rejects(self):
        self.assertEqual(self.simulate("health_failed")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_missing_backup_rejects(self):
        self.assertEqual(self.simulate("backup_unverified")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_rogue_failed_sha_rejects_state_reconcile(self):
        self.assertEqual(self.simulate("state_tampered")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_tampered_candidate_file_rejects_reconcile(self):
        self.assertEqual(self.simulate("candidate_tampered")["state"],
                         "FAKE_RECONCILE_REJECTED")

    def test_unknown_fault_rejected(self):
        with self.assertRaisesRegex(m.StateLabStop, "STOP_UNKNOWN_FAULT"):
            self.simulate("shutdown_live")

    def test_wrong_mode_or_none_rejected(self):
        for bad in (None, "LIVE", "", True, "OFFLINE"):
            with self.subTest(value=bad):
                with self.assertRaisesRegex(m.StateLabStop,
                                            "STOP_OFFLINE_MODE_REQUIRED"):
                    m.rehearse(mode=bad)

    def test_fake_shas_are_not_actual_baseline_assertions(self):
        self.assertEqual(m.OLD_FAKE_SHA, "a" * 40)
        self.assertEqual(m.TARGET_FAKE_SHA, "1" * 40)
        self.assertNotEqual(m.OLD_FAKE_SHA, m.protocol.BASE_MAIN_SHA)
        self.assertNotEqual(m.TARGET_FAKE_SHA, m.protocol.BASE_MAIN_SHA)

    def test_state_is_strict_and_failed_sha_must_be_empty(self):
        old = m._prior_state()
        self.assertEqual(set(old), m.STATE_KEYS)
        self.assertEqual(old["failedSha"], "")
        bad = dict(old)
        bad["privateSecret"] = "never"
        with self.assertRaisesRegex(m.StateLabStop, "STOP_STATE_FIELDS"):
            m._encode_state(bad)

    def test_boolean_instead_of_valid_state_string_rejected(self):
        bad = m._prior_state()
        bad["installedSha"] = True
        with self.assertRaisesRegex(m.StateLabStop, "STOP_STATE_TYPES"):
            m._encode_state(bad)

    def test_rollback_preexisting_module_manifest_stays_12_plus_2(self):
        old, new = m.rollback._fixtures()
        self.assertEqual(set(old), set(m.protocol.EXISTING_FILES))
        self.assertEqual(set(new), m.protocol.FILE_SET)
        self.assertEqual(len(old), 12)
        self.assertEqual(len(new), 14)

    def test_evidence_schema_is_mock_only(self):
        proof = m._mock_target_evidence()
        self.assertEqual(proof["mode"], m.pinned.MODE)
        self.assertNotIn("realLiveAuthorisation", proof)
        self.assertEqual(proof["futureMainSha"], m.TARGET_FAKE_SHA)
        self.assertEqual(len(proof["ciRuns"]), 2)

    def test_missing_state_file_fails_closed(self):
        with m.tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(m.StateLabStop,
                                        "STOP_INVALID_FAKE_STATE_FILE"):
                m._read_state(Path(tmp) / "missing.json")

    def test_state_symlink_is_rejected(self):
        with m.tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            secret = base / "fake.json"
            secret.write_bytes(m._encode_state(m._prior_state()))
            fake = base / "state.json"
            fake.symlink_to(secret)
            with self.assertRaisesRegex(m.StateLabStop,
                                        "STOP_INVALID_FAKE_STATE_FILE"):
                m._read_state(fake)

    def test_bogus_state_destination_rejected(self):
        with m.tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "autoupdate-state.json"
            file.write_bytes(b"FAKE")
            with self.assertRaisesRegex(m.StateLabStop,
                                        "STOP_UNSAFE_FAKE_STATE_PATH"):
                m._write_state_atomic(file, b"{}")

    def test_source_contains_no_real_access_or_apply_entrypoint(self):
        source = (SCRIPTS / "v165_autoupdater_state_lab.py").read_text()
        tree = ast.parse(source)
        imports = {
            item.name.partition(".")[0]
            for n in ast.walk(tree) if isinstance(n, ast.Import)
            for item in n.names
        }
        self.assertTrue(imports.isdisjoint({
            "sqlite3", "subprocess", "socket", "requests", "urllib"
        }))
        self.assertNotIn("systemctl", source)
        for forbidden in (
            "--apply", "--deploy", "--rollback-dir", "--database",
            "--target", "--release",
        ):
            self.assertNotIn('add_argument("' + forbidden + '"', source)

    def test_only_offline_cli_executes(self):
        cmd = [sys.executable, str(SCRIPTS / "v165_autoupdater_state_lab.py")]
        result = subprocess.run(
            cmd + ["--rehearse-state-offline"], cwd=ROOT,
            capture_output=True, text=True, check=True, timeout=15
        )
        snapshot = json.loads(result.stdout)
        self.assertTrue(snapshot["fakeUpdaterStateReconciledSeparately"])
        self.assertFalse(snapshot["realAutoupdaterChanged"])
        self.assertEqual(snapshot["operationalDecision"], m.NO_GO)
        unsafe = subprocess.run(cmd + ["--apply"], cwd=ROOT,
                                capture_output=True, text=True, timeout=15)
        self.assertNotEqual(unsafe.returncode, 0)


if __name__ == "__main__":
    unittest.main()
