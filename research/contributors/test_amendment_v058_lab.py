# REMURA Contributors v0.58 LAB — isolated SQLite test-only controls
import sqlite3
import unittest
from amendment_v058_lab import AmendmentLab, Denied

T='2026-11-21T06:00:00Z'
NEXT='2026-11-21T06:01:00Z'
def rid(n): return f'00000000-0000-4000-8000-{n:012x}'
def payload(price='1.12345',note='review level',observed='2026-11-21T05:50:00Z'):
    return dict(market='FX',provider='LAB',ticker='EURUSD',product='SPOT',contract='',period='DAY',kind='DELTA_PEAK',price=price,anchor_utc='2026-11-21T00:00:00Z',observed_utc=observed,note=note)

class AmendTests(unittest.TestCase):
    def setUp(self): self.lab=AmendmentLab()
    def tearDown(self): self.lab.close()
    def create(self,actor='fixture-a',n=1,p=None,base=None):
        return self.lab.submit(actor,rid(n),p or payload(),T,base)
    def denied(self,fn):
        with self.assertRaises(Denied): fn()

    def test_01_new_entry_is_pending(self):
        r=self.create();self.assertEqual(r['state'],'PENDING_REVIEW');self.assertEqual(self.lab.own_receipts('fixture-a'),[(1,None,'UNREVIEWED')])
    def test_02_own_amendment_is_append_only(self):
        a=self.create();b=self.create(n=2,p=payload('1.23456'),base=a['id'])
        self.assertEqual(b['id'],2);self.assertEqual(self.lab.own_receipts('fixture-a'),[(1,None,'UNREVIEWED'),(2,1,'UNREVIEWED')])
    def test_03_cross_user_amendment_denied(self):
        a=self.create();self.denied(lambda:self.create('fixture-b',2,payload('5'),a['id']))
        self.assertEqual(self.lab.own_receipts('fixture-b'),[])
    def test_04_unknown_parent_denied(self):self.denied(lambda:self.create(n=3,base=999))
    def test_05_chaining_parent_refused(self):
        a=self.create();b=self.create(n=2,base=a['id']);self.denied(lambda:self.create(n=3,base=b['id']))
    def test_06_exact_idempotency(self):
        x=self.create();y=self.create();self.assertTrue(y['duplicate']);self.assertEqual(y['id'],x['id']);self.assertEqual(len(self.lab.owner_queue('fixture-owner')),1)
    def test_07_same_request_changed_price_denied(self):
        self.create();self.denied(lambda:self.create(p=payload('9.1')))
    def test_08_replay_with_new_parent_denied(self):
        self.create();self.denied(lambda:self.create(n=1,base=1))
    def test_09_owner_cannot_submit_as_contributor(self):self.denied(lambda:self.create('fixture-owner'))
    def test_10_owner_only_review(self):
        self.create();self.denied(lambda:self.lab.review('fixture-a',1,'APPROVED',NEXT))
    def test_11_amendment_approval_needs_approved_parent(self):
        self.create();self.create(n=2,base=1);self.denied(lambda:self.lab.review('fixture-owner',2,'APPROVED',NEXT))
        self.assertEqual(self.lab.review('fixture-owner',1,'APPROVED',NEXT)['action'],'APPROVED')
        self.lab.review('fixture-owner',2,'APPROVED',NEXT)
    def test_12_only_one_approved_sibling(self):
        self.create();self.create(n=2,base=1);self.create(n=3,base=1)
        self.lab.review('fixture-owner',1,'APPROVED',NEXT)
        self.lab.review('fixture-owner',2,'APPROVED',NEXT)
        self.denied(lambda:self.lab.review('fixture-owner',3,'APPROVED',NEXT))
        self.lab.review('fixture-owner',3,'REJECTED',NEXT)
    def test_13_double_review_denied(self):
        self.create();self.lab.review('fixture-owner',1,'REJECTED',NEXT)
        self.denied(lambda:self.lab.review('fixture-owner',1,'APPROVED',NEXT))
    def test_14_unreviewed_and_rejected_records_remain(self):
        self.create();self.lab.review('fixture-owner',1,'REJECTED',NEXT);self.assertEqual(self.lab.own_receipts('fixture-a'),[(1,None,'REJECTED')])
    def test_15_original_entries_immutable_sql(self):
        self.create()
        with self.assertRaises(sqlite3.IntegrityError):self.lab.db.execute("UPDATE entries SET subject='fixture-b' WHERE id=1")
    def test_16_reviews_immutable_sql(self):
        self.create();self.lab.review('fixture-owner',1,'APPROVED',NEXT)
        with self.assertRaises(sqlite3.IntegrityError):self.lab.db.execute('DELETE FROM reviews WHERE entry_id=1')
    def test_17_revoke_blocks_future_contribution(self):
        self.create();self.lab.revoke('fixture-owner','fixture-a');self.denied(lambda:self.create(n=2))
    def test_18_revoke_blocks_own_receipts(self):
        self.create();self.lab.revoke('fixture-owner','fixture-a');self.denied(lambda:self.lab.own_receipts('fixture-a'))
    def test_19_contributor_cannot_revoke(self):
        self.denied(lambda:self.lab.revoke('fixture-a','fixture-b'))
    def test_20_actor_cannot_view_other_receipts(self):
        self.create();self.assertEqual(self.lab.own_receipts('fixture-b'),[])
    def test_21_owner_queue_only_owner(self):
        self.create();self.denied(lambda:self.lab.owner_queue('fixture-a'))
    def test_22_note_limit_and_control_char(self):
        self.denied(lambda:self.create(p=payload(note='x'*281)))
        self.denied(lambda:self.create(p=payload(note='hello\nworld')))
    def test_23_clock_future_denied(self):
        self.denied(lambda:self.create(p=payload(observed='2026-11-22T00:00:00Z')))
    def test_24_price_negative_or_malformed(self):
        self.denied(lambda:self.create(p=payload('0')))
        self.denied(lambda:self.create(p=payload('3e4')))
    def test_25_unknown_field_rejected(self):
        x=payload();x['role']='OWNER';self.denied(lambda:self.create(p=x))
    def test_26_period_not_allowlisted(self):
        x=payload();x['period']='NEXT_MONTH';self.denied(lambda:self.create(p=x))
    def test_27_no_cross_user_request_id_collision(self):
        a=self.create();b=self.create('fixture-b');self.assertNotEqual(a['id'],b['id'])
    def test_28_invalid_parent_type_denied(self):
        self.denied(lambda:self.create(base=True))
    def test_29_price_decimal_normalization(self):
        a=self.create(p=payload('1,2300'));self.assertEqual(a['id'],1)
        b=self.create(p=payload('1.23'));self.assertTrue(b['duplicate'])
    def test_30_revoke_cannot_be_undone(self):
        self.lab.revoke('fixture-owner','fixture-b');self.denied(lambda:self.lab.revoke('fixture-owner','fixture-b'))
    def test_31_owner_rejects_after_contributor_revocation(self):
        self.create();self.lab.revoke('fixture-owner','fixture-a');self.assertEqual(self.lab.review('fixture-owner',1,'REJECTED',NEXT)['action'],'REJECTED')
    def test_33_revoked_source_cannot_be_approved(self):
        self.create();self.lab.revoke('fixture-owner','fixture-a');self.denied(lambda:self.lab.review('fixture-owner',1,'APPROVED',NEXT))
    def test_32_review_clock_before_creation_denied(self):
        self.create();self.denied(lambda:self.lab.review('fixture-owner',1,'APPROVED','2026-11-21T05:59:59Z'))

if __name__=='__main__':unittest.main()
