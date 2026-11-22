# REMURA COT global integrity v0.4 - new synthetic cases only.
import hashlib
import json
import sqlite3
import unittest

from cot_wal_reopen_v03_lab import EphemeralWALReopen
from cot_global_integrity_v04_lab import audit_fixture
from cot_revision_lineage_v01_lab import RevisionError

KEY=("tff","112741","2026-11-17")
OTHER=("tff","092741","2026-11-17")
VALUES=(1000.0,50.0,40.0,30.0,20.0)
REV=(1000.0,70.0,40.0,30.0,20.0)
T1="2026-11-20T12:00:00Z"
T2="2026-11-20T18:00:00Z"
SOURCE="CFTC_PRIMARY_CLAIM"

class GlobalCOTIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.fx=EphemeralWALReopen(synthetic=True)
        self.db=self.fx.store._db

    def tearDown(self):
        self.fx.close()

    def capture(self,rows=None,at=T1):
        self.fx.store.ingest(rows if rows is not None else {KEY:VALUES},
                             received_utc=at,source_claim=SOURCE)

    def state(self):
        return audit_fixture(self.db,synthetic=True)

    def test_01_empty_fixture_unknown_not_evidence(self):
        self.assertEqual(self.state()["status"],"UNKNOWN_EMPTY_FIXTURE")
        self.assertEqual(self.state()["counts"]["capture_events"],0)

    def test_02_valid_capture_integrity_consistent_but_unattested(self):
        self.capture()
        out=self.state()
        self.assertEqual(out["status"],"LOCAL_FIXTURE_CONSISTENT_UNATTESTED")
        self.assertEqual(out["issues"],[])
        self.assertFalse(out["independent_first_seen_verified"])

    def test_03_multiple_revisions_keep_global_chain_consistent(self):
        self.capture({KEY:VALUES,OTHER:VALUES})
        self.capture({KEY:REV,OTHER:VALUES},at=T2)
        out=self.state()
        self.assertEqual(out["counts"],{"capture_events":2,"versions":3,"heads":2})
        self.assertEqual(out["issues"],[])

    def test_04_missing_head_rejected_even_if_asof_history_still_exists(self):
        self.capture()
        self.db.execute("DELETE FROM current_head")
        self.assertIn("MISSING_OR_EXTRA_CURRENT_HEAD",self.state()["issues"])

    def test_05_stale_head_rejected_even_if_legacy_read_would_succeed(self):
        self.capture()
        self.capture({KEY:REV},at=T2)
        self.db.execute("UPDATE current_head SET version=1")
        self.assertIn("CURRENT_HEAD_NOT_LATEST",self.state()["issues"])

    def test_06_missing_immutability_trigger_detected(self):
        self.capture()
        self.db.execute("DROP TRIGGER events_no_delete")
        self.assertIn("IMMUTABILITY_TRIGGER_MISSING",self.state()["issues"])

    def test_07_altered_event_body_triggers_hash_failure(self):
        self.capture()
        self.db.execute("DROP TRIGGER events_no_update")
        self.db.execute("UPDATE capture_events SET envelope_json='{}'")
        self.assertIn("EVENT_HASH_MISMATCH",self.state()["issues"])

    def test_08_changed_event_row_count_detected(self):
        self.capture()
        self.db.execute("DROP TRIGGER events_no_update")
        self.db.execute("UPDATE capture_events SET row_count=0")
        self.assertIn("EVENT_ROWCOUNT_INVALID",self.state()["issues"])

    def test_09_altered_version_payload_triggers_hash_failure(self):
        self.capture()
        self.db.execute("DROP TRIGGER versions_no_update")
        self.db.execute("UPDATE versions SET content_payload_json='[]'")
        self.assertIn("VERSION_HASH_MISMATCH",self.state()["issues"])

    def test_10_forged_source_claim_is_not_accepted(self):
        self.capture()
        self.db.execute("DROP TRIGGER events_no_update")
        self.db.execute("UPDATE capture_events SET source_claim='UNVERIFIED'")
        self.assertIn("EVENT_SOURCE_INVALID",self.state()["issues"])

    def test_11_divergent_version_vs_event_receipt_clock_detected(self):
        self.capture()
        self.db.execute("DROP TRIGGER versions_no_update")
        self.db.execute("UPDATE versions SET received_at='2026-11-21T01:00:00Z'")
        self.assertIn("VERSION_EVENT_CLOCK_MISMATCH",self.state()["issues"])

    def test_12_explicit_synthetic_connection_permission_required(self):
        self.capture()
        with self.assertRaises(RevisionError):
            audit_fixture(self.db)
        with self.assertRaises(RevisionError):
            audit_fixture("oracle.sqlite3",synthetic=True)
        self.assertEqual(self.state()["write_operations_performed"],0)

if __name__=="__main__":
    unittest.main()
