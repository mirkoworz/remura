"""No-deploy specification tests for future REMURA 1.65 installer protocol."""
from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT/"deploy/oracle/v165_release_protocol_draft.py"
spec = importlib.util.spec_from_file_location("v165_release_protocol_draft", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class V165ProtocolDraftTests(unittest.TestCase):
    def test_contract_exact_existing_and_new_modules(self):
        self.assertTrue(m.validate_manifest(m.EXISTING_FILES,m.NEW_FILES))
        self.assertEqual(len(m.EXISTING_FILES),12)
        self.assertEqual(len(m.NEW_FILES),2)
        self.assertEqual(len(m.FILE_SET),14)
        self.assertIn("scripts/private_server.py",m.EXISTING_FILES)
        self.assertNotIn("scripts/storage_cache_v165.py",m.EXISTING_FILES)
        self.assertIn("scripts/storage_cache_v165.py",m.NEW_FILES)

    def test_manifest_matches_sha_pinned_offline_release_preview(self):
        preview=(ROOT/"deploy/oracle/v165_release_offline_preview.py").read_text()
        tree=ast.parse(preview)
        assignments={t.id:v for n in tree.body if isinstance(n,ast.Assign)
                     for t in n.targets if isinstance(t,ast.Name)
                     for v in [n.value]}
        pinned=ast.literal_eval(assignments["SOURCE_BLOBS"])
        self.assertEqual(set(pinned),m.FILE_SET)
        self.assertEqual(m.BASE_MAIN_SHA, ast.literal_eval(assignments["BASE_MAIN_SHA"]))

    def test_extra_private_file_or_missing_file_rejected(self):
        x=list(m.EXISTING_FILES)
        x.append("private/remura.env")
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_EXACT_FILE_MANIFEST"):
            m.validate_manifest(x,m.NEW_FILES)
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_EXACT_FILE_MANIFEST"):
            m.validate_manifest(m.EXISTING_FILES,m.NEW_FILES[:-1])
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_EXACT_FILE_MANIFEST"):
            m.validate_manifest(m.EXISTING_FILES,m.NEW_FILES+m.NEW_FILES)

    def test_refuse_malformed_manifest_types(self):
        for bad in (None,{"scripts/private_server.py":1}, "nav.js", 0):
            with self.subTest(bad=type(bad).__name__):
                with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_MANIFEST_TYPE"):
                    m.validate_manifest(bad,m.NEW_FILES)

    def test_order_blocks_service_stop_before_backup_restore(self):
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_OUT_OF_ORDER"):
            m.advance_synthetic("NOT_STARTED","collector_stopped_under_lock",
                                evidence={"synthetic":True,"step":"collector_stopped_under_lock"})
        self.assertLess(m.RELEASE_SEQUENCE.index("consistent_sqlite_backup_and_isolated_restore_verified"),
                        m.RELEASE_SEQUENCE.index("collector_stopped_under_lock"))
        self.assertLess(m.RELEASE_SEQUENCE.index("v164_rollback_bundle_sealed"),
                        m.RELEASE_SEQUENCE.index("collector_stopped_under_lock"))

    def test_cannot_reconcile_before_service_and_banner_checks(self):
        self.assertLess(m.RELEASE_SEQUENCE.index("post_install_hashes_and_private_health_verified"),
                        m.RELEASE_SEQUENCE.index("autoupdater_reconciled_in_separate_pinned_step"))
        self.assertLess(m.RELEASE_SEQUENCE.index("all_nine_version_banners_and_pwa_cache_verified"),
                        m.RELEASE_SEQUENCE.index("autoupdater_reconciled_in_separate_pinned_step"))

    def test_empty_or_fake_evidence_not_accepted(self):
        ev=m.RELEASE_SEQUENCE[0]
        for evidence in (None,{},{"synthetic":False,"step":ev},
                         {"synthetic":True,"step":"wrong"},
                         {"synthetic":1,"step":ev},
                         {"synthetic":True,"step":ev,"token":"secret"}):
            with self.subTest(evidence=evidence):
                with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_"):
                    m.advance_synthetic("NOT_STARTED",ev,evidence=evidence)

    def test_forward_step_requires_matching_event(self):
        initial=m.RELEASE_SEQUENCE[0]
        self.assertEqual(m.advance_synthetic(
            "NOT_STARTED",initial,evidence={"synthetic":True,"step":initial}),initial)
        second=m.RELEASE_SEQUENCE[1]
        self.assertEqual(m.advance_synthetic(
            initial,second,evidence={"synthetic":True,"step":second}),second)
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_OUT_OF_ORDER"):
            m.advance_synthetic(initial,initial,evidence={"synthetic":True,"step":initial})

    def test_replay_completed_still_no_go(self):
        report=m.replay_offline()
        self.assertEqual(report["lastSyntheticState"],m.RELEASE_SEQUENCE[-1])
        self.assertEqual(report["syntheticStepsVisited"],len(m.RELEASE_SEQUENCE))
        self.assertFalse(report["productionInstallerExecuted"])
        self.assertFalse(report["realVpsChanged"])
        self.assertFalse(report["operatorAuthorizationObtained"])
        self.assertEqual(report["operationalDecision"],m.NO_GO)

    def test_every_rollback_fault_ends_synthetic_only(self):
        for event in m.RELEASE_SEQUENCE:
            with self.subTest(event=event):
                report=m.replay_offline(fail_after=event)
                self.assertEqual(report["lastSyntheticState"],"ROLLED_BACK_SYNTHETIC")
                self.assertTrue(report["syntheticRollbackTriggered"])
                self.assertFalse(report["realRollbackPerformed"])
                self.assertEqual(report["operationalDecision"],m.NO_GO)

    def test_unrecognized_fault_or_event_rejected(self):
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_UNKNOWN_FAIL_POINT"):
            m.replay_offline(fail_after="INSTALL_LIVE")
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_INVALID_EVENT"):
            m.advance_synthetic("NOT_STARTED","--apply",evidence={"synthetic":True,"step":"--apply"})

    def test_rollback_terminal_state_cannot_progress(self):
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_TERMINAL_STATE"):
            m.rollback_synthetic("ROLLED_BACK_SYNTHETIC")
        with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_TERMINAL_STATE"):
            m.advance_synthetic("FAILED_CLOSED_SYNTHETIC",m.RELEASE_SEQUENCE[0],
                                evidence={"synthetic":True,"step":m.RELEASE_SEQUENCE[0]})

    def test_unknown_resources_always_unknown_not_zero(self):
        self.assertEqual(m.estimate_workspace_bytes()["state"],
                         "UNKNOWN_REAL_FILE_BYTES_NOT_MEASURED")
        self.assertIsNone(m.estimate_workspace_bytes()["minimumFreeBytesProposed"])
        self.assertEqual(m.estimate_workspace_bytes(1,0,0,None)["operationalDecision"],m.NO_GO)

    def test_synthetic_reserve_sizing_cannot_claim_disk_capacity(self):
        report=m.estimate_workspace_bytes(1_000_000,5_000,20_000,10_000)
        self.assertEqual(report["minimumFreeBytesProposed"],
                         4*(1_000_000+5_000+20_000)+3*10_000+512*1024**2)
        self.assertEqual(report["operationalDecision"],m.NO_GO)
        self.assertNotIn("availableFreeBytes",report)

    def test_invalid_size_and_boolean_reserve_rejected(self):
        for values in ((True,0,0,100),(-1,0,0,100),
                       (0,0,0,100),(100,0,0,0),
                       (100,0,0,8*1024**3+1)):
            with self.subTest(values=values):
                with self.assertRaisesRegex(m.ReleaseGuardError,"STOP_"):
                    m.estimate_workspace_bytes(*values)

    def test_readiness_snapshot_never_claims_true_production_proofs(self):
        info=m.sanitized_snapshot()
        self.assertFalse(info["installerAvailable"])
        self.assertFalse(info["applyAvailable"])
        self.assertFalse(info["realLiveEvidenceVerified"])
        self.assertFalse(info["realBackupOrRestoreVerified"])
        self.assertFalse(info["realRollbackVerified"])
        self.assertFalse(info["realCostsVerified"])
        self.assertFalse(info["productionAuthorizationVerified"])
        self.assertFalse(info["researchC5Enabled"])
        self.assertEqual(info["operationalDecision"],m.NO_GO)
        self.assertIn("live_v164_installed_sha",info["preflightEvidenceRequired"])

    def test_only_plan_offline_cli_is_offered(self):
        source=SCRIPT.read_text()
        self.assertIn('--plan-offline',source)
        for command in ("--apply","--rollback-dir","--deploy","--release",
                        "--target","--database"):
            self.assertNotIn('add_argument("'+command+'"',source)
        parsed=ast.parse(source)
        imported={a.name.partition(".")[0] for n in ast.walk(parsed)
                  if isinstance(n,ast.Import) for a in n.names}
        self.assertTrue(imported.isdisjoint(
            {"subprocess","sqlite3","socket","requests","urllib","shutil","os"}))
        self.assertNotIn("systemctl ",source)

if __name__ == "__main__":
    unittest.main()
