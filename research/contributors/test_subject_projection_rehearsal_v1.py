# REMURA Contributors v0.33 LAB — 16/11/2026 13:21 CET
import json,sqlite3,unittest,tempfile
from pathlib import Path
from subject_projection_rehearsal_v1 import project
ROOT=Path(__file__).parent
A="a"*64; B="b"*64; O="c"*64; EA="1"*64; EB="2"*64; EO="3"*64
G="d"*32; P="e"*64; T="2026-11-16T10:00:00Z"
class ProjectionTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.executescript((ROOT/"d1_access_candidate.sql").read_text())
        self.db.execute("INSERT INTO lab_owner VALUES(1,?,?,0)",(O,EO))
        self.db.executemany("INSERT INTO lab_identities VALUES(?,?,?,0)",[(A,EA,"friend-a"),(B,EB,"friend-b")])
        self.db.execute("INSERT INTO lab_generation VALUES(1,?,?)",(G,P))
        self.db.execute("INSERT INTO lab_catalog VALUES('EURUSD','FXCM','EURUSD','SPOT','','fixture',1)")
        self.db.execute("UPDATE lab_state SET write_enabled=1")
        for i,s in enumerate([A,B],1):
            self.db.execute("INSERT INTO lab_entries VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i,s,f"00000000-0000-0000-0000-{i:012d}","EURUSD","FXCM","EURUSD","SPOT","","WEEK","DELTA_PEAK",
                 str(i)+".01",T,T,T,"PRIVATE_NOTE_"+str(i),"fixture"))
            self.db.execute("INSERT INTO lab_reviews VALUES(?,?,?,?,?,?)",(i,i,O,"APPROVED",T,"PRIVATE_REASON_"+str(i)))
        self.db.execute("UPDATE lab_state SET write_enabled=0")
        self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
    def get(self,**kwargs):
        opts=dict(subject=A,generation=G,pin=P,synthetic=True);opts.update(kwargs)
        return project(self.db,**opts)
    def test_exact_scope_no_other_subject_or_free_text(self):
        before=self.db.total_changes
        a=self.get();b=self.get(subject=B)
        self.assertEqual([r["price"] for r in a["entries"]],["1.01"])
        self.assertEqual([r["price"] for r in b["entries"]],["2.01"])
        self.assertEqual(a["reviews"][0]["request_id"],a["entries"][0]["request_id"])
        text=json.dumps(a)
        for secret in (A,B,O,EA,EB,EO,G,P,"PRIVATE_NOTE","PRIVATE_REASON","friend-a","2.01"):
            self.assertNotIn(secret,text)
        self.assertFalse(a["complete_privacy_export"])
        self.assertFalse(a["delivery_enabled"])
        self.assertFalse(a["deletion_performed"])
        self.assertEqual(before,self.db.total_changes)
    def test_unknown_owner_wrong_pin_or_generation(self):
        for args in (dict(subject=O),dict(subject="f"*64),dict(pin="f"*64),dict(generation="f"*32),dict(synthetic=False)):
            with self.assertRaises(ValueError):self.get(**args)
    def test_revoked_subject_not_reactivated(self):
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute("UPDATE lab_state SET recovery_enabled=1")
        self.db.execute("INSERT INTO lab_identity_revocations VALUES(?,?,?)",(A,O,T))
        self.db.execute("UPDATE lab_state SET recovery_enabled=0")
        self.db.commit();self.db.execute("PRAGMA query_only=ON")
        before=self.db.total_changes
        a=self.get()
        self.assertTrue(a["revoked"]);self.assertEqual(len(a["entries"]),1)
        self.assertEqual(before,self.db.total_changes)
    def test_open_or_mutable_state_denied(self):
        self.db.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):self.get()
        for field in ("write_enabled","read_enabled","recovery_enabled"):
            self.db.execute("UPDATE lab_state SET "+field+"=1");self.db.commit()
            self.db.execute("PRAGMA query_only=ON")
            with self.assertRaises(ValueError):self.get()
            self.db.execute("PRAGMA query_only=OFF")
            self.db.execute("UPDATE lab_state SET "+field+"=0");self.db.commit()
        self.db.execute("PRAGMA query_only=ON")
        self.db.execute("BEGIN")
        with self.assertRaises(ValueError):self.get()
        self.db.rollback()
    def test_disk_and_attached_databases_denied(self):
        with tempfile.TemporaryDirectory() as d:
            db=sqlite3.connect(str(Path(d)/"synthetic.sqlite"))
            try:
                db.execute("PRAGMA query_only=ON")
                with self.assertRaises(ValueError):project(db,subject=A,generation=G,pin=P,synthetic=True)
            finally:db.close()
        self.db.execute("PRAGMA query_only=OFF")
        self.db.execute("ATTACH ':memory:' AS extra")
        self.db.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):self.get()
