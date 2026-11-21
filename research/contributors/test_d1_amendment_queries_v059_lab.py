# REMURA Contributors v0.59 LAB -- query contract tests; no real identity or D1.
import re
import sqlite3
import unittest
from pathlib import Path
from test_d1_amendment_v059_lab import A,B,O,EA,EB,EO,T,BEFORE,AFTER,NEXT,K,ORIGINAL,FALLBACK
ROOT=Path(__file__).parent

def queries():
    source=(ROOT/'d1_amendment_queries_v059_lab.mjs').read_text()
    found=dict(re.findall(r'^\s*(\w+):"([^"]+)",?$',source,re.M))
    if len(found)!=5: raise RuntimeError(f'Unexpected query contract: {list(found)}')
    return found

Q=queries()
class AmendmentQueriesTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript((ORIGINAL if ORIGINAL.exists() else FALLBACK).read_text())
        self.db.executescript((ROOT/'d1_amendment_v059_lab.sql').read_text())
        self.db.execute('INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)',(O,EO))
        self.db.executemany('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)',[(A,EA,'friend-a'),(B,EB,'friend-b')])
        self.db.execute('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)',K+('fixture-fx',))
        self.db.execute('UPDATE lab_state SET write_enabled=1,read_enabled=1,recovery_enabled=1')
        for n,s in enumerate((A,B),1):
            self.db.execute('''INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,
                price,anchor_utc,observed_utc,received_utc,note,source_group) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                (s,f'00000000-0000-4000-8000-{n:012d}',*K,'DAY','DELTA_PEAK','1.123',BEFORE,BEFORE,T,'fixture','fixture-fx'))
        self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'APPROVED',T,'fixture'))
    def tearDown(self):self.db.close()
    def insert(self,actor=A,tag=EA,source=1,n=3,price='1.234'):
        return self.db.execute(Q['submit'],(actor,f'00000000-0000-4000-8000-{n:012d}',price,T,AFTER,'note',source,actor,tag)).rowcount
    def approve(self,id=1,action='APPROVED',owner=O,email=EO,at=NEXT):
        return self.db.execute(Q['review'],(id,action,at,'fixture',owner,email)).rowcount
    def own(self,s=A,tag=EA):return self.db.execute(Q['own'],(s,tag,0)).fetchall()
    def approved(self,s=A,tag=EA):return self.db.execute(Q['approved'],(s,tag)).fetchall()
    def denied(self,fn):
        with self.assertRaises(sqlite3.IntegrityError):fn()

    def test_01_prepared_submit_own(self):self.assertEqual(self.insert(),1)
    def test_02_wrong_subject_blocks_submit(self):self.assertEqual(self.insert(actor=B,tag=EB,source=1),0)
    def test_03_wrong_email_tag_blocks_submit(self):self.assertEqual(self.insert(tag=EB),0)
    def test_04_unapproved_original_blocks(self):self.denied(lambda:self.insert(actor=B,tag=EB,source=2))
    def test_05_own_projection_is_private(self):
        self.insert();self.assertEqual(len(self.own()),1);self.assertEqual(self.own(B,EB),[])
    def test_06_own_projection_wrong_email_blocked(self):
        self.insert();self.assertEqual(self.own(A,EB),[])
    def test_07_own_projection_read_gate(self):
        self.insert();self.db.execute('UPDATE lab_state SET read_enabled=0');self.assertEqual(self.own(),[])
    def test_08_owner_queue_authorized(self):
        self.insert();self.assertEqual(len(self.db.execute(Q['ownerQueue'],(0,O,EO)).fetchall()),1)
    def test_09_owner_queue_other_role_denied(self):
        self.insert();self.assertEqual(self.db.execute(Q['ownerQueue'],(0,A,EA)).fetchall(),[])
    def test_10_owner_queue_wrong_email_denied(self):
        self.insert();self.assertEqual(self.db.execute(Q['ownerQueue'],(0,O,EA)).fetchall(),[])
    def test_11_owner_queue_omits_reviewed(self):
        self.insert();self.approve();self.assertEqual(self.db.execute(Q['ownerQueue'],(0,O,EO)).fetchall(),[])
    def test_12_prepared_review_checks_owner(self):
        self.insert();self.assertEqual(self.approve(owner=A,email=EA),0)
    def test_13_prepared_review_accepts_owner(self):
        self.insert();self.assertEqual(self.approve(),1)
    def test_14_published_view_only_approved_original(self):
        self.assertEqual([r[0] for r in self.approved()],[1])
    def test_15_approved_amendment_replaces_price(self):
        self.insert();self.approve();self.assertEqual(self.approved()[0][8],'1.234')
    def test_16_unreviewed_amendment_never_replaces_price(self):
        self.insert();self.assertEqual(self.approved()[0][8],'1.123')
    def test_17_rejected_amendment_never_replaces_price(self):
        self.insert();self.approve(action='REJECTED');self.assertEqual(self.approved()[0][8],'1.123')
    def test_18_revoked_amendment_restores_original(self):
        self.insert();self.approve();self.approve(action='REVOKED',at='2026-11-21T06:33:00Z');self.assertEqual(self.approved()[0][8],'1.123')
    def test_19_revoked_original_hidden(self):
        self.insert();self.approve();self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'REVOKED',AFTER,'fixture'))
        self.assertEqual(self.approved(),[])
    def test_20_revoked_contributor_levels_hidden(self):
        self.insert();self.db.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,));self.assertEqual(self.approved(B,EB),[])
    def test_21_revoked_viewer_denied_all(self):
        self.db.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(B,));self.assertEqual(self.approved(B,EB),[])
    def test_22_invalid_viewer_email_denied(self):self.assertEqual(self.approved(A,EB),[])
    def test_23_read_gate_blocks_approved_projection(self):
        self.db.execute('UPDATE lab_state SET read_enabled=0');self.assertEqual(self.approved(),[])
    def test_24_inactive_mapping_hides_approved_projection(self):
        self.db.execute('UPDATE lab_catalog SET active=0');self.assertEqual(self.approved(),[])
    def test_25_no_private_notes_or_subjects_in_approved_projection(self):
        self.insert();self.approve();self.assertEqual(len(self.approved()[0]),10)

if __name__=='__main__':unittest.main()
