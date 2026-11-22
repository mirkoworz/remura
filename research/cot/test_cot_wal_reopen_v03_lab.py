# REMURA COT v0.3: ONLY NEW fixture WAL reopen checks. No Oracle/Cloudflare.
import sqlite3
import unittest

from cot_revision_lineage_v01_lab import RevisionError
from cot_wal_reopen_v03_lab import EphemeralWALReopen

K=("tff","112741","2026-11-17")
K2=("tff","092741","2026-11-17")
A=(1000.0,50.0,40.0,30.0,20.0)
B=(1000.0,70.0,40.0,30.0,20.0)
T0="2026-11-20T10:00:00Z"
T1="2026-11-20T12:00:00Z"
TM="2026-11-20T14:00:00Z"
T2="2026-11-20T18:00:00Z"
SOURCE="CFTC_PRIMARY_CLAIM"

class WALReopenTests(unittest.TestCase):
    def setUp(self):
        self.fx=EphemeralWALReopen(synthetic=True)

    def tearDown(self):
        self.fx.close()

    def ingest(self, rows=None, t=T1, fail=None):
        return self.fx.store.ingest(
            rows if rows is not None else {K:A},
            received_utc=t,source_claim=SOURCE,fail_after_row=fail)

    def historical(self, t=TM, key=K):
        return self.fx.store.as_of(
            dataset=key[0],code=key[1],report_date=key[2],decision_utc=t)

    def present(self):
        return self.fx.store.current(
            dataset=K[0],code=K[1],report_date=K[2])

    def test_01_fixture_has_real_ephemeral_sqlite_file_and_wal(self):
        self.assertTrue(self.fx.fixture_file_exists())
        self.assertEqual(self.fx.journal_mode(),"wal")
        self.assertEqual(self.fx.assert_integrity(),"ok")

    def test_02_committed_event_survives_close_and_reopen(self):
        self.ingest()
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(1,1,1))
        self.assertEqual(self.present()["positions"],list(A))

    def test_03_two_versions_reopen_without_past_time_travel(self):
        self.ingest()
        self.ingest({K:B},t=T2)
        self.fx.reopen()
        self.assertEqual(self.historical(TM)["positions"],list(A))
        self.assertEqual(self.historical(T2)["positions"],list(B))
        self.assertEqual(self.present()["positions"],list(B))

    def test_04_injected_fault_mid_new_batch_stays_rolled_back_after_reopen(self):
        with self.assertRaisesRegex(RuntimeError,"synthetic_crash"):
            self.ingest({K:A,K2:A},fail=1)
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(0,0,0))
        self.assertEqual(self.historical(T2)["status"],"UNKNOWN")

    def test_05_fault_mid_revision_preserves_old_values_after_reopen(self):
        self.ingest({K:A,K2:A})
        with self.assertRaisesRegex(RuntimeError,"synthetic_crash"):
            self.ingest({K:B,K2:B},t=T2,fail=1)
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(1,2,2))
        self.assertEqual(self.present()["positions"],list(A))
        self.assertEqual(self.historical(T2)["positions"],list(A))

    def test_06_idempotent_restart_preserves_single_event(self):
        self.ingest()
        self.fx.reopen()
        again=self.ingest()
        self.assertEqual(again["status"],"IDEMPOTENT_SYNTHETIC_REPLAY")
        self.assertEqual(self.fx.store.counts(),(1,1,1))

    def test_07_later_unchanged_capture_adds_event_not_fake_revision(self):
        self.ingest()
        self.fx.reopen()
        self.ingest(t=T2)
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(2,1,1))
        self.assertEqual(self.historical(T2)["version"],1)

    def test_08_trigger_immutability_persists_after_restart(self):
        self.ingest()
        self.fx.reopen()
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_event"):
            self.fx.store._db.execute("DELETE FROM capture_events")
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_version"):
            self.fx.store._db.execute("UPDATE versions SET version=9")
        self.assertEqual(self.fx.store.counts(),(1,1,1))

    def test_09_concurrent_write_conflict_aborts_without_partial_change(self):
        self.ingest()
        other=sqlite3.connect(str(self.fx._path),timeout=0,isolation_level=None)
        try:
            self.fx.store._db.execute("BEGIN IMMEDIATE")
            with self.assertRaisesRegex(sqlite3.OperationalError,"locked"):
                other.execute("BEGIN IMMEDIATE")
            self.fx.store._db.execute("ROLLBACK")
        finally:
            other.close()
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(1,1,1))

    def test_10_invalid_values_fail_before_durable_write(self):
        with self.assertRaises(RevisionError):
            self.ingest({K:(1000.0,True,40.0,30.0,20.0)})
        self.fx.reopen()
        self.assertEqual(self.fx.store.counts(),(0,0,0))

    def test_11_missing_before_first_seen_remains_unknown_after_reopen(self):
        self.ingest()
        self.fx.reopen()
        self.assertIsNone(self.historical(T0)["positions"])
        self.assertEqual(self.historical(T0)["status"],"UNKNOWN")

    def test_12_local_provenance_remains_unattested_after_reopen(self):
        self.ingest()
        self.fx.reopen()
        observation=self.historical(T2)
        self.assertFalse(observation["external_attestation"])
        self.assertFalse(observation["live_use_allowed"])

    def test_13_integrity_check_and_foreign_keys_after_each_reopen(self):
        self.ingest()
        for _ in range(3):
            self.fx.reopen()
            self.assertEqual(self.fx.assert_integrity(),"ok")
            self.assertEqual(self.fx.store._db.execute("PRAGMA foreign_keys").fetchone()[0],1)

    def test_14_no_arbitrary_database_path_can_be_supplied(self):
        with self.assertRaises(TypeError):
            EphemeralWALReopen(synthetic=True,db_path="/tmp/external.sqlite3")
        with self.assertRaises(RevisionError):
            EphemeralWALReopen()

    def test_15_temp_fixture_auto_removed_on_close(self):
        self.ingest()
        path=self.fx._path
        self.fx.close()
        self.assertFalse(path.exists())
        # tearDown expects another close; create a fresh clean fixture.
        self.fx=EphemeralWALReopen(synthetic=True)

if __name__=="__main__":
    unittest.main()
