# REMURA v0.82 LAB — NEW gating matrix tests only
from pathlib import Path
import sys, unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import staging_gate_matrix_v082_lab as m
class MatrixNewTests(unittest.TestCase):
    def test_01_unknown_all(self):
        o=m.check_matrix({})
        self.assertEqual(o["decision"],"NO_GO")
        self.assertEqual(len(o["unknown_gates"]),len(m.GATES))
    def test_02_complete_lab_never_deploy(self):
        o=m.check_matrix({k:"LAB_ONLY" for k in m.GATES})
        self.assertFalse(o["automatic_deploy_allowed"])
        self.assertFalse(o["provider_attested"])
        self.assertEqual(o["decision"],"NO_GO")
    def test_03_all_manual_review_still_no_go(self):
        o=m.check_matrix({k:"MANUAL_REVIEW_REQUIRED" for k in m.GATES})
        self.assertEqual(o["decision"],"NO_GO")
    def test_04_extra_gate(self):
        x={k:"LAB_ONLY" for k in m.GATES};x["DEPLOY"]="YES"
        self.assertIn("MISSING_OR_EXTRA_GATES",m.check_matrix(x)["reasons"])
    def test_05_bool_state(self):
        x={k:"LAB_ONLY" for k in m.GATES};x["CF_FREE_PLAN"]=True
        self.assertIn("INVALID_GATE_STATE",m.check_matrix(x)["reasons"])
    def test_06_role_min_permissions(self):
        self.assertNotIn("write_other_member_levels",m.ROLE_ACTIONS["CONTRIBUTOR"])
        self.assertNotIn("auto_approve",m.ROLE_ACTIONS["OWNER"])
    def test_07_no_reservation_release(self):
        self.assertIn("release_reserved_automatically",m.DENIED_ACTIONS)
        self.assertIn("auto_retry_lost_response",m.DENIED_ACTIONS)
    def test_08_owner_intake_separate(self):
        self.assertIn("review_amendments",m.ROLE_ACTIONS["OWNER"])
        self.assertIn("review_proposed_levels",m.ROLE_ACTIONS["OWNER"])
    def test_09_manifest_match(self):
        self.assertEqual(m.check_matrix({k:"UNKNOWN" for k in m.GATES})["route_manifest"],"SOURCE_LOCK_MATCH")
    def test_10_manifest_unchecked(self):
        self.assertIn("ROUTE_MANIFEST_NOT_CHECKED",m.check_matrix({},verify_routes=False)["reasons"])
    def test_11_manifest_drift_fail_closed(self):
        with patch.object(m,"review",side_effect=m.ManifestError("x")):
            result=m.check_matrix({})
        self.assertEqual(result["route_manifest"],"DRIFT")
    def test_12_zero_private_labels(self):
        result=str(m.check_matrix({k:"UNKNOWN" for k in m.GATES}))
        self.assertNotIn("@",result)
        self.assertNotIn("account_id",result)
    def test_13_bad_cli(self):
        self.assertEqual(m.main([]),2)
    def test_14_readonly_cli(self):
        self.assertEqual(m.main(["--offline-review"]),0)
