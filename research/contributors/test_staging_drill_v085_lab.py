# REMURA Contributors v0.85 LAB — tests NEW procedural staging drill only
import sys, unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent))
import staging_drill_v085_lab as m

class StagingDrillNewTests(unittest.TestCase):
    def all(self,state="DOCUMENTED_OFFLINE"):
        return {name:state for name in m.CHECKS}
    def check(self,ev):
        r=m.normalize(ev)
        self.assertEqual(r["stage"],"NO_GO")
        self.assertFalse(r["runtime_authorized"])
        self.assertFalse(r["actual_provider_evidence_attested"])
        self.assertFalse(r["automatic_deploy_allowed"])
        self.assertFalse(r["automatic_rollback_allowed"])
        self.assertFalse(r["automatic_retry_or_reserved_release_allowed"])
        return r
    def test_01_all_documented_still_no_go(self):
        r=self.check(self.all())
        self.assertEqual(r["documented_offline"],len(m.CHECKS))
        self.assertEqual(r["pending_manual"],[])
    def test_02_all_unknown(self):
        r=self.check(self.all("UNKNOWN"))
        self.assertEqual(len(r["pending_manual"]),len(m.CHECKS))
    def test_03_manual_pending(self):
        r=self.check(self.all("MANUAL_PROVIDER_REVIEW_PENDING"))
        self.assertEqual(r["documented_offline"],0)
    def test_04_missing_key_rejected(self):
        ev=self.all();del ev[m.CHECKS[0]]
        self.assertEqual(self.check(ev)["status"],"INVALID_OR_INCOMPLETE")
    def test_05_extra_key_rejected(self):
        ev=self.all();ev["LIVE_DEPLOY"]="YES"
        self.assertEqual(self.check(ev)["status"],"INVALID_OR_INCOMPLETE")
    def test_06_bool_rejected(self):
        ev=self.all();ev[m.CHECKS[0]]=True
        self.assertEqual(self.check(ev)["status"],"INVALID_OR_INCOMPLETE")
    def test_07_int_rejected(self):
        ev=self.all();ev[m.CHECKS[0]]=1
        self.assertEqual(self.check(ev)["status"],"INVALID_OR_INCOMPLETE")
    def test_08_invalid_state_rejected(self):
        ev=self.all();ev[m.CHECKS[0]]="APPROVED"
        self.assertEqual(self.check(ev)["status"],"INVALID_OR_INCOMPLETE")
    def test_09_non_dictionary_rejected(self):
        self.assertEqual(self.check([])["status"],"INVALID_OR_INCOMPLETE")
    def test_10_complete_rollback_dag(self):
        m.ensure_plan()
        self.assertGreaterEqual(len(m.ROLLBACK),8)
    def test_11_missing_deny_rejects_dag(self):
        bad=tuple((name,deps) for name,deps in m.ROLLBACK if name!="DENY_PRIVATE_ACCESS_POLICY")
        with patch.object(m,"ROLLBACK",bad):
            with self.assertRaises(m.DrillError):m.ensure_plan()
    def test_12_reordered_revoke_denied(self):
        bad=list(m.ROLLBACK)
        bad[1],bad[2]=bad[2],bad[1]
        with patch.object(m,"ROLLBACK",tuple(bad)):
            with self.assertRaises(m.DrillError):m.ensure_plan()
    def test_13_duplicate_rollback_rejected(self):
        with patch.object(m,"ROLLBACK",m.ROLLBACK+(m.ROLLBACK[-1],)):
            with self.assertRaises(m.DrillError):m.ensure_plan()
    def test_14_do_not_release_reserved(self):
        self.assertIn("VERIFY_NO_AUTO_RESEND_OR_RESERVED_RELEASE", self.check(self.all())["rollback_order"])
    def test_15_maintain_audit_before_owner_signoff(self):
        steps=self.check(self.all())["rollback_order"]
        self.assertLess(steps.index("PRESERVE_OWNER_AUDIT_AND_RESERVATIONS"),steps.index("OWNER_SIGNOFF_ON_RECONCILIATION"))
    def test_16_freeze_writes_before_audit(self):
        steps=self.check(self.all())["rollback_order"]
        self.assertLess(steps.index("FREEZE_D1_FIXTURE_WRITES"),steps.index("PRESERVE_OWNER_AUDIT_AND_RESERVATIONS"))
    def test_17_no_sensitive_data_in_output(self):
        r=self.check(self.all())
        s=str(r)
        for sensitive in ("@","token","account_id","SECRET_VALUE"):
            self.assertNotIn(sensitive,s)
    def test_18_safari_still_manual(self):
        ev=self.all()
        ev["SAFARI_REVOCATION_TEST_PLANNED"]="MANUAL_PROVIDER_REVIEW_PENDING"
        self.assertIn("SAFARI_REVOCATION_TEST_PLANNED",self.check(ev)["pending_manual"])
    def test_19_d1_unknown_still_blocked(self):
        ev=self.all();ev["D1_ROWS_TODAY_OBSERVED"]="UNKNOWN"
        self.assertIn("D1_ROWS_TODAY_OBSERVED",self.check(ev)["pending_manual"])
    def test_20_access_unknown_still_blocked(self):
        ev=self.all();ev["ACCESS_SEATS_OBSERVED"]="UNKNOWN"
        self.assertIn("ACCESS_SEATS_OBSERVED",self.check(ev)["pending_manual"])
    def test_21_bad_cli(self):
        self.assertEqual(m.main([]),2)
    def test_22_good_cli(self):
        self.assertEqual(m.main(["--synthetic-rehearsal"]),0)
if __name__=="__main__":unittest.main()
