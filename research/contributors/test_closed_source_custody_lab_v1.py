# REMURA Contributors v0.41 LAB — 17/11/2026 09:32 CET
import sqlite3,unittest
import test_closed_generation_disposition_lab_v1 as f
from closed_source_custody_lab_v1 import source_pin,bound_disposition,verify_bound
from recovery_journal_candidate import digest
FLAGS=dict(synthetic=True,ingress_closed=True)
class SourceCustodyTests(unittest.TestCase):
    def setUp(self):
        self.fixture=f.DispositionTests("test_exclusion_and_retention_counts")
        self.fixture.setUp();self.addCleanup(self.fixture.doCleanups)
        self.db=self.fixture.db;self.events=self.fixture.events;self.pin=self.fixture.pin
        self.source=self.measure()
    def measure(self):return source_pin(self.db,self.events,self.pin,f.G,**FLAGS)
    def make(self,**kw):
        args=dict(subject=f.A,expected_source_pin=self.source,**FLAGS)
        return bound_disposition(self.db,self.events,self.pin,f.G,f.N,**dict(args,**kw))
    def verify(self,b,p,m,c,**kw):
        args=dict(expected_source_pin=self.source,latest_journal_pin=self.pin,old_generation=f.G,new_generation=f.N,**FLAGS)
        return verify_bound(b,p,m,c,**dict(args,**kw))
    def mutate(self,sql):
        self.db.execute("PRAGMA query_only=OFF")
        self.db.executescript(sql);self.db.execute("PRAGMA query_only=ON")
    def test_repeat_and_bound_candidate(self):
        self.assertEqual(self.measure(),self.source)
        b,p,m,c=self.make();r=self.verify(b,p,m,c)
        self.assertEqual([x["slot"] for x in c["entries"]],["friend-b"])
        self.assertTrue(r["fixture_source_pin_matched"])
        for k in ("may_open","restore_authorized","independent_pin_verified","scientific_admission","all_copies_erased"):self.assertFalse(r[k])
        self.assertFalse(self.db.in_transaction)
    def test_same_journal_old_backup_rejected(self):
        self.mutate("INSERT INTO lab_intent_used VALUES('"+("1"*32)+"','"+f.B+"','WRITE','CONTRIBUTOR',1800000000);")
        current=self.measure();self.assertNotEqual(current,self.source)
        with self.assertRaises(ValueError):self.make()
        b,p,m,c=self.make(expected_source_pin=current)
        self.assertTrue(self.verify(b,p,m,c,expected_source_pin=current)["fixture_source_pin_matched"])
    def test_omitted_note_still_bound_to_source(self):
        sql=self.db.execute("SELECT sql FROM sqlite_master WHERE name='entry_no_update'").fetchone()[0]
        self.mutate("DROP TRIGGER entry_no_update; UPDATE lab_entries SET note='changed' WHERE id=2; "+sql+";")
        self.assertNotEqual(self.measure(),self.source)
        with self.assertRaises(ValueError):self.make()
    def test_schema_and_revocation_tamper(self):
        self.mutate("DROP TRIGGER identity_revocation_no_delete;")
        with self.assertRaises(ValueError):self.measure()
    def test_binding_wrong_latest_anchor_or_generation(self):
        b,p,m,c=self.make()
        for kw in (dict(expected_source_pin="0"*64),dict(latest_journal_pin="0"*64),dict(new_generation=f.G),dict(ingress_closed=False)):
            with self.assertRaises(ValueError):self.verify(b,p,m,c,**kw)
        altered={**b,"source_pin":"0"*64}
        with self.assertRaises(ValueError):self.verify(altered,digest(altered),m,c)
    def test_candidate_tamper_and_wrong_binding_digest(self):
        b,p,m,c=self.make()
        with self.assertRaises(ValueError):self.verify(b,p,m,{**c,"entries":[]})
        with self.assertRaises(ValueError):self.verify(b,"0"*64,m,c)
    def test_scope_and_open_denied(self):
        with self.assertRaises(ValueError):self.make(synthetic=False)
        self.mutate("CREATE TEMP TABLE lab_entries(id);")
        with self.assertRaises(ValueError):self.make()
    def test_revocation_record_missing_with_schema_preserved(self):
        sql=self.db.execute("SELECT sql FROM sqlite_master WHERE name='identity_revocation_no_delete'").fetchone()[0]
        self.mutate("DROP TRIGGER identity_revocation_no_delete; DELETE FROM lab_identity_revocations; "+sql+";")
        with self.assertRaises(ValueError):self.measure()
if __name__=="__main__":unittest.main()
