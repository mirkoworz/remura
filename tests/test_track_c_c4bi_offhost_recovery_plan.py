"""C4b(i) tests: fictional sizes and provider quotas, never real backups."""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import track_c_c4bi_offhost_recovery_plan as m

GB=m.GB
DB=120*m.MB


def target(provider, free=None, used=None, planned=None):
    return {
        "provider":provider,
        "declaredFreeBytes":free,
        "declaredUsedMonthlyRequests":used,
        "plannedAdditionalMonthlyRequests":planned,
    }


def oracle(free=8*GB, used=100, planned=60):
    return target("OCI_STANDARD_OBJECT_STORAGE",free,used,planned)


def drive(free=11*GB):
    return target("GOOGLE_DRIVE_PERSONAL",free)


class FreeFirstOfflinePlan(unittest.TestCase):
    def check(self, source=DB, generations=3, targets=None, **override):
        kwargs=dict(source_bytes=source,generations=generations,
                    targets=[oracle(),drive()] if targets is None else targets,
                    mode=m.MODE)
        kwargs.update(override)
        return m.assess(**kwargs)

    def test_oci_trial_standard_is_10gb_conservative_not_20gb(self):
        out=self.check()
        self.assertEqual(out["offhostTargets"][0]["planningReferenceMaximumBytes"],
                         10*GB)
        self.assertEqual(m.OCI_OBJECT_COMBINED_POST_TRIAL,20*GB)
        self.assertEqual(m.OCI_REQUEST_FREE_REFERENCE,50000)

    def test_google_15gb_shared_is_only_theoretical_cap(self):
        out=self.check()
        self.assertEqual(out["offhostTargets"][1]["planningReferenceMaximumBytes"],
                         15*GB)
        self.assertFalse(out["cloudBillingAndQuotasVerified"])

    def test_two_provider_proposal_not_recovery_proof(self):
        out=self.check()
        self.assertTrue(out["desiredProvidersPresent"])
        self.assertFalse(out["independentAccountsVerified"])
        self.assertFalse(out["encryptedBackupActuallyCreated"])
        self.assertFalse(out["isolatedRestoreTestPassed"])
        self.assertEqual(out["operationalDecision"],m.NO_GO)

    def test_estimate_is_larger_than_plaintext_and_multiplies_copies(self):
        out=self.check()
        self.assertGreater(out["estimatedPerGenerationBytes"],DB)
        self.assertEqual(out["offhostTargets"][0]["estimatedBytesForAllGenerations"],
                         out["estimatedPerGenerationBytes"]*3)

    def test_even_plausible_space_and_requests_are_not_billing_proof(self):
        out=self.check()
        o=out["offhostTargets"][0]
        self.assertEqual(o["declaredSpaceAssessment"],
                         "PLAUSIBLE_DECLARED_CAPACITY_NOT_VERIFIED")
        self.assertEqual(o["requestAssessment"],
                         "PLAUSIBLE_DECLARED_REQUEST_MARGIN_NOT_VERIFIED")
        self.assertFalse(o["freeOfChargeForThisAccountVerified"])

    def test_unsupported_duplicate_provider_rejected(self):
        with self.assertRaisesRegex(ValueError,"unknown_or_duplicate"):
            self.check(targets=[oracle(),oracle()])
        with self.assertRaisesRegex(ValueError,"unknown_or_duplicate"):
            self.check(targets=[target("GITHUB_ARTIFACTS")])

    def test_zero_and_negative_source_size_rejected(self):
        for size in (0,-1,True,"500",m.MAX_SOURCE_DB_BYTES+1):
            with self.subTest(size=size):
                with self.assertRaisesRegex(ValueError,"strict_bounded"):
                    self.check(source=size)

    def test_unknown_source_size_not_zero_or_approved(self):
        x=self.check(source=None)
        self.assertEqual(x["status"],"UNKNOWN_REAL_SQLITE_SIZE_NOT_MEASURED")
        self.assertIsNone(x["estimatedPerGenerationBytes"])
        self.assertEqual(x["offhostTargets"][0]["declaredSpaceAssessment"],
                         "UNKNOWN_SOURCE_BACKUP_SIZE")

    def test_unknown_free_space_not_assumed_available(self):
        x=self.check(targets=[oracle(free=None)])
        self.assertEqual(x["offhostTargets"][0]["declaredSpaceAssessment"],
                         "UNKNOWN_ACCOUNT_FREE_SPACE")

    def test_pressure_reserve_blocks_large_snapshot(self):
        x=self.check(source=3*GB,generations=3,targets=[oracle()])
        self.assertEqual(x["offhostTargets"][0]["declaredSpaceAssessment"],
                         "INSUFFICIENT_DECLARED_HEADROOM_OR_RESERVE")

    def test_full_google_storage_blocks_as_shared_quota(self):
        x=self.check(targets=[drive(free=0)])
        self.assertEqual(x["offhostTargets"][0]["declaredSpaceAssessment"],
                         "INSUFFICIENT_DECLARED_HEADROOM_OR_RESERVE")

    def test_exceeding_80_percent_oci_request_margin_blocks(self):
        x=self.check(targets=[oracle(used=39000,planned=1200)])
        self.assertEqual(x["offhostTargets"][0]["requestAssessment"],
                         "DECLARED_REQUEST_MARGIN_INSUFFICIENT")

    def test_unknown_oci_requests_stays_unknown(self):
        x=self.check(targets=[oracle(used=None,planned=None)])
        self.assertEqual(x["offhostTargets"][0]["requestAssessment"],
                         "UNKNOWN_OCI_REQUEST_USAGE")

    def test_drive_api_request_quota_not_invented(self):
        x=self.check(targets=[drive()])
        self.assertEqual(x["offhostTargets"][0]["requestAssessment"],
                         "GOOGLE_API_USAGE_NOT_AUDITED")
        with self.assertRaisesRegex(ValueError,"drive_request_quota_not_modelled"):
            self.check(targets=[drive()|{"plannedAdditionalMonthlyRequests":0}])

    def test_credentials_or_paths_as_fields_rejected_and_not_echoed(self):
        row=oracle()
        row["accessKey"]="NEVER_EXPOSE"
        with self.assertRaisesRegex(ValueError,"strict_targets"):
            self.check(targets=[row])

    def test_unreasonable_generation_limit_and_target_count_rejected(self):
        for num in (0,-1,6,True):
            with self.subTest(num=num):
                with self.assertRaisesRegex(ValueError,"strict_bounded"):
                    self.check(generations=num)
        with self.assertRaisesRegex(ValueError,"bounded_offhost"):
            self.check(targets=[oracle(),drive(),oracle()])

    def test_default_requires_explicit_offline_mode(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            m.assess(source_bytes=DB,generations=2,targets=[])

    def test_missing_target_is_not_zero_cost_green_light(self):
        x=self.check(targets=[])
        self.assertEqual(x["status"],"UNKNOWN_NO_OFFHOST_TARGET_DECLARED")
        self.assertFalse(x["desiredProvidersPresent"])
        self.assertEqual(x["operationalDecision"],m.NO_GO)

    def test_runbook_requires_encryption_key_separate_and_offhost_restore(self):
        x=self.check()
        requirements=x["requiredRecoveryEvidence"]
        self.assertIn("AEAD_ENCRYPT_BEFORE_NETWORK_TRANSFER",requirements)
        self.assertIn("DECRYPTION_KEY_RECOVERABLE_OUTSIDE_VPS_AND_PROVIDER",requirements)
        self.assertIn("ISOLATED_DECRYPT_AND_SQLITE_RESTORE_TEST",requirements)
        self.assertIn("INDEPENDENT_FAILURE_DOMAIN_SECOND_COPY",requirements)

    def test_static_no_file_network_or_process_imports_and_no_live_wiring(self):
        file=ROOT/"scripts"/"track_c_c4bi_offhost_recovery_plan.py"
        ast_tree=ast.parse(file.read_text())
        imported={alias.name for node in ast.walk(ast_tree)
                  if isinstance(node,ast.Import) for alias in node.names}
        self.assertTrue({"os","pathlib","sqlite3","socket","requests","subprocess",
                         "urllib","cryptography","boto3"}.isdisjoint(imported))
        for live in ("private_server.py","resource_monitor.py",
                     "price_store.py","signals_monitor.py","cot_monitor.py"):
            self.assertNotIn("track_c_c4bi_offhost_recovery_plan",
                             (ROOT/"scripts"/live).read_text())

    def test_never_claim_new_resources_and_calls(self):
        x=self.check()
        self.assertEqual(x["newProviderCalls"],0)
        self.assertEqual(x["newCloudResources"],0)
        self.assertEqual(x["newVpsRequests"],0)
        self.assertEqual(x["operationalDecision"],m.NO_GO)

if __name__=="__main__":
    unittest.main()
