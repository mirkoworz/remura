# REMURA COT v0.6 — only NEW forward-only capture / as-of cases.
import sqlite3
import unittest
from cot_forward_only_v06_lab import ForwardOnlyCOT
from cot_revision_lineage_v01_lab import RevisionError

KEY=("tff","112741","2026-11-17")
OTHER=("tff","092741","2026-11-17")
BASE=(1000.,50.,40.,30.,20.)
REV=(1000.,70.,40.,30.,20.)
T0="2026-11-20T10:00:00Z"
T1="2026-11-20T11:00:00Z"
T2="2026-11-20T12:00:00Z"
SOURCE="CFTC_PRIMARY_CLAIM"

class ForwardCaptureTests(unittest.TestCase):
    def setUp(self):
        self.s=ForwardOnlyCOT(synthetic=True)
    def tearDown(self):
        self.s.close()
    def put(self,values=BASE,clock=T1,rows=None,**kw):
        return self.s.capture(rows or {KEY:values},received_utc=clock,
                              source_claim=SOURCE,**kw)
    def asof(self,when):
        return self.s.as_of(dataset=KEY[0],code=KEY[1],
                            report_date=KEY[2],decision_utc=when)
    def test_01_requires_synthetic_and_rejects_live_path(self):
        with self.assertRaisesRegex(RevisionError,"synthetic_only"):
            ForwardOnlyCOT()
        with self.assertRaises(TypeError):
            ForwardOnlyCOT(synthetic=True,path="/var/lib/oracle.sqlite")
    def test_02_legacy_seed_unavailable_after_schema_migration(self):
        with self.assertRaisesRegex(RevisionError,"legacy_seed_after_cutover"):
            self.s.fixture.seed_legacy(dataset=KEY[0],code=KEY[1],
                report_date=KEY[2],values=BASE,first_seen=T0)
        self.assertEqual(self.asof(T2)["status"],"UNKNOWN_NO_FORWARD_CAPTURE_AT_DECISION")
    def test_03_first_capture_creates_event_version_and_head(self):
        x=self.put()
        self.assertEqual(x["new_versions"],1)
        state=self.s.audit()
        self.assertEqual((state["events"],state["versions"],state["heads"]),(1,1,1))
        self.assertEqual(self.asof(T2)["positions"],list(BASE))
        self.assertFalse(self.asof(T2)["scientific_admission"])
    def test_04_past_decision_remains_unknown_even_after_capture(self):
        self.put()
        self.assertIsNone(self.asof(T0)["positions"])
        self.assertFalse(self.asof(T0)["legacy_fallback_allowed"])
    def test_05_forward_revision_preserves_original_asof(self):
        self.put(clock=T1)
        self.put(REV,clock=T2)
        self.assertEqual(self.asof(T1)["version"],1)
        self.assertEqual(self.asof(T1)["positions"],list(BASE))
        self.assertEqual(self.asof(T2)["version"],2)
        self.assertEqual(self.asof(T2)["positions"],list(REV))
        self.assertEqual(self.s.audit()["versions"],2)
    def test_06_same_payload_same_clock_is_idempotent(self):
        self.put()
        x=self.put()
        self.assertEqual(x["status"],"EXACT_EVENT_IDEMPOTENT")
        self.assertEqual(self.s.audit()["events"],1)
    def test_07_unchanged_forward_capture_records_event_not_version(self):
        self.put()
        x=self.put(clock=T2)
        self.assertEqual(x["new_versions"],0)
        self.assertEqual(self.s.audit()["events"],2)
        self.assertEqual(self.s.audit()["versions"],1)
    def test_08_same_clock_conflicting_version_rollback(self):
        self.put()
        with self.assertRaisesRegex(RevisionError,"same_receipt_conflicting"):
            self.put(REV)
        self.assertEqual(self.s.audit()["events"],1)
    def test_09_backdated_change_refused(self):
        self.put(clock=T2)
        with self.assertRaisesRegex(RevisionError,"nonmonotonic_local_receipt"):
            self.put(REV,clock=T1)
        self.assertEqual(self.s.audit()["versions"],1)
    def test_10_fault_after_event_atomic_rollback(self):
        with self.assertRaisesRegex(RuntimeError,"synthetic_fault_after_event"):
            self.put(fail_after="event")
        self.assertEqual((self.s.audit()["events"],self.s.audit()["versions"]),(0,0))
    def test_11_fault_after_versions_atomic_rollback(self):
        with self.assertRaisesRegex(RuntimeError,"synthetic_fault_after_versions"):
            self.put(fail_after="versions")
        self.assertEqual((self.s.audit()["events"],self.s.audit()["heads"]),(0,0))
    def test_12_multiple_keys_one_event_and_partial_revision(self):
        self.put(rows={KEY:BASE,OTHER:BASE})
        self.put(clock=T2,rows={KEY:REV,OTHER:BASE})
        result=self.s.audit()
        self.assertEqual((result["events"],result["versions"],result["heads"]),(2,3,2))
    def test_13_update_immutable_version_rejected(self):
        self.put()
        with self.assertRaises(sqlite3.DatabaseError):
            self.s.db.execute("UPDATE cot_v05_versions SET version=2")
    def test_14_manual_head_rollback_detected(self):
        self.put()
        self.put(REV,clock=T2)
        self.s.db.execute("UPDATE cot_v05_current_head SET version=1")
        with self.assertRaisesRegex(RevisionError,"stale_current_head"):
            self.s.audit()
    def test_15_legacy_mutation_after_cutover_detected(self):
        self.s.db.execute("""INSERT INTO cot_reports
          (dataset,code,report_date,oi,first_long,first_short,second_long,second_short)
          VALUES(?,?,?,?,?,?,?,?)""",(*KEY,*BASE))
        with self.assertRaisesRegex(RevisionError,"legacy_modified"):
            self.s.audit()
    def test_16_corrupt_envelope_detected_after_remove_immutability_guard(self):
        self.put()
        self.s.db.execute("DROP TRIGGER cot_v05_events_immutable_update")
        with self.assertRaises(RevisionError):
            self.s.audit()
    def test_17_false_provider_approval_denied(self):
        with self.assertRaisesRegex(RevisionError,"unsupported_source"):
            self.s.capture({KEY:BASE},received_utc=T1,source_claim="INDEPENDENT_SIGNED")
        self.assertFalse(self.s.audit()["independent_provenance"])

if __name__=="__main__":
    unittest.main()
