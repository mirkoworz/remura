# REMURA Contributors v0.22 LAB — 16/11/2026 07:08 CET
import sqlite3, unittest, subprocess, tempfile, time, concurrent.futures
from pathlib import Path
from test_d1_lab_review import queries, I, R, K, T, L
ROOT=Path(__file__).parent
Q=queries("d1_access_candidate.mjs"); N=queries("operation_intent_candidate.mjs")
A="a"*64; B="b"*64; O="c"*64; EA="1"*64; EB="2"*64; EO="3"*64

class AccessCandidateTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.row_factory=sqlite3.Row
        self.db.executescript((ROOT/"d1_access_candidate.sql").read_text())
        self.db.execute("INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)",(O,EO))
        self.db.executemany("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)",[(A,EA,"friend-a"),(B,EB,"friend-b")])
        self.db.execute("INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)",K+("fixture-fx",))
    def tearDown(self):self.db.close()
    def gates(self,w=0,r=0,h=0):
        self.db.execute("UPDATE lab_state SET write_enabled=?,read_enabled=?,recovery_enabled=?",(w,r,h))
    def q(self,name,*args):return self.db.execute(Q[name],args).fetchall()
    def insert(self,s=A,n=1):
        return self.db.execute(I["insert"],(s,f"00000000-0000-0000-0000-{n:012d}",*K,"WEEK","DELTA_PEAK","1.0854",T,T,T,"synthetic",*K))
    def decide(self,action="APPROVED",at=T):return self.db.execute(R["decision"],(1,O,action,at,"synthetic"))
    def test_default_closed(self):
        self.assertEqual(self.q("contributor",A,EA,"READ"),[])
        self.assertEqual(self.q("owner",O,EO,"RECOVERY"),[])
        with self.assertRaises(sqlite3.IntegrityError):self.insert()
    def test_roles_and_tags_immutable(self):
        self.gates(1,1,1)
        self.assertEqual(self.q("contributor",A,EA,"READ")[0]["slot"],"friend-a")
        for s,e in [(A,EB),(O,EO),(B,EA)]:self.assertEqual(self.q("contributor",s,e,"READ"),[])
        self.assertEqual(self.q("owner",A,EA,"WRITE"),[])
        for sql in ["UPDATE lab_identities SET email_tag='x'","UPDATE lab_identities SET slot='friend-b'","DELETE FROM lab_identities","UPDATE lab_owner SET subject='x'"]:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
        self.db.execute("DELETE FROM lab_catalog")
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(),[])
    def test_cross_role_and_fixture_denied(self):
        for sql,args in [
            ("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",(O,"4"*64)),
            ("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",("d"*64,EO)),
            ("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",("fixture-a","4"*64))]:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql,args)
    def test_cross_role_trigger_before_slot_conflict(self):
        db=sqlite3.connect(":memory:")
        try:
            db.executescript((ROOT/"d1_access_candidate.sql").read_text())
            db.execute("INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)",(O,EO))
            for s,e in [(O,EA),(A,EO)]:
                with self.assertRaisesRegex(sqlite3.IntegrityError,"role_conflict"):
                    db.execute("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",(s,e))
        finally:db.close()
        db=sqlite3.connect(":memory:")
        try:
            db.executescript((ROOT/"d1_access_candidate.sql").read_text())
            db.execute("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",(A,EA))
            with self.assertRaisesRegex(sqlite3.IntegrityError,"role_conflict"):
                db.execute("INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)",(O,EA))
        finally:db.close()
    def test_isolation_and_gate_split(self):
        self.gates(1,0,0);self.insert(A,1);self.insert(B,2)
        self.assertEqual(self.q("receipts",A,EA,0),[])
        self.decide()
        self.gates(0,1,0)
        ra=self.q("receipts",A,EA,0);rb=self.q("receipts",B,EB,0)
        self.assertEqual([r["id"] for r in ra],[1]);self.assertEqual([r["id"] for r in rb],[2])
        self.assertEqual(ra[0]["status"],"APPROVED");self.assertNotIn("reason",ra[0].keys())
        self.assertEqual(self.q("receipts",A,EB,0),[])
        self.assertEqual(self.q("queue",0,A,EA),[])
        self.assertEqual(len(self.q("queue",0,O,EO)),2)
        self.assertEqual(self.q("history",1,O,EO),[])
        with self.assertRaises(sqlite3.IntegrityError):self.decide("REVOKED",L)
        self.gates(0,0,1);self.decide("REVOKED",L)
        self.assertEqual([x["action"] for x in self.q("history",1,O,EO)],["APPROVED","REVOKED"])
    def test_revocation_atomic_and_no_rebind(self):
        self.gates(1,1,1);self.insert();self.decide()
        self.gates(0,0,1);self.q("revoke",O,L,"friend-a",O,EO)
        self.assertEqual(self.db.execute("SELECT revoked FROM lab_identities WHERE subject=?",(A,)).fetchone()[0],1)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_identity_revocations").fetchone()[0],1)
        self.gates(1,1,1)
        self.assertEqual(self.q("receipts",A,EA,0),[])
        self.assertEqual(self.q("contributor",A,EA,"WRITE"),[])
        with self.assertRaises(sqlite3.IntegrityError):self.insert(A,3)
        for sql in ["UPDATE lab_identities SET revoked=0 WHERE subject='"+A+"'","DELETE FROM lab_identity_revocations","UPDATE lab_identity_revocations SET at_utc='"+T+"'"]:
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
        self.assertEqual(self.q("history",1,O,EO)[0]["action"],"APPROVED")
        self.decide("REVOKED",L)
    def test_recovery_owner_required(self):
        self.gates(1,1,0)
        with self.assertRaises(sqlite3.IntegrityError):self.q("revoke",O,L,"friend-a",O,EO)
        self.gates(0,0,1);self.q("revoke",O,L,"friend-a",A,EA)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_identity_revocations").fetchone()[0],0)
        self.db.execute("UPDATE lab_owner SET revoked=1")
        self.q("revoke",O,L,"friend-a",O,EO)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_identity_revocations").fetchone()[0],0)
    def test_intent_generation_and_burn(self):
        g="1"*32; pin="2"*64; exp=int(time.time())+60
        self.gates(1,1,1)
        self.assertEqual(self.db.execute(N["generation"],(g,pin)).fetchall(),[])
        self.db.execute("INSERT INTO lab_generation VALUES(1,?,?)",(g,pin))
        a=(g,pin,"WRITE","CONTRIBUTOR",A,EA,"CONTRIBUTOR",A,EA)
        self.assertEqual(self.db.execute(N["permission"],a).fetchone()["allowed"],1)
        n="3"*32
        data=(n,A,"WRITE","CONTRIBUTOR",exp,g,pin,exp,*a[2:])
        self.assertEqual(self.db.execute(N["burn"],data).rowcount,1)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute(N["burn"],data)
        self.assertEqual(self.db.execute("SELECT count(*) FROM lab_intent_used").fetchone()[0],1)
        for expiry,gen,tag in [(exp-120,g,EA),(exp,"4"*32,EA),(exp,g,EB)]:
            d=("5"*32,A,"WRITE","CONTRIBUTOR",expiry,gen,pin,expiry,"WRITE","CONTRIBUTOR",A,tag,"CONTRIBUTOR",A,tag)
            self.assertEqual(self.db.execute(N["burn"],d).rowcount,0)
        self.db.execute("UPDATE lab_identities SET revoked=1 WHERE subject=?",(A,))
        self.assertEqual(self.db.execute(N["burn"],("6"*32,*data[1:])).rowcount,0)
    def test_concurrent_nonce_one_winner(self):
        with tempfile.TemporaryDirectory() as d:
            path=str(Path(d)/"fixture.sqlite")
            db=sqlite3.connect(path);db.executescript((ROOT/"d1_access_candidate.sql").read_text())
            db.execute("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",(A,EA))
            db.execute("UPDATE lab_state SET write_enabled=1")
            g="1"*32;pin="2"*64;db.execute("INSERT INTO lab_generation VALUES(1,?,?)",(g,pin));db.commit();db.close()
            exp=int(time.time())+60
            data=("3"*32,A,"WRITE","CONTRIBUTOR",exp,g,pin,exp,"WRITE","CONTRIBUTOR",A,EA,"CONTRIBUTOR",A,EA)
            def go(_):
                c=sqlite3.connect(path,timeout=5)
                try:
                    with c:return c.execute(N["burn"],data).rowcount
                except sqlite3.IntegrityError:return 0
                finally:c.close()
            with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:self.assertEqual(sorted(pool.map(go,range(2))),[0,1])
    def test_http_node(self):
        subprocess.run(["node",str(ROOT/"test_http_access_candidate.mjs")],check=True,timeout=20)
    def test_node(self):
        subprocess.run(["node",str(ROOT/"test_d1_access_candidate.mjs")],check=True,timeout=20)

if __name__=="__main__":unittest.main()
