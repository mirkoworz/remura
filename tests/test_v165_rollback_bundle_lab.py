"""Offline v1.65 persisted rollback bundle, 12 existing + 2 new fake files."""
from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "deploy/oracle"
sys.path.insert(0, str(ORACLE))
import v165_rollback_bundle_lab as m


class V165RollbackBundleLabTests(unittest.TestCase):
    def report(self, fault=None):
        return m.rehearse(mode=m.MODE, fault=fault)

    def test_full_fake_disk_seal_and_recovery(self):
        r = self.report()
        self.assertEqual(r["state"], "SYNTHETIC_ROLLBACK_CHECKED")
        self.assertTrue(r["syntheticBundlePersistedAndSealed"])
        self.assertTrue(r["syntheticRollbackAttempted"])
        self.assertTrue(r["syntheticRollbackComplete"])
        self.assertTrue(r["fakeNewModulesAbsentAfterRecovery"])
        self.assertTrue(r["temporaryFixtureErasedAtExit"])

    def test_no_go_and_no_live_proofs(self):
        r = self.report()
        for name in ("trustedSealIndependentOfFixture",
                     "liveInstalledVersionAttested", "realSqliteOpened",
                     "offhostBackupVerified", "liveFilesModified",
                     "realAutoupdaterReconciled", "realServerAccessed",
                     "releaseAuthorized", "researchC5Enabled"):
            self.assertFalse(r[name], name)
        self.assertEqual(r["operationalDecision"], m.NO_GO)

    def test_manifest_exact_12_preexisting_2_new(self):
        old, next_ = m._fixtures()
        record = m._manifest(old, next_)
        self.assertEqual(len(old), 12)
        self.assertEqual(len(next_), 14)
        self.assertEqual(set(record["files"]), m.protocol.FILE_SET)
        self.assertEqual(sum(v["kind"] == "new" for v in record["files"].values()), 2)
        for name in m.protocol.NEW_FILES:
            self.assertIsNone(record["files"][name]["oldSha256"])

    def test_no_unknown_path_in_manifest(self):
        with self.assertRaisesRegex(m.LabStop, "STOP_PATH_NOT_ALLOWLISTED"):
            m._path(Path("any"), "private/remura-prices.sqlite3")
        with self.assertRaisesRegex(m.LabStop, "STOP_PATH_NOT_ALLOWLISTED"):
            m._path(Path("any"), "../secrets")

    def test_halt_after_seal_keeps_originals_and_no_recovery_claim(self):
        r = self.report("after_seal")
        self.assertEqual(r["state"], "SYNTHETIC_STOPPED_BEFORE_INSTALL")
        self.assertFalse(r["syntheticRollbackAttempted"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_mid_install_fault_rolls_back_persisted_originals(self):
        r = self.report("mid_install")
        self.assertTrue(r["syntheticRollbackComplete"])
        self.assertTrue(r["fakeNewModulesAbsentAfterRecovery"])

    def test_after_install_fault_restores_old_and_removes_both_new(self):
        r = self.report("after_install")
        self.assertTrue(r["syntheticRollbackComplete"])
        self.assertTrue(r["fakeNewModulesAbsentAfterRecovery"])

    def test_interrupted_rollback_is_retried_idempotently(self):
        r = self.report("during_rollback")
        self.assertTrue(r["syntheticInterruptedRollbackRetried"])
        self.assertTrue(r["syntheticRollbackComplete"])

    def test_manifest_corruption_fail_closed(self):
        r = self.report("corrupt_manifest")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_backup_hash_corruption_fail_closed(self):
        r = self.report("corrupt_backup")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_symlink_in_backup_rejected(self):
        r = self.report("symlink_backup")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_unreviewed_extra_backup_file_rejected(self):
        r = self.report("unexpected_backup")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_live_fake_file_tampering_rejected_before_rollback(self):
        r = self.report("tamper_installed")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_live_fake_symlink_rejected_before_rollback(self):
        r = self.report("symlink_installed")
        self.assertTrue(r["syntheticTamperRejected"])
        self.assertFalse(r["syntheticRollbackComplete"])

    def test_unknown_fault_rejected(self):
        with self.assertRaisesRegex(m.LabStop, "STOP_UNKNOWN_FAULT"):
            self.report("turn_on_live")

    def test_wrong_or_missing_mode_rejected(self):
        for value in ("LIVE", None, True, "", "OFFLINE"):
            with self.subTest(mode=value):
                with self.assertRaisesRegex(m.LabStop, "STOP_OFFLINE_MODE_REQUIRED"):
                    m.rehearse(mode=value)

    def test_bounded_read_refuses_empty_and_oversize(self):
        with m.tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fake.txt"
            path.write_bytes(b"")
            with self.assertRaisesRegex(m.LabStop, "STOP_UNSAFE_OR_OVERSIZED_FILE"):
                m._regular_bytes(path)
            path.write_bytes(b"x" * (m.MAX_BYTES+1))
            with self.assertRaisesRegex(m.LabStop, "STOP_UNSAFE_OR_OVERSIZED_FILE"):
                m._regular_bytes(path)

    def test_seal_rejects_missing_or_changed_trusted_digest(self):
        old, new = m._fixtures()
        with m.tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            bundle, digest = m._seal(base, old, new)
            self.assertTrue(m._verify_bundle(bundle, digest, old, new))
            with self.assertRaisesRegex(m.LabStop, "STOP_MANIFEST_CHANGED"):
                m._verify_bundle(bundle, "f"*64, old, new)

    def test_extra_snapshot_file_detected(self):
        old, new = m._fixtures()
        with m.tempfile.TemporaryDirectory() as tmp:
            base=Path(tmp)
            bundle,digest=m._seal(base, old, new)
            m._write_new(bundle/"extra", b"FAKE")
            with self.assertRaisesRegex(m.LabStop, "STOP_BUNDLE_EXTRA_OR_MISSING"):
                m._verify_bundle(bundle,digest,old,new)

    def test_manifest_schema_must_match_synthetic(self):
        old, new = m._fixtures()
        manifest = m._manifest(old,new)
        self.assertEqual(manifest["schema"], m.SCHEMA)
        self.assertFalse(manifest["liveAttested"])
        self.assertFalse(manifest["releaseAuthorized"])
        self.assertEqual(manifest["fixture"],m.MODE)

    def test_source_does_not_import_live_control_modules(self):
        source=(ORACLE/"v165_rollback_bundle_lab.py").read_text()
        parsed=ast.parse(source)
        imports={x.name.partition(".")[0] for n in ast.walk(parsed)
                 if isinstance(n,ast.Import) for x in n.names}
        self.assertTrue(imports.isdisjoint(
            {"subprocess","sqlite3","socket","urllib","requests"}))
        self.assertNotIn("systemctl",source)
        for flag in ("--apply", "--deploy", "--rollback-dir", "--database",
                     "--target", "--release"):
            self.assertNotIn('add_argument("'+flag+'"',source)

    def test_only_offline_cli_runs_and_legacy_commands_fail(self):
        args=[sys.executable,str(ORACLE/"v165_rollback_bundle_lab.py")]
        p=subprocess.run(args+["--rehearse-fixture-offline"],cwd=ROOT,
                         capture_output=True,text=True,timeout=15,check=True)
        record=json.loads(p.stdout)
        self.assertTrue(record["syntheticRollbackComplete"])
        self.assertEqual(record["operationalDecision"],m.NO_GO)
        p=subprocess.run(args+["--apply"],cwd=ROOT,capture_output=True,
                         text=True,timeout=15)
        self.assertNotEqual(p.returncode,0)


if __name__ == "__main__":
    unittest.main()
