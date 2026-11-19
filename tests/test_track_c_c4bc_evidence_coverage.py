"""C4b(c): provenance completeness is not proof; no network, VPS or APIs."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import track_c_c4bc_evidence_coverage as gate

NOW = datetime(2026, 11, 8, 12, 0, tzinfo=timezone.utc)


def utc(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def record(key, *, kind="REDACTED_EXTERNAL_UNATTESTED", when=NOW, ident=None):
    return {"gate": key, "sourceType": gate.GATES[key][0],
            "evidenceClass": kind, "capturedAtUtc": utc(when),
            "evidenceId": ident or ("TEST_" + key)}


class TestOfflineCoverage(unittest.TestCase):
    def check(self, rows=(), **kwargs):
        return gate.coverage(rows, evaluated_at_utc=utc(NOW), mode=gate.MODE,
                             **kwargs)

    def test_missing_evidence_does_not_mean_zero_consumption(self):
        result = self.check([])
        self.assertEqual(result["requiredGateCount"], 8)
        self.assertEqual(result["submittedForHumanReview"], 0)
        self.assertEqual(len(result["missingOrStaleOrLabGates"]), 8)
        self.assertEqual(result["gateStates"]["OCI_PLAN_BILLING"], "MISSING")
        self.assertFalse(result["cloudBillingVerified"])
        self.assertEqual(result["operationalDecision"], gate.NO_GO)

    def test_historical_oci_report_not_current_billing(self):
        result = self.check([record("OCI_PLAN_BILLING",
                                    kind="HISTORICAL_DOCUMENT",
                                    when=NOW-timedelta(days=1))])
        self.assertEqual(result["gateStates"]["OCI_PLAN_BILLING"],
                         "HISTORICAL_OR_STALE")
        self.assertFalse(result["cloudBillingVerified"])

    def test_even_recent_lab_restore_not_offhost_restore(self):
        result = self.check([record("OFFHOST_RESTORE", kind="SYNTHETIC_LAB")])
        self.assertEqual(result["gateStates"]["OFFHOST_RESTORE"],
                         "LAB_ONLY_NOT_OPERATIONAL_PROOF")
        self.assertFalse(result["offhostRestoreVerified"])

    def test_fresh_user_supplied_report_requires_manual_attestation(self):
        result = self.check([record("VPS_RESOURCES")])
        self.assertEqual(result["gateStates"]["VPS_RESOURCES"],
                         "SUBMITTED_EXTERNAL_NOT_INDEPENDENTLY_ATTESTED")
        self.assertFalse(result["realVpsResourceHeadroomVerified"])
        self.assertEqual(result["submittedForHumanReview"], 1)

    def test_expired_freshness_degrades_to_historical(self):
        result = self.check([record("VPS_RESOURCES",
                                    when=NOW-timedelta(minutes=11))])
        self.assertEqual(result["gateStates"]["VPS_RESOURCES"], "HISTORICAL_OR_STALE")

    def test_earliest_qualifying_utc_limit_is_inclusive(self):
        result = self.check([record("VPS_RESOURCES",
                                    when=NOW-timedelta(minutes=10))])
        self.assertEqual(result["submittedForHumanReview"], 1)

    def test_duplicates_cannot_falsely_raise_confidence(self):
        row = record("SQLITE_WAL_INVENTORY")
        result = self.check([row,dict(row,evidenceId="TEST_SECOND")])
        self.assertEqual(result["gateStates"]["SQLITE_WAL_INVENTORY"],
                         "CONFLICT_DUPLICATE_NOT_ATTESTED")
        self.assertIn("SQLITE_WAL_INVENTORY", result["missingOrStaleOrLabGates"])

    def test_future_or_non_utc_is_not_recorded(self):
        rows = [record("GITHUB_USAGE", when=NOW+timedelta(seconds=1))]
        bad = record("FIRESTORE_USAGE")
        bad["capturedAtUtc"] = "2026-11-08T13:00:00+01:00"
        rows.append(bad)
        result = self.check(rows)
        self.assertEqual(result["invalidRecords"], 2)
        self.assertEqual(result["submittedForHumanReview"], 0)

    def test_unexpected_fields_and_secrets_are_safely_rejected(self):
        bad = record("VPS_RESOURCES")
        bad["apiToken"] = "DO_NOT_ECHO_ANYWHERE"
        result = self.check([bad])
        self.assertEqual(result["invalidRecords"], 1)
        self.assertNotIn("DO_NOT_ECHO_ANYWHERE", repr(result))
        self.assertEqual(result["gateStates"]["VPS_RESOURCES"], "MISSING")

    def test_unknown_source_and_forged_verified_status_are_rejected(self):
        bad = record("OCI_PLAN_BILLING")
        bad["sourceType"] = "GITHUB_ACTIONS_GREEN"
        another = record("OFFHOST_RESTORE")
        another["evidenceClass"] = "VERIFIED_LIVE"
        out = self.check([bad,another])
        self.assertEqual(out["invalidRecords"], 2)
        self.assertFalse(out["offhostRestoreVerified"])

    def test_all_fresh_submissions_never_authorize_live(self):
        records = [record(k) for k in gate.GATES]
        result = self.check(records)
        self.assertEqual(result["submittedForHumanReview"], len(gate.GATES))
        self.assertEqual(result["missingOrStaleOrLabGates"], ())
        self.assertFalse(result["allEvidenceIndependentlyAuthenticated"])
        self.assertFalse(result["liveResearchKillSwitchVerified"])
        self.assertFalse(result["institutionalFirstSeenVerified"])
        self.assertEqual(result["operationalDecision"], gate.NO_GO)

    def test_mode_and_batch_boundaries(self):
        with self.assertRaisesRegex(ValueError, "explicit_offline"):
            gate.coverage([], evaluated_at_utc=utc(NOW))
        with self.assertRaisesRegex(ValueError, "bounded_redacted"):
            self.check([record("VPS_RESOURCES")] * 25)

    def test_flags_prove_no_new_vps_or_provider_calls(self):
        result = self.check([record("PROVIDER_FIRST_SEEN",
                                    kind="HISTORICAL_DOCUMENT")])
        self.assertEqual(result["newVpsRequests"], 0)
        self.assertEqual(result["newProviderCalls"], 0)
        self.assertFalse(result["institutionalFirstSeenVerified"])
        self.assertEqual(result["operationalDecision"], gate.NO_GO)

if __name__ == "__main__":
    unittest.main()
