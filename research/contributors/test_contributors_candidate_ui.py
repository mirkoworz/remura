# REMURA Contributors v0.25 LAB — 16/11/2026 07:19 CET
import sqlite3,subprocess,unittest
from pathlib import Path
from test_d1_lab_review import queries
ROOT=Path(__file__).parent
Q=queries("d1_access_candidate.mjs")
class CandidateUITests(unittest.TestCase):
    def test_profile_catalog_permissions(self):
        db=sqlite3.connect(":memory:")
        try:
            db.executescript((ROOT/"d1_access_candidate.sql").read_text())
            a,e,o,t="a"*64,"b"*64,"c"*64,"d"*64
            db.execute("INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,'friend-a')",(a,e))
            db.execute("INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)",(o,t))
            db.execute("INSERT INTO lab_catalog VALUES('EURUSD','OANDA','EURUSD','SPOT','','fixture',1)")
            def profile(s,k):return db.execute(Q["profile"],(s,k,s,k)).fetchall()
            def cat(s,k):return db.execute(Q["catalog"],(s,k)).fetchall()
            self.assertEqual(profile(a,e),[]);self.assertEqual(cat(a,e),[])
            db.execute("UPDATE lab_state SET write_enabled=1")
            self.assertEqual(profile(a,e),[("CONTRIBUTOR","friend-a",1,0,0)])
            self.assertEqual(profile(o,t),[("OWNER","owner",1,0,0)])
            self.assertEqual(cat(o,t),[]);self.assertEqual(cat(a,t),[])
            self.assertEqual(cat(a,e),[("EURUSD","OANDA","EURUSD","SPOT","")])
            db.execute("UPDATE lab_state SET write_enabled=0,recovery_enabled=1")
            self.assertEqual(profile(o,t),[("OWNER","owner",0,0,1)]);self.assertEqual(profile(a,e),[])
            db.execute("UPDATE lab_state SET read_enabled=1")
            db.execute("UPDATE lab_identities SET revoked=1")
            self.assertEqual(profile(a,e),[])
        finally:db.close()
    def test_client_node(self):
        subprocess.run(["node",str(ROOT/"test_contributors_candidate_client.mjs")],check=True,timeout=20)

    def test_candidate_dom(self):
        subprocess.run(["node",str(ROOT/"test_contributors_candidate_dom.mjs")],check=True,timeout=20)

    def test_direct_candidate_worker(self):
        subprocess.run(["node",str(ROOT/"test_contributors_worker_candidate.mjs")],check=True,timeout=20)
