# REMURA COT v0.5 — 13 NEW additive cutover / legacy quarantine cases.
import sqlite3
import unittest
from cot_sidecar_cutover_v05_lab import SyntheticCutover, SIDECAR_TABLES, SIDECAR_TRIGGERS
from cot_revision_lineage_v01_lab import RevisionError

KEY=("tff","112741","2026-11-17")
VALUES=(1000,50,40,30,20)
CLOCK="2026-11-20T12:00:00Z"

class SidecarCutoverTests(unittest.TestCase):
    def setUp(self):
        self.fx=SyntheticCutover(synthetic=True)
    def tearDown(self):
        self.fx.close()
    def seed(self):
        self.fx.seed_legacy(dataset=KEY[0],code=KEY[1],report_date=KEY[2],
                            values=VALUES,first_seen=CLOCK)
    def test_01_explicit_synthetic_only_no_path(self):
        with self.assertRaisesRegex(RevisionError,"explicit_synthetic"):
            SyntheticCutover()
        with self.assertRaises(TypeError):
            SyntheticCutover(synthetic=True,path="oracle.sqlite3")
    def test_02_schema_adds_three_tables_without_legacy_rewrite(self):
        self.seed()
        old=self.fx._legacy_rows()
        result=self.fx.migrate()
        self.assertEqual(self.fx._legacy_rows(),old)
        self.assertEqual(result["status"],"SYNTHETIC_ADDITIVE_SCHEMA_ONLY")
        self.assertEqual(result["sidecar_versions"],0)
        self.assertTrue(result["legacy_rows_quarantined_not_versioned"])
    def test_03_future_db_schema_has_all_immutability_guards(self):
        self.fx.migrate()
        self.assertEqual(self.fx._sidecar_state()["tables"],sorted(SIDECAR_TABLES))
        self.assertEqual(self.fx._sidecar_state()["triggers"],sorted(SIDECAR_TRIGGERS))
    def test_04_failure_after_tables_removes_entire_schema(self):
        self.seed()
        old=self.fx._legacy_hash()
        with self.assertRaisesRegex(RuntimeError,"synthetic_fault_after_tables"):
            self.fx.migrate(fail_after="tables")
        self.assertEqual(self.fx._sidecar_state(),{"tables":[],"triggers":[]})
        self.assertEqual(self.fx._legacy_hash(),old)
    def test_05_failure_after_triggers_rolls_back_both_tables_and_triggers(self):
        self.seed()
        old=self.fx._legacy_hash()
        with self.assertRaisesRegex(RuntimeError,"synthetic_fault_after_triggers"):
            self.fx.migrate(fail_after="triggers")
        self.assertEqual(self.fx._sidecar_state(),{"tables":[],"triggers":[]})
        self.assertEqual(self.fx._legacy_hash(),old)
    def test_06_success_after_failed_savepoint_retry(self):
        with self.assertRaises(RuntimeError):
            self.fx.migrate(fail_after="triggers")
        self.assertEqual(self.fx.migrate()["sidecar_triggers"],4)
    def test_07_idempotent_recheck_does_not_add_versions(self):
        self.seed()
        a=self.fx.migrate()
        b=self.fx.migrate()
        self.assertEqual(a,b)
        self.assertEqual(b["sidecar_events"],0)
    def test_08_legacy_overwritten_history_cannot_be_admitted(self):
        self.seed()
        self.fx.migrate()
        for time in ("2026-11-18T00:00:00Z","2026-11-22T14:00:00Z"):
            result=self.fx.legacy_asof(dataset=KEY[0],code=KEY[1],
                                       report_date=KEY[2],decision_utc=time)
            self.assertIsNone(result["positions"])
            self.assertIsNone(result["version"])
            self.assertFalse(result["scientific_admission"])
    def test_09_missing_legacy_value_remains_unknown(self):
        self.fx.migrate()
        state=self.fx.legacy_asof(dataset=KEY[0],code=KEY[1],
                                  report_date=KEY[2],
                                  decision_utc="2026-11-22T00:00:00Z")
        self.assertEqual(state["status"],"UNKNOWN_NO_LEGACY_ROW")
    def test_10_legacy_changes_after_cutover_block_audit(self):
        self.seed()
        self.fx.migrate()
        self.fx._db.execute("UPDATE cot_reports SET first_long=900")
        with self.assertRaisesRegex(RevisionError,"legacy_modified_since_cutover"):
            self.fx.audit()
    def test_11_missing_immutable_trigger_blocks_future_cutover_report(self):
        self.fx.migrate()
        self.fx._db.execute("DROP TRIGGER cot_v05_versions_immutable_delete")
        with self.assertRaisesRegex(RevisionError,"sidecar_schema_or_immutability_drift"):
            self.fx.audit()
    def test_12_new_version_cannot_be_injected_into_schema_only_audit(self):
        self.fx.migrate()
        self.fx._db.execute("""INSERT INTO cot_v05_capture_events
            (received_utc,source_claim,envelope_sha256,payload_json)
            VALUES (?,?,?,?)""",(CLOCK,"CFTC_PRIMARY_CLAIM","b"*64,"{}"))
        with self.assertRaisesRegex(RevisionError,"sidecar_unexpected_rows"):
            self.fx.audit()
    def test_13_bad_schema_injection_and_legacy_seeding_after_cutover_denied(self):
        self.fx._db.execute("CREATE TABLE cot_v05_versions (faux INTEGER)")
        with self.assertRaisesRegex(RevisionError,"preexisting_sidecar_objects"):
            self.fx.migrate()
        self.fx._db.execute("DROP TABLE cot_v05_versions")
        self.fx.migrate()
        with self.assertRaisesRegex(RevisionError,"legacy_seed_after_cutover"):
            self.seed()

if __name__=="__main__":
    unittest.main()
