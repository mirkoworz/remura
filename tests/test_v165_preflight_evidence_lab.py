"""Strict offline v1.65 private-evidence capture PLAN, no true receipts."""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "deploy" / "oracle"
sys.path.insert(0, str(DIR))
import v165_preflight_evidence_lab as m


class EvidencePlanLabTests(unittest.TestCase):
    def test_plan_exactly_tracks_all_twelve_incident_evidence_gates(self):
        self.assertTrue(m.validate_plan())
        self.assertEqual(tuple(x[0] for x in m.GATES),
                         m.incident.REQUIRED_LIVE_EVIDENCE)
        self.assertEqual(len(m.GATES), 12)

    def test_empty_plan_all_real_evidence_missing(self):
        report = m.plan()
        self.assertEqual(report["gateCount"], 12)
        self.assertEqual(report["missingRealEvidenceCount"], 12)
        self.assertEqual(report["syntheticReceiptCount"], 0)
        self.assertEqual(report["operationalDecision"], m.NO_GO)

    def test_even_all_mock_receipts_never_prove_any_live_gate(self):
        rows = m.fixtures(simulated_gates=m.incident.REQUIRED_LIVE_EVIDENCE)
        report = m.evaluate_only_fixture_rows(rows)
        self.assertEqual(report["syntheticReceiptCount"], 12)
        self.assertEqual(report["missingRealEvidenceCount"], 12)
        self.assertTrue(all(x["actualRealEvidenceState"] == "NOT_ATTESTED"
                            for x in report["gates"]))
        self.assertEqual(report["operationalDecision"], m.NO_GO)

    def test_mock_one_gate_keeps_all_real_missing(self):
        report=m.evaluate_only_fixture_rows(m.fixtures(
            simulated_gates=(m.GATES[0][0],)))
        self.assertEqual(report["syntheticReceiptCount"], 1)
        self.assertEqual(report["missingRealEvidenceCount"], 12)

    def test_capture_roles_are_explicit_and_not_conflated(self):
        kinds={x[0]:x[1] for x in m.GATES}
        self.assertEqual(kinds["consistent_sqlite_wal_backup_and_isolated_restore_test"],
                         "FUTURE_CONTROLLED_WRITE_AND_RESTORE")
        self.assertEqual(kinds["offhost_backup_and_recovery_evidence"],
                         "FUTURE_CONTROLLED_WRITE_AND_RESTORE")
        self.assertEqual(kinds["private_origin_reverse_proxy_and_tailscale_acl_evidence"],
                         "FUTURE_READ_ONLY_ATTESTATION")
        self.assertEqual(kinds["oracle_billing_eligibility_and_real_disk_inode_measurements"],
                         "FUTURE_EXTERNAL_BILLING_ATTESTATION")

    def test_every_proof_is_private_and_needs_separate_consent(self):
        for gate in m.plan()["gates"]:
            with self.subTest(id=gate["gateId"]):
                self.assertIn(gate["plannedFutureCustody"],m.CUSTODY)
                self.assertFalse(gate["publicEvidenceUploadPermitted"])
                self.assertTrue(gate["separateOperatorAuthorizationRequired"])

    def test_public_packet_never_includes_secrets_or_raw_data_fields(self):
        payload=m.plan()
        self.assertEqual(set(payload),m.PUBLIC_REPORT_FIELDS)
        text=json.dumps(payload)
        for word in ("privateKey", "accessToken", "authorizationHeader",
                     "accountNumber", "dbBytes", "rawSqlite", "apiToken",
                     "realSha", "sourceIP"):
            self.assertNotIn(word,text)

    def test_plan_reports_no_true_operator_permission(self):
        report=m.plan()
        for field in ("containsRealEvidence", "containsPrivateValues",
                      "actualCostsAttested", "actualBackupRestored",
                      "actualLiveShaVerified", "releaseAuthorized",
                      "vpsContacted", "readOnlyVpsChecksPerformed",
                      "productionWritesPerformed", "researchC5Enabled"):
            self.assertFalse(report[field],field)

    def test_missing_row_is_invalid(self):
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_EXACT_ROW_COUNT"):
            m.evaluate_only_fixture_rows(m.fixtures()[:-1])

    def test_extra_row_is_invalid(self):
        rows=m.fixtures()
        rows.append(deepcopy(rows[0]))
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_EXACT_ROW_COUNT"):
            m.evaluate_only_fixture_rows(rows)

    def test_wrong_rows_type_is_invalid(self):
        for rows in (None, {}, "", True, b"data"):
            with self.subTest(kind=type(rows).__name__):
                with self.assertRaisesRegex(m.EvidencePlanError,"STOP_EXACT_ROW_COUNT"):
                    m.evaluate_only_fixture_rows(rows)

    def test_secret_field_rejected_before_any_output(self):
        rows=m.fixtures()
        rows[0]["privateKey"]="FAKE"
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_STRICT_PUBLIC_FIXTURE_FIELDS"):
            m.evaluate_only_fixture_rows(rows)

    def test_raw_values_not_accepted(self):
        rows=m.fixtures()
        rows[0]["value"]={"filesystem":"/opt/remura/private"}
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_STRICT_PUBLIC_FIXTURE_FIELDS"):
            m.evaluate_only_fixture_rows(rows)

    def test_real_proof_status_rejected(self):
        for status in ("REAL_VERIFIED", "SUCCESS", "GO", "OK", "LIVE",
                       True, 1, None, {}, "https://example.com/proof"):
            with self.subTest(status=status):
                rows=m.fixtures()
                rows[0]["fixtureReceipt"]=status
                with self.assertRaisesRegex(m.EvidencePlanError,"STOP_REAL_EVIDENCE_NOT_ACCEPTED"):
                    m.evaluate_only_fixture_rows(rows)

    def test_duplicate_gate_rejected(self):
        rows=m.fixtures()
        rows[1]["gateId"]=rows[0]["gateId"]
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_GATE_ORDER_OR_DUPLICATE"):
            m.evaluate_only_fixture_rows(rows)

    def test_reordered_gate_rejected(self):
        rows=m.fixtures()
        rows[0],rows[1]=rows[1],rows[0]
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_GATE_ORDER_OR_DUPLICATE"):
            m.evaluate_only_fixture_rows(rows)

    def test_unknown_gate_rejected(self):
        rows=m.fixtures()
        rows[0]["gateId"]="secret_other_check"
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_GATE_ID"):
            m.evaluate_only_fixture_rows(rows)

    def test_gate_type_boolean_rejected(self):
        rows=m.fixtures()
        rows[0]["gateId"]=True
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_GATE_ID"):
            m.evaluate_only_fixture_rows(rows)

    def test_wrong_record_type_rejected(self):
        rows=m.fixtures()
        rows[0]=["id", "MISSING"]
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_STRICT_PUBLIC_FIXTURE_FIELDS"):
            m.evaluate_only_fixture_rows(rows)

    def test_mock_gate_subset_validated(self):
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_UNKNOWN_OR_DUPLICATE_FIXTURE_ID"):
            m.fixtures(simulated_gates=(m.GATES[0][0],m.GATES[0][0]))
        with self.assertRaisesRegex(m.EvidencePlanError,"STOP_UNKNOWN_OR_DUPLICATE_FIXTURE_ID"):
            m.fixtures(simulated_gates=("unknown",))

    def test_fixture_ids_invalid_type_rejected(self):
        for ids in (None, "all", {}, True, 123):
            with self.subTest(ids=type(ids).__name__):
                with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_FIXTURE_IDS"):
                    m.fixtures(simulated_gates=ids)

    def test_fixture_non_string_id_rejected(self):
        for bad in (None,1,True,{}):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_FIXTURE_IDS"):
                    m.fixtures(simulated_gates=[bad])

    def test_internal_gate_spec_drift_is_detected(self):
        orig=m.GATES
        try:
            m.GATES=orig[:-1]
            with self.assertRaisesRegex(m.EvidencePlanError,"STOP_GATE_DRIFT"):
                m.validate_plan()
        finally:
            m.GATES=orig

    def test_unknown_gate_capture_class_rejected(self):
        orig=m.GATES
        try:
            edited=list(orig)
            edited[0]=(orig[0][0],"LIVE_WRITE",orig[0][2],orig[0][3])
            m.GATES=tuple(edited)
            with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_GATE_SPEC"):
                m.validate_plan()
        finally:
            m.GATES=orig

    def test_unknown_gate_custody_rejected(self):
        orig=m.GATES
        try:
            edited=list(orig)
            edited[0]=(orig[0][0],orig[0][1],"PUBLIC_GITHUB",orig[0][3])
            m.GATES=tuple(edited)
            with self.assertRaisesRegex(m.EvidencePlanError,"STOP_INVALID_GATE_SPEC"):
                m.validate_plan()
        finally:
            m.GATES=orig

    def test_every_gate_has_human_review_criterion(self):
        self.assertTrue(all(len(x["humanReviewCriterion"]) >=20
                            for x in m.plan()["gates"]))

    def test_no_service_or_database_access_code(self):
        source=(DIR/"v165_preflight_evidence_lab.py").read_text("utf-8")
        imports={item.name.partition(".")[0]
                 for node in ast.walk(ast.parse(source))
                 if isinstance(node,ast.Import) for item in node.names}
        self.assertTrue(imports.isdisjoint({
            "os", "sqlite3", "urllib", "requests", "socket",
            "subprocess", "shutil", "pathlib", "fcntl", "http"
        }))
        for word in ("systemctl", "urlopen(", "connect(", "open(",
                     "/opt/remura"):
            self.assertNotIn(word,source)
        for arg in ("--apply","--deploy","--restore","--path","--host",
                    "--target","--credentials","--json"):
            self.assertNotIn('add_argument("'+arg+'"',source)

    def test_cli_offline_only(self):
        cmd=[sys.executable,str(DIR/"v165_preflight_evidence_lab.py")]
        p=subprocess.run(cmd+["--plan-evidence-offline"],cwd=ROOT,
                         capture_output=True,text=True,timeout=12,check=True)
        report=json.loads(p.stdout)
        self.assertEqual(report["gateCount"],12)
        self.assertEqual(report["missingRealEvidenceCount"],12)
        self.assertEqual(report["operationalDecision"],m.NO_GO)
        bad=subprocess.run(cmd+["--apply"],cwd=ROOT,
                           capture_output=True,text=True,timeout=12)
        self.assertNotEqual(bad.returncode,0)

    def test_deterministic_plan_no_current_time_timestamps(self):
        self.assertEqual(m.plan(),m.plan())
        self.assertNotIn("observedAt",m.plan())
        self.assertNotIn("capturedAt",m.plan())

    def test_synthetic_receipt_cannot_change_report_schema(self):
        r1=m.plan()
        r2=m.evaluate_only_fixture_rows(m.fixtures(
            simulated_gates=m.incident.REQUIRED_LIVE_EVIDENCE))
        self.assertEqual(set(r1),set(r2))
        self.assertEqual(r1["operationalDecision"],r2["operationalDecision"])
        self.assertEqual(r1["gates"][0]["actualRealEvidenceState"],
                         r2["gates"][0]["actualRealEvidenceState"])


if __name__=="__main__":
    unittest.main()
