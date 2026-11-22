# REMURA - new atomic COT tests ONLY; no external network or production DB.
import hashlib
import json
import sqlite3
import unittest

from cot_revision_lineage_v01_lab import RevisionError
from cot_atomic_ingest_v02_lab import AtomicOfflineCOTStore

KEY = ("tff", "112741", "2026-11-17")
KEY2 = ("tff", "092741", "2026-11-17")
OLD = (1000.0, 50.0, 40.0, 30.0, 20.0)
NEW = (1000.0, 75.0, 40.0, 30.0, 20.0)
T1 = "2026-11-20T12:00:00Z"
T2 = "2026-11-20T18:00:00Z"
MID = "2026-11-20T14:00:00Z"
SRC = "CFTC_PRIMARY_CLAIM"

class AtomicCotTests(unittest.TestCase):
    def setUp(self):
        self.db = AtomicOfflineCOTStore(synthetic=True)

    def tearDown(self):
        self.db.close()

    def ingest(self, rows=None, at=T1, source=SRC, fail=None):
        return self.db.ingest(rows or {KEY: OLD}, received_utc=at,
                              source_claim=source, fail_after_row=fail)

    def asof(self, when=MID, key=KEY):
        return self.db.as_of(dataset=key[0], code=key[1],
                             report_date=key[2], decision_utc=when)

    def current(self):
        return self.db.current(dataset=KEY[0], code=KEY[1], report_date=KEY[2])

    def test_01_new_capture_atomically_publishes_event_version_and_head(self):
        result = self.ingest()
        self.assertEqual(self.db.counts(), (1, 1, 1))
        self.assertEqual(result["new_versions"], 1)
        self.assertEqual(self.current()["positions"], list(OLD))
        self.assertFalse(result["external_attestation"])

    def test_02_revision_does_not_time_travel_across_decision_boundary(self):
        self.ingest()
        before = self.asof()
        self.ingest({KEY: NEW}, at=T2)
        after_old = self.asof()
        after_new = self.asof(when=T2)
        self.assertEqual(before["positions"], list(OLD))
        self.assertEqual(after_old["positions"], list(OLD))
        self.assertEqual(after_new["positions"], list(NEW))
        self.assertEqual((after_old["version"], after_new["version"]), (1, 2))
        self.assertEqual(self.current()["positions"], list(NEW))

    def test_03_crash_between_rows_rolls_back_all_three_tables(self):
        with self.assertRaisesRegex(RuntimeError, "synthetic_crash"):
            self.ingest({KEY: OLD, KEY2: OLD}, fail=1)
        self.assertEqual(self.db.counts(), (0, 0, 0))
        self.assertEqual(self.asof(when=T2)["status"], "UNKNOWN")

    def test_04_failed_revision_cannot_publish_new_head_or_version(self):
        self.ingest({KEY: OLD, KEY2: OLD})
        initial_counts = self.db.counts()
        with self.assertRaisesRegex(RuntimeError, "synthetic_crash"):
            self.ingest({KEY: NEW, KEY2: NEW}, at=T2, fail=1)
        self.assertEqual(self.db.counts(), initial_counts)
        self.assertEqual(self.current()["positions"], list(OLD))
        self.assertEqual(self.asof(when=T2)["positions"], list(OLD))

    def test_05_invalid_second_row_rejects_entire_batch_without_write(self):
        with self.assertRaises(RevisionError):
            self.ingest({KEY: OLD, KEY2: (1000.0, True, 0.0, 0.0, 0.0)})
        self.assertEqual(self.db.counts(), (0, 0, 0))

    def test_06_exact_repeat_is_idempotent(self):
        self.ingest()
        result = self.ingest()
        self.assertEqual(result["status"], "IDEMPOTENT_SYNTHETIC_REPLAY")
        self.assertEqual(self.db.counts(), (1, 1, 1))

    def test_07_observed_unchanged_later_preserves_version_with_new_event(self):
        self.ingest()
        self.ingest(at=T2)
        self.assertEqual(self.db.counts(), (2, 1, 1))
        self.assertEqual(self.asof(when=T2)["version"], 1)

    def test_08_conflicting_values_same_local_clock_fail_closed(self):
        self.ingest()
        with self.assertRaisesRegex(RevisionError, "same_clock_conflicting_values"):
            self.ingest({KEY: NEW}, at=T1)
        self.assertEqual(self.db.counts(), (1, 1, 1))

    def test_09_reverse_local_time_fails_without_backdating(self):
        self.ingest(at=T2)
        with self.assertRaisesRegex(RevisionError, "nonmonotonic_local_capture"):
            self.ingest({KEY: NEW}, at=T1)
        self.assertEqual(self.db.counts(), (1, 1, 1))

    def test_10_versions_and_events_are_sql_immutable(self):
        self.ingest()
        for sql, error in (
            ("UPDATE capture_events SET received_at='2020-01-01T00:00:00Z'", "immutable_event"),
            ("DELETE FROM capture_events", "immutable_event"),
            ("UPDATE versions SET received_at='2020-01-01T00:00:00Z'", "immutable_version"),
            ("DELETE FROM versions", "immutable_version"),
        ):
            with self.assertRaisesRegex(sqlite3.DatabaseError, error):
                self.db._db.execute(sql)
        self.assertEqual(self.db.counts(), (1, 1, 1))

    def test_11_missing_legacy_version_stays_unknown_not_zero(self):
        self.ingest()
        missing = self.asof(when="2026-11-20T11:59:59Z")
        self.assertEqual(missing["status"], "UNKNOWN")
        self.assertIsNone(missing["positions"])
        self.assertIsNone(missing["version"])

    def test_12_source_claim_is_recorded_but_never_attested(self):
        r = self.ingest(source="CFTC_FALLBACK_CLAIM")
        self.assertFalse(r["live_use_allowed"])
        self.assertEqual(self.asof()["source_claim"], "CFTC_FALLBACK_CLAIM")
        self.assertFalse(self.asof()["external_attestation"])
        with self.assertRaisesRegex(RevisionError, "unknown_source_claim"):
            self.ingest({KEY2: OLD}, at=T2, source="UNVERIFIED")

    def test_13_envelope_includes_source_receipt_and_exact_rows(self):
        self.ingest({KEY: OLD, KEY2: NEW})
        event_hash, payload = self.db._db.execute(
            "SELECT envelope_sha256,envelope_json FROM capture_events"
        ).fetchone()
        self.assertEqual(hashlib.sha256(payload.encode("ascii")).hexdigest(), event_hash)
        envelope = json.loads(payload)
        self.assertEqual(envelope["source_claim"], SRC)
        self.assertEqual(envelope["local_received_at"], T1)
        self.assertEqual(len(envelope["rows"]), 2)

    def test_14_tampered_mutable_head_is_detected_before_current_read(self):
        self.ingest()
        self.ingest({KEY: NEW}, at=T2)
        self.db._db.execute(
            "UPDATE current_head SET version=1 WHERE dataset=? AND code=?",
            (KEY[0], KEY[1])
        )
        with self.assertRaisesRegex(RevisionError, "head_is_not_latest"):
            self.current()
        self.assertEqual(self.asof(when=T2)["positions"], list(NEW))

    def test_15_not_file_backed_without_optin_and_no_real_external_calls(self):
        with self.assertRaises(RevisionError):
            AtomicOfflineCOTStore()
        self.assertEqual(self.db._db.execute("PRAGMA database_list").fetchone()[2], "")
        self.assertFalse(self.ingest()["external_attestation"])

    def test_16_bad_event_integrity_fails_closed_during_asof(self):
        self.ingest()
        # Physical tampering is blocked by triggers, but integrity verification
        # also rejects a corrupted envelope if corruption bypasses write guards.
        self.db._db.execute("DROP TRIGGER events_no_update")
        self.db._db.execute("UPDATE capture_events SET envelope_json='{}'")
        with self.assertRaisesRegex(RevisionError, "event_integrity_failure"):
            self.asof()

if __name__ == "__main__":
    unittest.main()
