# REMURA Contributors v0.94 — 16 NEW intended pilot scope scenarios only.
import copy
import unittest
from contributors_pilot_scope_v094_lab import (
    PilotScopeError, compile_pilot, model_action, review_claimed_ui,
)

OWN="fixture-owner"
A="fixture-contrib-aa"
B="fixture-contrib-bb"

def make(*contributors):
    return compile_pilot(owner_subject=OWN, contributor_subjects=list(contributors))

def allow(plan, who, action, **kwargs):
    return model_action(plan, claimed_actor=who, action=action, **kwargs)["planned_allow"]

class PilotScopeTests(unittest.TestCase):
    def test_01_one_person_pilot_generates_only_two_fixture_accounts(self):
        p=make(A)
        self.assertEqual(p["contributors"],1)
        self.assertEqual(set(p["roster"]),{OWN,A})
        self.assertFalse(p["real_pilot_allowed"])

    def test_02_two_person_pilot_stable_across_input_order(self):
        p=make(A,B)
        q=make(B,A)
        self.assertEqual(p["scope_sha256"],q["scope_sha256"])
        self.assertEqual(p["roster"],q["roster"])

    def test_03_duplicate_fixture_subject_denied(self):
        with self.assertRaisesRegex(PilotScopeError,"duplicate_identity"):
            make(A,A)

    def test_04_owner_is_separate_no_owner_as_contributor(self):
        with self.assertRaises(PilotScopeError):
            make(A,OWN)

    def test_05_no_real_email_or_access_subject_allowed(self):
        for bad in ("foo@example.org","123e4567-e89b-12d3-a456-426614174000",
                    "fixture-contrib-xx;drop", "", "fixture-admin"):
            with self.subTest(bad=bad), self.assertRaises(PilotScopeError):
                make(bad)

    def test_06_missing_or_many_contributors_deny(self):
        for values in ([],[A,B,"fixture-contrib-cc"]):
            with self.assertRaises(PilotScopeError):
                make(*values)

    def test_07_contributor_can_view_allowed_parts_and_own_levels(self):
        p=make(A)
        self.assertTrue(allow(p,A,"REMURA_READ_ALLOWED_SECTIONS"))
        self.assertTrue(allow(p,A,"READ_OWN_LEVELS",target_subject=A))

    def test_08_contributor_can_submit_and_amend_only_own(self):
        p=make(A,B)
        for act in ("SUBMIT_OWN_LEVEL","AMEND_OWN_LEVEL"):
            self.assertTrue(allow(p,A,act,target_subject=A))
            self.assertFalse(allow(p,A,act,target_subject=B))

    def test_09_no_cross_account_read_levels(self):
        p=make(A,B)
        self.assertFalse(allow(p,A,"READ_OWN_LEVELS",target_subject=B))

    def test_10_contributor_cannot_approve_or_access_owner_queue(self):
        p=make(A)
        for action in ("OWNER_REVIEW","OWNER_APPROVE_OTHERS","OWNER_QUEUE",
                       "OWNER_AUDIT_READ","APPROVE_SELF"):
            self.assertFalse(allow(p,A,action,target_subject=A))

    def test_11_owner_only_approves_other_contributor_not_self_authored(self):
        p=make(A,B)
        self.assertTrue(allow(p,OWN,"OWNER_APPROVE_OTHERS",
                              target_subject=A, approval_author_subject=A))
        self.assertFalse(allow(p,OWN,"OWNER_APPROVE_OTHERS",
                               target_subject=OWN, approval_author_subject=A))
        self.assertFalse(allow(p,OWN,"OWNER_APPROVE_OTHERS",
                               target_subject=A, approval_author_subject=OWN))

    def test_12_neither_role_gets_cot_oracle_secrets_deployment(self):
        p=make(A)
        for who in (OWN,A):
            for action in ("WRITE_COT","WRITE_ORACLE","READ_SECRETS",
                           "DEPLOY_PRODUCTION","ALTER_ACCESS_POLICY","EDIT_OTHERS_LEVELS"):
                self.assertFalse(allow(p,who,action,target_subject=who))

    def test_13_unknown_identity_and_unsupported_permission_fail_closed(self):
        p=make(A)
        self.assertFalse(allow(p,"fixture-contrib-zz","READ_OWN_LEVELS",
                               target_subject="fixture-contrib-zz"))
        out=model_action(p,claimed_actor=A,action="SUPERUSER",target_subject=A)
        self.assertEqual(out["reason"],"UNLISTED_ACTION_FAIL_CLOSED")

    def test_14_ui_claims_extra_admin_privilege_detected(self):
        p=make(A)
        out=review_claimed_ui(p,actor=A,
                 requested_actions=["REMURA_READ_ALLOWED_SECTIONS",
                                    "SUBMIT_OWN_LEVEL","OWNER_AUDIT_READ"])
        self.assertEqual(out["unapproved_ui_actions"],["OWNER_AUDIT_READ"])
        self.assertTrue(out["backend_authorization_required"])
        self.assertFalse(out["pilot_go"])

    def test_15_scope_hash_prevents_self_forged_plan_expansion(self):
        p=make(A)
        tampered=copy.deepcopy(p)
        tampered["roster"][A].append("OWNER_QUEUE")
        self.assertFalse(allow(tampered,A,"OWNER_QUEUE"))
        tampered=copy.deepcopy(p)
        tampered["scope_sha256"]="0"*64
        self.assertFalse(allow(tampered,A,"SUBMIT_OWN_LEVEL",target_subject=A))

    def test_16_planning_never_certifies_real_cloudflare_or_safari(self):
        p=make(A,B)
        for field in ("cloudflare_access_seats_verified","cloudflare_d1_quota_verified",
                      "github_actions_quota_verified","safari_login_revocation_tested",
                      "live_identity_verified","policy_installed_on_worker",
                      "real_pilot_allowed"):
            self.assertFalse(p[field],field)
        self.assertEqual(p["network_calls"],0)
        self.assertFalse(model_action(p,claimed_actor=A,action="SUBMIT_OWN_LEVEL",
                                      target_subject=A)["runtime_authorization"])

if __name__=="__main__":
    unittest.main()
