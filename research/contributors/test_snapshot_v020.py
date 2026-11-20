# REMURA Experience v0.20 LAB — 20/11/2026 18:59 CET
import json
import tempfile
import unittest
import sqlite3
from pathlib import Path
from snapshot_v020 import SnapshotV020
from snapshot_store_v019 import encode,sha,WKEY
from test_snapshot_store_v019 import data, NOW, OWNER, USER, YES, CLOCK
import witness_v016 as witness

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.f=SnapshotV020(Path(self.tmp.name)/'f');self.f.initialize_snapshot()
    def tearDown(self):self.tmp.cleanup()
    def pub(self,**kw):return self.f.publish_snapshot(**(dict(expected=0,data=data(),auth=OWNER,approve=YES,clock=CLOCK)|kw))
    def view(self,clock=CLOCK,auth=USER):
        r=self.f.deliver(auth,clock);return None if r is None else json.loads(r['body'])
    def seed(self):self.assertEqual(self.pub(),'PUBLISHED')
    def pairclock(self,a,b):
        it=iter((a,b));return lambda:next(it)
    def pending(self,stage='archive'):
        self.seed()
        with self.f._open() as (_,__,w):self.prior=witness.read(w,WKEY)
        x=data();x['prices'][0]['price']=1.5
        self.wanted=sha(encode({'schema':'REMURA_SHARED_FIXTURE_V1','revision':2,**x}))
        self.assertEqual(self.pub(expected=1,data=x,interrupt=stage),'INTERRUPTED')
        self.assertIsNone(self.view())
    def recover(self,**kw):return self.f.recover_snapshot(**(dict(prior=self.prior,wanted=self.wanted,auth=OWNER,approve=YES,clock=CLOCK)|kw))
    def test_clock_advance(self):
        self.seed();v=self.view(self.pairclock(NOW,NOW+20));self.assertEqual(v['schema'],'REMURA_SHARED_VIEW_FIXTURE_V2');self.assertEqual(v['prices'][0]['price'],1.25);self.assertEqual(len(v['cot']),28)
    def test_clock_backward(self):self.seed();self.assertIsNone(self.view(self.pairclock(NOW+1,NOW)))
    def test_window_limit(self):self.seed();self.assertIsNone(self.view(self.pairclock(NOW,NOW+5001)))
    def test_window_boundary(self):self.seed();self.assertIsNotNone(self.view(self.pairclock(NOW,NOW+5000)))
    def test_snapshot_expiry_crossing(self):self.seed();self.assertIsNone(self.view(self.pairclock(NOW+900000,NOW+900001)))
    def test_price_expiry_crossing(self):
        x=data();x['prices'][0]['observed_at']='2026-11-20T15:45:00Z';self.assertEqual(self.pub(data=x),'PUBLISHED');v=self.view(self.pairclock(NOW,NOW+1));self.assertIsNone(v['prices'][0]['price']);self.assertEqual(v['prices'][0]['freshness'],'STALE')
    def test_already_stale_redacted(self):
        x=data();x['prices'][0]['observed_at']='2026-11-20T15:00:00Z';self.assertEqual(self.pub(data=x),'PUBLISHED');self.assertIsNone(self.view()['prices'][0]['price'])
    def test_bad_clock(self):self.seed();self.assertIsNone(self.view(self.pairclock(NOW,True)))
    def test_identity_swap(self):
        self.seed();it=iter((USER(),USER(),dict(USER(),subject='b')));self.assertIsNone(self.view(auth=lambda:next(it)))
    def test_recover_archive(self):self.pending();self.assertEqual(self.recover(),'RECOVERED');self.assertEqual(self.view()['prices'][0]['price'],1.5)
    def test_recover_journal(self):self.pending('journal');self.assertEqual(self.recover(),'RECOVERED')
    def test_repeat(self):
        self.pending();self.assertEqual(self.recover(),'RECOVERED');self.assertEqual(self.recover(),'ALREADY_COMMITTED')
        with self.f._open() as (a,j,w):self.assertEqual(a.execute('SELECT count(*) FROM fixture_revision').fetchone()[0],2);self.assertEqual(j.execute('SELECT count(*) FROM chain').fetchone()[0],2)
    def test_interrupted_recovery(self):
        self.pending();self.assertEqual(self.recover(interrupt=True),'INTERRUPTED');self.f=SnapshotV020(self.f.root);self.assertIsNone(self.view());self.assertEqual(self.recover(),'RECOVERED')
    def test_expired_candidate(self):self.pending();self.assertEqual(self.recover(clock=lambda:NOW+900001),'BLOCKED');self.assertIsNone(self.view())
    def test_wrong_digest(self):self.pending();self.assertEqual(self.recover(wanted='a'*64),'BLOCKED')
    def test_denied_approval(self):self.pending();self.assertEqual(self.recover(approve=lambda p,d:1),'BLOCKED')
    def test_wrong_role(self):self.pending();self.assertEqual(self.recover(auth=USER),'BLOCKED')
    def test_revoke_during_recovery(self):
        self.pending();it=iter((OWNER(),OWNER(),dict(OWNER(),subject='other')));self.assertEqual(self.recover(auth=lambda:next(it)),'BLOCKED');self.assertIsNone(self.view())
    def test_tamper(self):
        self.pending();
        with sqlite3.connect(self.f.archive) as db:db.execute('DROP TRIGGER fixture_revision_no_update');db.execute("UPDATE fixture_revision SET payload='{}' WHERE revision=1")
        self.assertEqual(self.recover(),'BLOCKED')
    def test_missing_witness(self):self.pending();self.f.anchor.unlink();self.assertEqual(self.recover(),'BLOCKED');self.assertFalse(self.f.anchor.exists())
    def test_clock_expiry_recovery(self):self.pending();it=iter((NOW,NOW+900001));self.assertEqual(self.recover(clock=lambda:next(it)),'BLOCKED')

if __name__=='__main__':unittest.main()
