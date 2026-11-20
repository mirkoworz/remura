# REMURA Experience v0.18 LAB — 20/11/2026 CET
import fcntl
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from recovery_v018 import Recovery
from integration_v017 import DATES, WKEY, body, digest
import witness_v016 as witness

OWNER = lambda: 'OWNER'
CONTRIBUTOR = lambda: 'CONTRIBUTOR'
APPROVE = lambda p,d: True
A,B = DATES


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Recovery(Path(self.tmp.name)/'fixture')
        self.f.initialize()
        self.assertEqual(self.f.publish(0,A,10,OWNER),'PUBLISHED')
        with self.f._open() as (_,__,w):
            self.prior = witness.read(w,WKEY)
        self.wanted = digest(body(2,B,20))

    def tearDown(self):
        self.tmp.cleanup()

    def pending(self, stage='archive'):
        self.assertEqual(self.f.publish(1,B,20,OWNER,stage),'INTERRUPTED')
        self.assertIsNone(self.f.read(CONTRIBUTOR))

    def recover(self, **kw):
        args = dict(prior=self.prior,wanted=self.wanted,authorize=OWNER,approve=APPROVE)
        return self.f.recover(**(args|kw))

    def visible(self):
        b = self.f.read(CONTRIBUTOR)
        return None if b is None else json.loads(b)['value']

    def test_archive_recovery(self):
        self.pending()
        self.assertEqual(self.recover(),'RECOVERED')
        self.assertEqual(self.visible(),20)

    def test_journal_recovery(self):
        self.pending('journal')
        self.assertEqual(self.recover(),'RECOVERED')
        self.assertEqual(self.visible(),20)

    def test_repeat_no_duplicate(self):
        self.pending()
        self.assertEqual(self.recover(),'RECOVERED')
        self.assertEqual(self.recover(),'ALREADY_COMMITTED')
        with self.f._open() as (a,j,w):
            self.assertEqual(a.execute('SELECT count(*) FROM fixture_revision').fetchone()[0],2)
            self.assertEqual(j.execute('SELECT count(*) FROM chain').fetchone()[0],2)
            self.assertEqual(witness.read(w,WKEY)[0],2)

    def test_ack_loss(self):
        self.assertEqual(self.f.publish(1,B,20,OWNER,'witness'),'ACK_LOST')
        self.assertEqual(self.recover(),'ALREADY_COMMITTED')

    def test_interrupted_recovery(self):
        self.pending()
        self.assertEqual(self.recover(interrupt=True),'INTERRUPTED')
        self.f = Recovery(self.f.root)
        self.assertIsNone(self.visible())
        self.assertEqual(self.recover(),'RECOVERED')

    def test_no_implicit_recovery(self):
        self.pending()
        self.assertEqual(self.f.publish(1,B,20,OWNER),'BLOCKED')
        self.assertIsNone(self.visible())

    def test_wrong_intent(self):
        self.pending()
        self.assertEqual(self.recover(wanted='a'*64),'BLOCKED')
        self.assertIsNone(self.visible())

    def test_bad_prior(self):
        self.pending()
        self.assertEqual(self.recover(prior=(1,'a'*64,self.prior[2])),'BLOCKED')

    def test_absent_candidate(self):
        self.assertEqual(self.recover(),'BLOCKED')
        self.assertEqual(self.visible(),10)

    def test_no_approval(self):
        self.pending()
        for result in (False,1,None):
            self.assertEqual(self.recover(approve=lambda p,d:result),'DENIED')
        self.assertIsNone(self.visible())

    def test_wrong_role(self):
        self.pending()
        self.assertEqual(self.recover(authorize=CONTRIBUTOR),'DENIED')

    def test_revoked(self):
        self.pending()
        roles = iter(('OWNER','OWNER',None))
        self.assertEqual(self.recover(authorize=lambda: next(roles)),'BLOCKED')
        self.assertIsNone(self.visible())

    def test_adapter_exception(self):
        self.pending()
        def broken(*args):
            raise RuntimeError('fixture adapter unavailable')
        self.assertEqual(self.recover(approve=broken),'BLOCKED')
        self.assertEqual(self.f.publish(1,B,20,broken),'BLOCKED')
        self.assertIsNone(self.f.read(broken))

    def test_historical_tamper(self):
        self.pending()
        with sqlite3.connect(self.f.archive) as db:
            db.execute('DROP TRIGGER fixture_revision_no_update')
            db.execute("UPDATE fixture_revision SET payload='{}' WHERE revision=1")
        self.assertEqual(self.recover(),'BLOCKED')

    def test_journal_tamper(self):
        self.pending('journal')
        with sqlite3.connect(self.f.chain) as db:
            db.execute("UPDATE chain SET tag=? WHERE seq=2",('a'*64,))
        self.assertEqual(self.recover(),'BLOCKED')

    def test_missing_witness(self):
        self.pending()
        self.f.anchor.unlink()
        self.assertEqual(self.recover(),'BLOCKED')
        self.assertFalse(self.f.anchor.exists())

    def test_lock(self):
        self.pending()
        with open(self.f.lock,'rb') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            self.assertEqual(self.recover(),'BLOCKED')
        self.assertEqual(self.recover(),'RECOVERED')

    def test_stale_intent_after_later_publish(self):
        self.pending()
        self.assertEqual(self.recover(),'RECOVERED')
        self.assertEqual(self.f.publish(2,B,30,OWNER),'PUBLISHED')
        self.assertEqual(self.recover(),'BLOCKED')
        self.assertEqual(self.visible(),30)

    def test_committed_receipt_requires_role(self):
        self.pending()
        self.assertEqual(self.recover(),'RECOVERED')
        roles = iter(('OWNER',None))
        self.assertEqual(self.recover(authorize=lambda:next(roles)),'DENIED')


if __name__ == '__main__':
    unittest.main()
