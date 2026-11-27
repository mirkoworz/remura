# REMURA Contributors v0.40 LAB — 17/11/2026 07:04 CET (session start)
import sqlite3,unittest,copy
from pathlib import Path
from recovery_journal_candidate import ZERO,append
from closed_generation_disposition_lab_v1 import disposition,check_disposition
O,A,B="a"*64,"b"*64,"c"*64
EO,EA,EB="d"*64,"e"*64,"f"*64
G,N="1"*32,"2"*32
T="2026-11-17T05:44:00Z"
class DispositionTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.events=[];self.pin=ZERO
        for s,t,r,slot,kind in [(O,EO,"OWNER","owner","ENROLL"),(A,EA,"CONTRIBUTOR","friend-a","ENROLL"),(B,EB,"CONTRIBUTOR","friend-b","ENROLL"),(A,EA,"CONTRIBUTOR","friend-a","REVOKE")]:
            self.events,self.pin=append(self.events,self.pin,kind,T,s,t,r,slot)
        db=self.db
        db.executescript((Path(__file__).parent/"d1_access_candidate.sql").read_text())
        db.execute("INSERT INTO lab_owner VALUES(1,?,?,0)",(O,EO))
        db.executemany("INSERT INTO lab_identities VALUES(?,?,?,0)",[(A,EA,"friend-a"),(B,EB,"friend-b")])
        db.execute("INSERT INTO lab_generation VALUES(1,?,?)",(G,self.pin))
        db.execute("INSERT INTO lab_catalog VALUES('EURUSD','FX','EURUSD','SPOT','','fixture',1)")
        db.execute("UPDATE lab_state SET write_enabled=1,recovery_enabled=1")
        for i,s in enumerate((A,B),1):
            db.execute("INSERT INTO lab_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(i,s,str(i)*36,"EURUSD","FX","EURUSD","SPOT","","DAY","DELTA_PEAK","1.08",T,T,T,"private-note","fixture"))
            db.execute("INSERT INTO lab_reviews VALUES(?,?,?,?,?,?)",(i,i,O,"APPROVED",T,"private-reason"))
        db.execute("INSERT INTO lab_identity_revocations VALUES(?,?,?)",(A,O,T))
        db.execute("UPDATE lab_state SET write_enabled=0,recovery_enabled=0")
        db.commit();db.execute("PRAGMA query_only=ON")
    def make(self,**kw):
        args=dict(subject=A,synthetic=True,ingress_closed=True)
        return disposition(self.db,self.events,self.pin,G,N,**dict(args,**kw))
    def test_exclusion_and_retention_counts(self):
        m,p,c=self.make()
        self.assertEqual([x["slot"] for x in c["entries"]],["friend-b"])
        self.assertEqual([x["entry_id"] for x in c["historical_reviews"]],[2])
        out=check_disposition(m,p,c,expected_generation=N,synthetic=True,ingress_closed=True)
        self.assertEqual((out["retained_entries"],out["excluded_entries"],out["retained_reviews"],out["excluded_reviews"]),(1,1,1,1))
        self.assertFalse(out["may_open"]);self.assertFalse(out["all_copies_erased"])
    def test_data_minimization(self):
        m,p,c=self.make()
        for x in (A,B,O,EA,EB,EO,"private-note","private-reason","request_id"):
            self.assertNotIn(x,str(c))
        self.assertTrue(c["quarantine"]);self.assertFalse(c["scientific_admission"])
    def test_old_generation_and_tampered_candidate(self):
        m,p,c=self.make()
        for bad in ({**c,"generation":G},{**c,"entries":[]},{**c,"may_open":True}):
            with self.assertRaises(ValueError):check_disposition(m,p,bad,expected_generation=N,synthetic=True,ingress_closed=True)
        with self.assertRaises(ValueError):check_disposition(m,p,c,expected_generation=G,synthetic=True,ingress_closed=True)
    def test_pin_tampered(self):
        m,p,c=self.make()
        with self.assertRaises(ValueError):check_disposition(m,"0"*64,c,expected_generation=N,synthetic=True,ingress_closed=True)
    def test_closed_and_query_only(self):
        for k in ("synthetic","ingress_closed"):
            with self.assertRaises(ValueError):self.make(**{k:False})
        self.db.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):self.make()
    def test_stale_source_identity_denied(self):
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute("DROP TRIGGER identity_no_rebind");self.db.execute("UPDATE lab_identities SET revoked=0 WHERE subject=?",(A,))
        self.db.commit();self.db.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):self.make()
    def test_source_not_modified(self):
        self.make()
        self.assertFalse(self.db.in_transaction)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_entries").fetchone()[0],2)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_reviews").fetchone()[0],2)
    def test_active_subject_cannot_be_excluded(self):
        with self.assertRaises(ValueError):self.make(subject=B)
if __name__=="__main__":unittest.main()
