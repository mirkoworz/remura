"""REMURA v1.65 offline incident classification; no recovery actions."""
from __future__ import annotations

import ast
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
DIR = ROOT / "deploy/oracle"
sys.path.insert(0, str(DIR))
import v165_incident_decision_lab as m
import v165_autoupdater_state_lab as previous


class IncidentDecisionTests(unittest.TestCase):
    def test_all_fifteen_scenarios_exact_classification(self):
        expected = {
            "baseline": "BASELINE_FIXTURE_ONLY",
            "staged": "STAGED_FIXTURE_ONLY",
            "partial_replacement": "PARTIAL_REPLACEMENT_HALT",
            "installed_unreconciled": "CANDIDATE_PENDING_RECONCILE",
            "fully_reconciled": "RECONCILED_FIXTURE_ONLY",
            "rollback_partial": "ROLLBACK_INTERRUPTED_HALT",
            "rollback_before_reconcile": "RESTORED_FIXTURE_ONLY",
            "rollback_after_reconcile": "INVERSE_RECONCILE_REQUIRED",
            "corrupt_bundle": "CORRUPT_ROLLBACK_HALT",
            "sqlite_failed": "SQLITE_FAILURE_HALT",
            "updater_busy": "LOCK_NOT_ATTESTED_HALT",
            "service_failed": "UNHEALTHY_HALT",
            "unknown_evidence": "UNKNOWN_EVIDENCE_HALT",
            "dirty_updater": "DIRTY_UPDATER_HALT",
            "contradictory": "CONTRADICTORY_HALT",
        }
        self.assertEqual(set(m.SCENARIOS), set(expected))
        for key, code in expected.items():
            with self.subTest(case=key):
                self.assertEqual(m.decide(m.SCENARIOS[key])["classification"], code)

    def test_every_scenario_never_allows_live_actions(self):
        for name, evidence in m.SCENARIOS.items():
            with self.subTest(name=name):
                report = m.decide(evidence)
                self.assertFalse(report["automaticRollbackPermitted"])
                self.assertFalse(report["automaticReconciliationPermitted"])
                self.assertFalse(report["realVpsInspected"])
                self.assertFalse(report["operatorAuthorized"])
                self.assertFalse(report["researchC5Enabled"])
                self.assertEqual(report["operationalDecision"], m.NO_GO)

    def test_real_proof_flags_always_false(self):
        result = m.decide(m.fixture(phase="RECONCILED", code="V165", updater="V165"))
        for key in ("realDatabaseRestored", "actualOffhostRecoveryVerified",
                    "actualCIAndLiveShaAttested", "actualCostsAndAclAttested"):
            self.assertIs(result[key], False)

    def test_no_source_field_or_private_data_accepted(self):
        bad = m.fixture()
        bad["privateSecret"] = "fake"
        with self.assertRaisesRegex(m.IncidentFixtureError, "STOP_STRICT_FIELDS"):
            m.decide(bad)

    def test_missing_key_rejected(self):
        bad = m.fixture()
        del bad["lock"]
        with self.assertRaisesRegex(m.IncidentFixtureError, "STOP_STRICT_FIELDS"):
            m.classify(bad)

    def test_wrong_structures_rejected(self):
        for bad in (None, [], "LIVE", True, 123, ()):
            with self.subTest(bad=bad):
                with self.assertRaisesRegex(m.IncidentFixtureError,
                                            "STOP_STRICT_FIELDS"):
                    m.classify(bad)

    def test_non_fixture_mode_rejected(self):
        for mode in (None, "LIVE", True, "READ_ONLY", 1):
            bad = m.fixture()
            bad["mode"] = mode
            with self.subTest(mode=mode):
                with self.assertRaisesRegex(m.IncidentFixtureError,
                                            "STOP_SYNTHETIC_MODE_ONLY"):
                    m.classify(bad)

    def test_wrong_phase_rejected(self):
        for value in ("INSTALL", "", "RELEASE", None, True):
            with self.subTest(value=value):
                with self.assertRaisesRegex(m.IncidentFixtureError, "STOP_INVALID_PHASE"):
                    m.classify(m.fixture(phase=value))

    def test_wrong_code_rejected(self):
        for value in ("LIVE_V165", "", "AUTO", None, False):
            with self.subTest(value=value):
                with self.assertRaisesRegex(m.IncidentFixtureError, "STOP_INVALID_CODE"):
                    m.classify(m.fixture(code=value))

    def test_wrong_updater_rejected(self):
        for value in ("READY", "MAIN", "", 1, None):
            with self.subTest(value=value):
                with self.assertRaisesRegex(m.IncidentFixtureError, "STOP_INVALID_UPDATER"):
                    m.classify(m.fixture(updater=value))

    def test_wrong_backup_type_rejected(self):
        with self.assertRaisesRegex(m.IncidentFixtureError,
                                    "STOP_INVALID_ROLLBACKBUNDLE"):
            m.classify(m.fixture(rollbackBundle=True))

    def test_wrong_sqlite_type_rejected(self):
        with self.assertRaisesRegex(m.IncidentFixtureError,
                                    "STOP_INVALID_SQLITERESTORE"):
            m.classify(m.fixture(sqliteRestore=False))

    def test_wrong_health_type_rejected(self):
        with self.assertRaisesRegex(m.IncidentFixtureError,
                                    "STOP_INVALID_HEALTH"):
            m.classify(m.fixture(health=42))

    def test_wrong_lock_type_rejected(self):
        with self.assertRaisesRegex(m.IncidentFixtureError,
                                    "STOP_INVALID_LOCK"):
            m.classify(m.fixture(lock=True))

    def test_corrupt_bundle_takes_precedence(self):
        q = m.fixture(code="UNKNOWN", lock="BUSY",
                      sqliteRestore="FAILED", rollbackBundle="CORRUPT")
        self.assertEqual(m.classify(q), "CORRUPT_ROLLBACK_HALT")

    def test_failed_sqlite_has_precedence_over_updater(self):
        q = m.fixture(sqliteRestore="FAILED", updater="DIRTY")
        self.assertEqual(m.classify(q), "SQLITE_FAILURE_HALT")

    def test_busy_lock_rejects_even_fully_reconciled_fixture(self):
        q = m.fixture(phase="RECONCILED", code="V165",
                      updater="V165", lock="BUSY")
        self.assertEqual(m.classify(q), "LOCK_NOT_ATTESTED_HALT")

    def test_unhealthy_prevents_reconcile_review(self):
        q = m.fixture(phase="CODE_REPLACED", code="V165", health="FAILED")
        self.assertEqual(m.classify(q), "UNHEALTHY_HALT")

    def test_unknown_does_not_default_to_zero_or_success(self):
        for field in ("phase", "code", "updater", "rollbackBundle",
                      "sqliteRestore", "health", "lock"):
            with self.subTest(field=field):
                q = m.fixture()
                q[field] = "UNKNOWN"
                self.assertIn(m.classify(q), {
                    "LOCK_NOT_ATTESTED_HALT", "UNKNOWN_EVIDENCE_HALT"
                })

    def test_dirty_updater_never_autocorrected(self):
        q = m.fixture(phase="RESTORED", updater="DIRTY")
        self.assertEqual(m.classify(q), "DIRTY_UPDATER_HALT")

    def test_incomplete_rollback_requires_human_review(self):
        q = m.fixture(phase="RESTORING", code="MIXED", updater="V165")
        self.assertEqual(m.classify(q), "ROLLBACK_INTERRUPTED_HALT")

    def test_post_reconcile_rollback_requires_inverse_review(self):
        q = m.fixture(phase="RESTORED", updater="V165")
        report = m.decide(q)
        self.assertEqual(report["classification"], "INVERSE_RECONCILE_REQUIRED")
        self.assertEqual(report["humanReviewGate"],
                         "REVIEW_SEPARATE_INVERSE_RECONCILE")
        self.assertFalse(report["automaticReconciliationPermitted"])

    def test_candidate_not_conflated_with_updater(self):
        q = m.fixture(phase="CODE_REPLACED", code="V165", updater="V164")
        self.assertEqual(m.classify(q), "CANDIDATE_PENDING_RECONCILE")

    def test_no_updater_v165_with_old_code_is_green(self):
        for phase in m.PHASES:
            with self.subTest(phase=phase):
                q = m.fixture(phase=phase, code="V164", updater="V165")
                self.assertNotIn(m.classify(q),
                    ("BASELINE_FIXTURE_ONLY", "RESTORED_FIXTURE_ONLY",
                     "RECONCILED_FIXTURE_ONLY"))

    def test_entire_code_updater_phase_matrix_stays_no_go(self):
        for phase in m.PHASES:
            for code in m.CODES:
                for updater in m.UPDATERS:
                    with self.subTest(phase=phase, code=code, updater=updater):
                        report = m.decide(m.fixture(
                            phase=phase, code=code, updater=updater))
                        self.assertFalse(report["automaticRollbackPermitted"])
                        self.assertFalse(report["automaticReconciliationPermitted"])
                        self.assertEqual(report["operationalDecision"], m.NO_GO)

    def test_every_classification_has_only_human_gate(self):
        self.assertEqual(set(m.CLASSIFICATIONS),
                         {m.classify(x) for x in m.SCENARIOS.values()})
        self.assertTrue(all(x[0].isupper() for x in m.CLASSIFICATIONS.values()))

    def test_evidence_list_explicit_live_separate(self):
        report = m.decide(m.fixture())
        keys = report["requiredIndependentLiveEvidence"]
        self.assertEqual(len(keys), 12)
        self.assertIn("offhost_backup_and_recovery_evidence", keys)
        self.assertIn("explicit_separate_operator_authorization", keys)

    def test_previous_lab_rollback_mismatch_maps_to_inverse_gate(self):
        previous_result = previous.rehearse(
            mode=previous.MODE, fault="rollback_after_reconcile")
        self.assertEqual(previous_result["state"],
                         "FAKE_INVERSE_RECONCILE_REQUIRED_NO_AUTO_FIX")
        self.assertEqual(
            m.classify(m.fixture(phase="RESTORED", updater="V165")),
            "INVERSE_RECONCILE_REQUIRED")

    def test_previous_lab_pending_reconcile_maps_correctly(self):
        previous_result = previous.rehearse(
            mode=previous.MODE, fault="stop_before_reconcile")
        self.assertEqual(previous_result["state"], "FAKE_PENDING_NOT_RECONCILED")
        self.assertEqual(m.classify(m.fixture(
            phase="CODE_REPLACED", code="V165", updater="V164")),
            "CANDIDATE_PENDING_RECONCILE")

    def test_cli_fixed_scenarios_no_live_parameters(self):
        source=(DIR / "v165_incident_decision_lab.py").read_text("utf-8")
        imported={item.name.partition(".")[0]
                  for node in ast.walk(ast.parse(source))
                  if isinstance(node, ast.Import) for item in node.names}
        self.assertTrue(imported.isdisjoint(
            {"os", "sqlite3", "subprocess", "urllib", "socket", "requests",
             "shutil", "fcntl"}))
        for flag in ("--apply", "--deploy", "--rollback", "--database",
                     "--target", "--host", "--path", "--json"):
            self.assertNotIn('add_argument("' + flag + '"', source)
        cmd=[sys.executable, str(DIR / "v165_incident_decision_lab.py")]
        process=subprocess.run(
            cmd+["--decision-fixtures-offline"],cwd=ROOT,
            text=True,capture_output=True,check=True,timeout=15)
        parsed=json.loads(process.stdout)
        self.assertEqual(parsed["scenarioCount"], 15)
        self.assertEqual(parsed["operationalDecision"], m.NO_GO)
        self.assertFalse(parsed["liveActionsAvailable"])
        invalid=subprocess.run(
            cmd+["--apply"],cwd=ROOT,text=True,capture_output=True,timeout=15)
        self.assertNotEqual(invalid.returncode,0)

    def test_fixture_replay_is_deterministic(self):
        self.assertEqual(m.rehearse(),m.rehearse())


if __name__ == "__main__":
    unittest.main()
