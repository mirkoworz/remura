"""C4b(j): 18 offline tests with FICTIONAL sqlite, key, simulated remote."""
from __future__ import annotations
import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import track_c_c4bj_synthetic_recovery as lab


class SyntheticEncryptedRestore(unittest.TestCase):
    def run_lab(self, fault="none"):
        return lab.rehearse(mode=lab.MODE, fault=fault)

    def test_success_wal_consistent_encryption_loss_and_restore(self):
        r = self.run_lab()
        self.assertEqual(r["state"], "SYNTHETIC_AESGCM_RESTORE_REHEARSAL_PASS_ONLY")
        for key in ("sqliteOnlineBackupRehearsed",
                    "aes256GcmAuthenticatedEncryptionRehearsed",
                    "ciphertextCopiedToSeparateLabDirectory",
                    "syntheticSourceDeletedBeforeRestore",
                    "restoredSqliteIntegrityCheck",
                    "restoredSyntheticFixtureVerified"):
            with self.subTest(key=key):
                self.assertTrue(r[key])

    def test_remote_payload_tamper_detected(self):
        r = self.run_lab("tamper_ciphertext")
        self.assertEqual(r["state"], "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")
        self.assertTrue(r["tamperOrWrongKeyRejected"])

    def test_gcm_tag_detects_rehashed_ciphertext_tamper(self):
        r = self.run_lab("tamper_rehashed_ciphertext")
        self.assertEqual(r["state"], "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")
        self.assertTrue(r["tamperOrWrongKeyRejected"])

    def test_wrong_key_detected_by_aead(self):
        self.assertEqual(self.run_lab("wrong_key")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_truncated_remote_detected(self):
        self.assertEqual(self.run_lab("truncate_ciphertext")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_remote_object_missing_detected(self):
        self.assertEqual(self.run_lab("missing_offhost")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_unrecognized_header_detected(self):
        self.assertEqual(self.run_lab("malformed_header")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_rehashed_header_detected(self):
        self.assertEqual(self.run_lab("header_rehashed")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_remote_checksum_tamper_detected(self):
        self.assertEqual(self.run_lab("tamper_digest")["state"],
                         "SYNTHETIC_FAULT_REJECTED_FAIL_CLOSED")

    def test_no_mode_no_execution(self):
        with self.assertRaisesRegex(ValueError, "explicit_synthetic_lab"):
            lab.rehearse()

    def test_invalid_mode_and_fault_rejected(self):
        with self.assertRaisesRegex(ValueError, "explicit_synthetic_lab"):
            lab.rehearse(mode="LIVE")
        with self.assertRaisesRegex(ValueError, "unknown_synthetic_fault"):
            lab.rehearse(mode=lab.MODE, fault="upload_production")

    def test_success_is_not_actual_production_recovery(self):
        r = self.run_lab()
        for flag in ("realOffhostProviderUsed", "realIndependentFailureDomainVerified",
                     "realExternalKeyRecoveryVerified", "realVpsDataAccessed",
                     "actualEncryptedBackupCreated", "actualOperationalRestoreVerified",
                     "productionSizeAndCostAssessed",
                     "productionEncryptionStreamingSafeVerified"):
            with self.subTest(flag=flag):
                self.assertFalse(r[flag])
        self.assertEqual(r["operationalDecision"], lab.NO_GO)

    def test_mock_remote_not_independent_host(self):
        r = self.run_lab()
        self.assertTrue(r["ciphertextCopiedToSeparateLabDirectory"])
        self.assertFalse(r["realIndependentFailureDomainVerified"])

    def test_returned_result_has_only_allowed_fields_no_secret(self):
        r = self.run_lab()
        self.assertTrue(set(r) <= {
            "schema", "state", "sqliteOnlineBackupRehearsed",
            "aes256GcmAuthenticatedEncryptionRehearsed",
            "ciphertextCopiedToSeparateLabDirectory",
            "syntheticSourceDeletedBeforeRestore", "restoredSqliteIntegrityCheck",
            "restoredSyntheticFixtureVerified", "tamperOrWrongKeyRejected",
            "realOffhostProviderUsed", "realIndependentFailureDomainVerified",
            "realExternalKeyRecoveryVerified", "realVpsDataAccessed",
            "actualEncryptedBackupCreated", "actualOperationalRestoreVerified",
            "productionSizeAndCostAssessed",
            "productionEncryptionStreamingSafeVerified",
            "operationalDecision", "newProviderCalls", "newVpsRequests",
        })
        self.assertNotIn("/opt/remura", repr(r))
        self.assertTrue(all(type(x) in (str, bool, int) for x in r.values()))

    def test_not_called_from_any_running_live_module(self):
        self.assertEqual(self.run_lab()["newProviderCalls"], 0)
        for name in ("private_server.py", "resource_monitor.py", "price_store.py",
                     "signals_monitor.py", "cot_monitor.py"):
            path = ROOT / "scripts" / name
            self.assertNotIn("track_c_c4bj_synthetic_recovery", path.read_text())

    def test_no_network_or_external_path_parameters(self):
        source = (ROOT/"scripts"/"track_c_c4bj_synthetic_recovery.py").read_text()
        tree = ast.parse(source)
        imported = {a.name for node in ast.walk(tree)
                    if isinstance(node, ast.Import) for a in node.names}
        self.assertTrue({"requests", "urllib", "http", "boto3", "google", "oci",
                         "socket", "subprocess"}.isdisjoint(imported))
        self.assertNotIn("/opt/remura/private", source)
        self.assertIn("tempfile.TemporaryDirectory", source)
        self.assertIn("AESGCM.generate_key", source)

    def test_all_faults_keep_c5_disabled(self):
        for fault in sorted(lab.FAULTS):
            with self.subTest(fault=fault):
                r = self.run_lab(fault)
                self.assertEqual(r["operationalDecision"], lab.NO_GO)
                self.assertFalse(r["actualOperationalRestoreVerified"])

    def test_ephemeral_key_not_claimed_recoverable(self):
        r = self.run_lab()
        self.assertEqual(r["state"], "SYNTHETIC_AESGCM_RESTORE_REHEARSAL_PASS_ONLY")
        self.assertFalse(r["realExternalKeyRecoveryVerified"])

if __name__ == "__main__":
    unittest.main()
