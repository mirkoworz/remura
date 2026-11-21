# REMURA Contributors v0.59 LAB -- additive SQL only, no cloud resources.
# When run inside real repository: exercises original d1_access_candidate.sql.
# When run standalone: reduced local surrogate explicitly NOT full integration.
import sqlite3
import unittest
from pathlib import Path

ROOT = Path(__file__).parent
ORIGINAL = ROOT / 'd1_access_candidate.sql'
FALLBACK = ROOT / 'd1_base_fixture.sql'
BASE = ORIGINAL if ORIGINAL.exists() else FALLBACK
A,B,O='a'*64,'b'*64,'c'*64
EA,EB,EO='1'*64,'2'*64,'3'*64
T='2026-11-21T06:30:00Z'
BEFORE='2026-11-21T06:20:00Z'
AFTER='2026-11-21T06:31:00Z'
NEXT='2026-11-21T06:32:00Z'
K=('EURUSD','OANDA','EURUSD','SPOT','')

class CandidateAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(':memory:')
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript(BASE.read_text())
        self.db.executescript((ROOT/'d1_amendment_v059_lab.sql').read_text())
        self.db.execute('INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)',(O,EO))
        self.db.executemany('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)',[(A,EA,'friend-a'),(B,EB,'friend-b')])
        self.db.execute('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)',K+('fixture-fx',))
        self.state(w=1,r=1,h=1)
        for i,s in enumerate((A,B),1):
            self.db.execute('''INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,
              price,anchor_utc,observed_utc,received_utc,note,source_group)
              VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',(s,f'00000000-0000-4000-8000-{i:012d}',*K,'DAY','DELTA_PEAK','1.123',BEFORE,BEFORE,T,'fixture','fixture-fx'))
        self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'APPROVED',T,'fixture'))
    def tearDown(self): self.db.close()
    def state(self,w=0,r=0,h=0):
        self.db.execute('UPDATE lab_state SET write_enabled=?,read_enabled=?,recovery_enabled=?',(w,r,h))
    def approve_b(self):
        self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(2,O,'APPROVED',T,'fixture'))
    def amend(self,actor=A,source=1,n=3,price='1.234',obs=T,received=AFTER,note='fixture'):
        return self.db.execute('''INSERT INTO lab_level_amendments_v059
            (subject,source_entry_id,request_id,price,observed_utc,received_utc,note)
            VALUES(?,?,?,?,?,?,?)''',(actor,source,f'00000000-0000-4000-8000-{n:012d}',price,obs,received,note)).lastrowid
    def review(self,amendment=1,action='APPROVED',owner=O,at=NEXT,reason='fixture'):
        return self.db.execute('''INSERT INTO lab_level_amendment_reviews_v059
           (amendment_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)''',(amendment,owner,action,at,reason))
    def denied(self,action):
        with self.assertRaises(sqlite3.IntegrityError): action()

    def test_01_additive_and_source_entry_intact(self):
        self.assertEqual(self.amend(),1)
        self.assertEqual(self.db.execute('SELECT price FROM lab_entries WHERE id=1').fetchone()[0],'1.123')
    def test_02_default_write_gate_blocks(self):
        self.state(w=0);self.denied(self.amend)
    def test_03_unapproved_parent_blocks(self): self.denied(lambda:self.amend(source=2,actor=B))
    def test_04_approved_b_parent_works(self):
        self.approve_b();self.assertEqual(self.amend(actor=B,source=2),1)
    def test_05_cross_user_parent_blocks(self): self.denied(lambda:self.amend(actor=B,source=1))
    def test_06_owner_cannot_pose_as_contributor(self): self.denied(lambda:self.amend(actor=O))
    def test_07_unlisted_actor_blocks(self): self.denied(lambda:self.amend(actor='d'*64))
    def test_08_revoked_actor_blocks(self):
        self.db.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,));self.denied(self.amend)
    def test_09_inactive_catalog_blocks(self):
        self.db.execute('UPDATE lab_catalog SET active=0');self.denied(self.amend)
    def test_10_original_revoked_blocks(self):
        self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'REVOKED',AFTER,'fixture'))
        self.denied(self.amend)
    def test_11_observation_before_anchor_blocks(self): self.denied(lambda:self.amend(obs='2026-11-21T06:19:00Z'))
    def test_12_observation_after_receipt_blocks(self): self.denied(lambda:self.amend(obs=NEXT))
    def test_13_received_before_source_blocks(self): self.denied(lambda:self.amend(received=BEFORE))
    def test_14_duplicate_actor_request_id_blocks(self):
        self.amend();self.denied(self.amend)
    def test_15_same_request_id_for_different_authors_allowed(self):
        self.approve_b();self.amend();self.amend(actor=B,source=2)
        self.assertEqual(self.db.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],2)
    def test_16_zero_price_denied(self): self.denied(lambda:self.amend(price='0'))
    def test_17_negative_or_scientific_price_denied(self):
        self.denied(lambda:self.amend(price='-1.2'));self.denied(lambda:self.amend(price='1e4'))
    def test_18_invalid_number_format_denied(self):
        self.denied(lambda:self.amend(price='1..2'));self.denied(lambda:self.amend(price='.5'))
    def test_19_note_too_long(self): self.denied(lambda:self.amend(note='x'*281))
    def test_20_control_character_note(self): self.denied(lambda:self.amend(note='a\nb'))
    def test_21_wrong_utc_format(self): self.denied(lambda:self.amend(obs='2026/11/21 06:30:00'))
    def test_22_entries_immutable(self):
        self.amend();self.denied(lambda:self.db.execute("UPDATE lab_level_amendments_v059 SET subject=? WHERE id=1",(B,)))
        self.denied(lambda:self.db.execute('DELETE FROM lab_level_amendments_v059 WHERE id=1'))
    def test_23_owner_approval(self):
        self.amend();self.review();self.assertEqual(self.db.execute('SELECT action FROM lab_level_amendment_reviews_v059').fetchone()[0],'APPROVED')
    def test_24_non_owner_review_blocks(self): self.amend();self.denied(lambda:self.review(owner=A))
    def test_25_revoked_owner_review_blocks(self):
        self.amend();self.db.execute('UPDATE lab_owner SET revoked=1 WHERE id=1');self.denied(self.review)
    def test_26_approved_only_if_contributor_active(self):
        self.amend();self.db.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,));self.denied(self.review)
    def test_27_approved_only_if_parent_approved(self):
        self.amend();self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'REVOKED',AFTER,'fixture'))
        self.denied(self.review)
    def test_28_second_active_approved_conflicts(self):
        self.amend();self.amend(n=4);self.review(1)
        self.denied(lambda:self.review(2))
    def test_29_rejected_amendment_does_not_block_later_approval(self):
        self.amend();self.amend(n=4);self.review(1,'REJECTED');self.review(2)
    def test_30_revoked_amendment_allows_later_approval(self):
        self.amend();self.amend(n=4);self.review(1)
        self.review(1,'REVOKED',at='2026-11-21T06:33:00Z')
        self.review(2,'APPROVED',at='2026-11-21T06:34:00Z')
    def test_31_double_approval_or_rejected_after_approval_blocks(self):
        self.amend();self.review();self.denied(self.review);self.denied(lambda:self.review(1,'REJECTED'))
    def test_32_revoke_requires_approval(self):
        self.amend();self.denied(lambda:self.review(1,'REVOKED'))
    def test_33_recovery_gate_required_for_revoke(self):
        self.amend();self.review();self.state(w=1,r=1,h=0)
        self.denied(lambda:self.review(1,'REVOKED'))
    def test_34_review_write_gate_required(self):
        self.amend();self.state(w=0,r=1,h=1);self.denied(self.review)
    def test_35_review_timestamp_and_reason_checked(self):
        self.amend();self.denied(lambda:self.review(at=BEFORE));self.denied(lambda:self.review(reason=''))
    def test_36_review_immutable(self):
        self.amend();self.review();self.denied(lambda:self.db.execute('DELETE FROM lab_level_amendment_reviews_v059'))
        self.denied(lambda:self.db.execute("UPDATE lab_level_amendment_reviews_v059 SET action='REJECTED'"))
    def test_37_personal_receipts_must_be_scoped_in_adapter(self):
        self.approve_b();self.amend();self.amend(actor=B,source=2)
        safe='SELECT id,source_entry_id FROM lab_level_amendments_v059 WHERE subject=? ORDER BY id'
        self.assertEqual(self.db.execute(safe,(A,)).fetchall(),[(1,1)])
        self.assertEqual(self.db.execute(safe,(B,)).fetchall(),[(2,2)])
    def test_38_bounded_10_daily_amendments(self):
        for n in range(3,13):self.amend(n=n)
        self.denied(lambda:self.amend(n=13))
    def test_39_closed_sql_has_no_deploy_metadata(self):
        sql=(ROOT/'d1_amendment_v059_lab.sql').read_text()
        self.assertNotIn('CREATE WORKER',sql)
        self.assertNotIn('DROP TABLE lab_entries',sql)
        self.assertNotIn('ALTER TABLE lab_reviews',sql)
    def test_40_all_fks_valid(self):
        self.amend();self.review();self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])

if __name__=='__main__': unittest.main()
