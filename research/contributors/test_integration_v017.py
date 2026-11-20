# REMURA Experience v0.17 LAB — 20/11/2026, 17:54 CET
import fcntl
import json
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path
from integration_v017 import Fixture, DATES

OWNER = lambda: 'OWNER'
CONTRIBUTOR = lambda: 'CONTRIBUTOR'
A,B = DATES


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Fixture(Path(self.tmp.name)/'fixture')
        self.f.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def publish(self, rev=0, stamp=A, value=10, auth=OWNER, interrupt=None):
        return self.f.publish(rev,stamp,value,auth,interrupt)

    def seed(self):
        self.assertEqual(self.publish(),'PUBLISHED')

    def value(self):
        result = self.f.read(CONTRIBUTOR)
        return None if result is None else json.loads(result)['value']

    def backup(self, files):
        for p in files:
            shutil.copy2(p,p.with_suffix('.old'))

    def restore(self, files):
        for p in files:
            shutil.copy2(p.with_suffix('.old'),p)

    def test_empty(self):
        self.assertIsNone(self.value())

    def test_persistence_and_second_publication(self):
        self.seed()
        self.f = Fixture(self.f.root)
        self.assertEqual(self.value(),10)
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        self.assertEqual(self.value(),20)

    def test_stale_writer(self):
        self.seed()
        self.assertEqual(self.publish(),'BLOCKED')
        self.assertEqual(self.value(),10)

    def test_backdated(self):
        self.assertEqual(self.publish(stamp=B),'PUBLISHED')
        self.assertEqual(self.publish(1,A),'BLOCKED')

    def test_invalid_value(self):
        self.assertEqual(self.publish(value=True),'BLOCKED')
        self.assertEqual(self.publish(value=101),'BLOCKED')
        self.assertIsNone(self.value())

    def test_publication_denied(self):
        self.assertEqual(self.publish(auth=CONTRIBUTOR),'DENIED')
        self.assertIsNone(self.value())

    def test_read_roles(self):
        self.seed()
        for role in ('OWNER','VIEWER',None,True):
            self.assertIsNone(self.f.read(lambda:role))
        self.assertEqual(self.value(),10)

    def test_read_revocation(self):
        self.seed()
        roles = iter(('CONTRIBUTOR',None))
        self.assertIsNone(self.f.read(lambda:next(roles)))

    def test_publication_revocation(self):
        roles = iter(('OWNER','OWNER',None))
        self.assertEqual(self.publish(auth=lambda:next(roles)),'BLOCKED')
        self.assertIsNone(self.value())
        self.assertEqual(self.publish(),'BLOCKED')

    def test_crash_after_archive(self):
        self.seed()
        self.assertEqual(self.publish(1,B,20,interrupt='archive'),'INTERRUPTED')
        self.assertIsNone(self.value())
        self.assertEqual(self.publish(1,B,20),'BLOCKED')

    def test_crash_after_journal(self):
        self.seed()
        self.assertEqual(self.publish(1,B,20,interrupt='journal'),'INTERRUPTED')
        self.assertIsNone(self.value())
        self.assertEqual(self.publish(1,B,20),'BLOCKED')

    def test_ack_loss_after_witness(self):
        self.seed()
        self.assertEqual(self.publish(1,B,20,interrupt='witness'),'ACK_LOST')
        self.f = Fixture(self.f.root)
        self.assertEqual(self.value(),20)
        self.assertEqual(self.publish(1,B,20),'BLOCKED')

    def test_restore_both_primary_files(self):
        self.seed()
        files = (self.f.archive,self.f.chain)
        self.backup(files)
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        self.restore(files)
        self.assertIsNone(self.value())
        self.assertEqual(self.publish(1,B,30),'BLOCKED')

    def test_restore_archive_only(self):
        self.seed()
        self.backup((self.f.archive,))
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        self.restore((self.f.archive,))
        self.assertIsNone(self.value())

    def test_restore_journal_only(self):
        self.seed()
        self.backup((self.f.chain,))
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        self.restore((self.f.chain,))
        self.assertIsNone(self.value())

    def test_restore_witness_only(self):
        self.seed()
        self.backup((self.f.anchor,))
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        self.restore((self.f.anchor,))
        self.assertIsNone(self.value())

    def test_archive_history_tamper(self):
        self.seed()
        self.assertEqual(self.publish(1,B,20),'PUBLISHED')
        with sqlite3.connect(self.f.archive) as db:
            db.execute('DROP TRIGGER fixture_revision_no_update')
            db.execute("UPDATE fixture_revision SET payload='{}' WHERE revision=1")
        self.assertIsNone(self.value())

    def test_journal_tamper(self):
        self.seed()
        with sqlite3.connect(self.f.chain) as db:
            db.execute("UPDATE chain SET tag=? WHERE seq=1",('a'*64,))
        self.assertIsNone(self.value())

    def test_missing_witness(self):
        self.seed()
        self.f.anchor.unlink()
        self.assertIsNone(self.value())
        self.assertEqual(self.publish(1,B,20),'BLOCKED')
        self.assertFalse(self.f.anchor.exists())

    def test_lock_contention(self):
        self.seed()
        with open(self.f.lock,'rb') as handle:
            fcntl.flock(handle,fcntl.LOCK_EX)
            self.assertIsNone(self.value())
            self.assertEqual(self.publish(1,B,20),'BLOCKED')
        self.assertEqual(self.value(),10)

    def test_cap(self):
        for i in range(32):
            self.assertEqual(self.publish(i,A,i),'PUBLISHED')
        self.assertEqual(self.value(),31)
        self.assertEqual(self.publish(32,A,32),'BLOCKED')

    def test_no_implicit_reinitialization(self):
        self.seed()
        with self.assertRaises(FileExistsError):
            self.f.initialize()
        self.assertEqual(self.value(),10)


if __name__ == '__main__':
    unittest.main()
