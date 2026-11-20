# REMURA Contributors v0.19 LAB — 16/11/2026 01:16 CET
import re
import sqlite3
import subprocess
import unittest
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).parent
def queries(name):
    return dict(re.findall(r'^\s*(\w+):"([^"]+)"', (ROOT/name).read_text(),re.M))
I=queries("d1_lab_adapter.mjs"); R=queries("d1_lab_review.mjs")
T="2026-11-16T00:16:00Z"; L="2026-11-16T00:17:00Z"
OWNER="fixture-owner"; A="fixture-a"; B="fixture-b"
K=("EURUSD","OANDA","EURUSD","SPOT","")

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.row_factory=sqlite3.Row
        self.db.executescript((ROOT/"d1_lab_schema.sql").read_text())
        self.db.execute("INSERT INTO lab_owner(id,subject) VALUES(1,?)",(OWNER,))
        self.db.executemany("INSERT INTO lab_identities(subject,slot) VALUES(?,?)",[(A,"friend-a"),(B,"friend-b")])
        self.db.execute("INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)",K+("fixture-fx",))
        self.db.execute("UPDATE lab_state SET enabled=1")
        for n,s in enumerate((A,B),1):
            self.db.execute(I["insert"],(s,str(UUID(int=n)),*K,"WEEK","DELTA_PEAK","1.0854",T,T,T,"synthetic",*K))
    def tearDown(self): self.db.close()
    def decide(self,id=1,action="APPROVED",at=T,owner=OWNER,reason="synthetic reason"):
        return self.db.execute(R["decision"],(id,owner,action,at,reason))
    def list(self,s):
        return [dict(r) for r in self.db.execute(I["receipts"],(s,0))]
    def queue(self,s=OWNER):return [dict(r) for r in self.db.execute(R["queue"],(0,s))]
    def history(self,id=1,s=OWNER):return [dict(r) for r in self.db.execute(R["history"],(id,s))]
    def deny(self,*args,**kw):
        with self.assertRaises(sqlite3.IntegrityError): self.decide(*args,**kw)
    def test_approval_revoke_and_receipt_privacy(self):
        self.assertEqual(self.queue()[0]["status"],"UNREVIEWED")
        self.decide()
        self.assertEqual(self.queue()[0]["status"],"APPROVED")
        a=self.list(A); self.assertEqual(a[0]["status"],"APPROVED")
        self.assertNotIn("reason",a[0]); self.assertNotIn("owner",a[0]); self.assertNotIn("subject",a[0])
        self.assertEqual(self.list(B)[0]["status"],"UNREVIEWED")
        self.decide(action="REVOKED",at=L)
        self.assertEqual(self.list(A)[0]["status"],"REVOKED")
        self.assertEqual([r["action"] for r in self.history()],["APPROVED","REVOKED"])
        self.deny(action="APPROVED",at=L)
    def test_reject_terminal_and_no_double_review(self):
        self.deny(action="REVOKED")
        self.decide(action="REJECTED")
        for action in ("APPROVED","REJECTED","REVOKED"): self.deny(action=action)
        self.assertEqual(len(self.history()),1)
    def test_owner_and_global_gate(self):
        self.deny(owner=A); self.deny(owner="fixture-other")
        self.assertEqual(self.queue(A),[]);self.assertEqual(self.history(s=A),[])
        self.db.execute("UPDATE lab_state SET enabled=0")
        self.deny(); self.assertEqual(self.queue(),[])
        self.db.execute("UPDATE lab_state SET enabled=1")
        self.db.execute("UPDATE lab_owner SET revoked=1")
        self.deny(); self.assertEqual(self.queue(),[])
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("UPDATE lab_owner SET revoked=0")
        with self.assertRaises(sqlite3.IntegrityError): self.db.execute("DELETE FROM lab_owner")
    def test_source_recheck_and_revocation_after_approval(self):
        self.decide()
        self.db.execute("UPDATE lab_identities SET revoked=1 WHERE subject=?",(A,))
        self.db.execute("UPDATE lab_catalog SET active=0")
        self.deny(id=2)
        self.decide(action="REVOKED",at=L)
        self.assertEqual(self.list(A),[])
        self.decide(id=2,action="REJECTED",at=L)
    def test_revoked_author_no_new_approval(self):
        self.db.execute("UPDATE lab_identities SET revoked=1 WHERE subject=?",(A,))
        self.deny()
        self.assertEqual(self.history(),[])
    def test_chronology_orphan_and_append_only(self):
        self.deny(at="2026-11-16T00:15:00Z");self.deny(id=999);self.deny(reason="")
        self.decide(at=L);self.deny(id=2,at=T)
        for q in ("UPDATE lab_reviews SET reason='changed'","DELETE FROM lab_reviews"):
            with self.assertRaises(sqlite3.IntegrityError): self.db.execute(q)
        self.assertEqual(self.db.execute("PRAGMA foreign_key_check").fetchall(),[])
    def test_node_adapter(self):
        subprocess.run(["node",str(ROOT/"test_d1_lab_review.mjs")],check=True,timeout=20)

if __name__=="__main__":unittest.main()
