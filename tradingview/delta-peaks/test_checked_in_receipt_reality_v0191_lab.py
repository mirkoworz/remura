# REMURA TradingView v0.8.191 — 14 new real checked-in TEST inventory cases.
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import shutil
import unittest

from checked_in_receipt_reality_v0191_lab import (
    EVIDENCE,WORKFLOWS,PINNED,TV_WORKFLOWS,WORKFLOW_SNAPSHOT,
    audit_checked_in,InventoryError,
)

class RealityTests(unittest.TestCase):
    def local(self):
        temp=TemporaryDirectory(prefix="remura-v0191-")
        root=Path(temp.name)
        e=root/"evidence";w=root/"workflows"
        e.mkdir();w.mkdir()
        for name in PINNED:shutil.copyfile(EVIDENCE/name,e/name)
        shutil.copyfile(WORKFLOWS/WORKFLOW_SNAPSHOT,w/WORKFLOW_SNAPSHOT)
        return temp,e,w

    def test_01_four_actual_checked_in_test_receipts(self):
        z=audit_checked_in()
        self.assertEqual(z["status"],"VERIFIED_PINNED_HISTORICAL_TEST_METADATA_ONLY")
        self.assertEqual(z["pinned_test_receipts_read"],4)
        self.assertEqual(z["pinned_test_window_bars"],40)
        self.assertEqual([r["unique_bars"] for r in z["pinned_test_windows"]],[4,12,12,12])

    def test_02_holdout_not_certified_by_test_metadata(self):
        z=audit_checked_in()
        self.assertEqual(z["pinned_receipts_in_holdout"],0)
        self.assertLess(z["last_pinned_test_window_close_utc"],"2026-11-23T00:00:00Z")
        self.assertFalse(z["live_alpha_go"])

    def test_03_sixteen_preexisting_workflows_are_manual_not_scheduled(self):
        z=audit_checked_in()
        self.assertEqual(z["github_main_tv_workflow_names_checked"],16)
        self.assertEqual(z["workflow_dispatch_without_schedule_in_checkout"],16)
        self.assertEqual(z["workflows_with_schedule_in_checkout"],0)

    def test_04_no_cloudflare_or_provider_operational_inference(self):
        z=audit_checked_in()
        self.assertEqual(z["real_cloudflare_worker_or_alert_status"],"UNKNOWN_NOT_QUERIED")
        self.assertIsNone(z["current_cvd_capture_operational"])
        self.assertIsNone(z["full_market_m5_denominator"])
        self.assertFalse(z["provider_publication_or_first_seen_verified"])
        self.assertEqual(z["cloudflare_api_calls"],0)

    def test_05_only_test_scope_with_no_independent_receipts(self):
        z=audit_checked_in()
        self.assertTrue(all(x["source_is_test"] for x in z["pinned_test_windows"]))
        self.assertTrue(all(not x["external_first_seen_verified"] for x in z["pinned_test_windows"]))
        self.assertTrue(z["historical_test_not_promoted_to_holdout"])

    def test_06_one_real_metadata_byte_altered_quarantines(self):
        t,e,w=self.local()
        try:
            p=e/"fx_second_receipt_20261116.json"
            p.write_bytes(p.read_bytes()+b" ")
            z=audit_checked_in(evidence_dir=e,workflow_dir=w)
            self.assertEqual(z["status"],"QUARANTINE_SOURCE_OR_WORKFLOW_DRIFT")
            self.assertTrue(any("fx_second" in x for x in z["issues"]))
        finally:t.cleanup()

    def test_07_deleted_receipt_cannot_appear_as_empty_window(self):
        t,e,w=self.local()
        try:
            (e/"fx_first_receipt_20261116.json").unlink()
            z=audit_checked_in(evidence_dir=e,workflow_dir=w)
            self.assertEqual(z["pinned_test_receipts_read"],3)
            self.assertIsNone(z["pinned_receipts_in_holdout"])
        finally:t.cleanup()

    def test_08_workflow_schedule_change_stays_unverified_not_auto_enabled(self):
        t,e,w=self.local()
        try:
            f=w/WORKFLOW_SNAPSHOT
            data=json.loads(f.read_text())
            data["entries"][0]["schedule"]=True
            f.write_text(json.dumps(data))
            z=audit_checked_in(evidence_dir=e,workflow_dir=w)
            self.assertEqual(z["workflows_with_schedule_in_checkout"],1)
            self.assertFalse(z["live_alpha_go"])
            self.assertIn("schedule_present_in_snapshot_requires_external_review",z["issues"])
        finally:t.cleanup()

    def test_09_workflow_removed_is_unknown_not_assumed_manual(self):
        t,e,w=self.local()
        try:
            (w/WORKFLOW_SNAPSHOT).unlink()
            z=audit_checked_in(evidence_dir=e,workflow_dir=w)
            self.assertEqual(z["workflows_unknown_in_checkout"],len(TV_WORKFLOWS))
            self.assertEqual(z["status"],"QUARANTINE_SOURCE_OR_WORKFLOW_DRIFT")
        finally:t.cleanup()

    def test_10_symlink_receipt_denied(self):
        t,e,w=self.local()
        try:
            f=e/"fx_first_receipt_20261116.json"
            dst=e/"safe_copy.json"
            shutil.copyfile(f,dst)
            f.unlink()
            f.symlink_to(dst)
            z=audit_checked_in(evidence_dir=e,workflow_dir=w)
            self.assertEqual(z["status"],"QUARANTINE_SOURCE_OR_WORKFLOW_DRIFT")
        finally:t.cleanup()

    def test_11_evidence_folder_is_not_proof_of_whole_market(self):
        z=audit_checked_in()
        self.assertTrue(z["pinned_receipts_outside_test_files_not_inspected"])
        self.assertFalse(z["evidence_independently_attested"])

    def test_12_wrong_path_type_is_denied_before_read(self):
        with self.assertRaisesRegex(InventoryError,"path_object_required"):
            audit_checked_in(evidence_dir="/tmp/something")

    def test_13_no_source_data_or_tokens_returned(self):
        z=audit_checked_in()
        self.assertEqual(z["d1_calls"],0)
        self.assertFalse(z["secrets_used"])
        self.assertFalse(z["deploy_performed"])
        self.assertTrue(all(set(row)=={"filename","run_id","window_start_utc",
            "window_end_utc","source_is_test","requested_slots","unique_bars",
            "missing_slots_in_requested_window","external_first_seen_verified"}
            for row in z["pinned_test_windows"]))

    def test_14_pinned_git_hash_proves_consistency_only_not_publication(self):
        z=audit_checked_in()
        self.assertEqual(z["issues"],[])
        self.assertEqual(z["next_action"],
            "OBTAIN_AUTHORIZED_REAL_PROSPECTIVE_CAPTURE_AND_INDEPENDENT_RECEIPT")
        self.assertFalse(z["live_alpha_go"])
        self.assertFalse(z["evidence_independently_attested"])

if __name__=="__main__":
    unittest.main()
