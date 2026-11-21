# REMURA Experience v0.25 LAB tests — 21/11/2026 07:21 CET
import shutil
import sqlite3
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path

from independent_anchor_v025_lab import (
    Denied, PrimaryFixture, WitnessFixture, approval, ZERO,
)

D1 = 'a' * 64
D2 = 'b' * 64


class WitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.w = WitnessFixture(self.root / 'witness-domain' / 'w.sqlite')
        self.p = PrimaryFixture(self.root / 'primary-domain' / 'primary.sqlite', self.w)
        self.w.initialize()
        self.p.initialize()

    def tearDown(self):
        self.temp.cleanup()

    def commit(self, digest=D1, action='PUBLISHED', expiry=1000, at=100, owner='owner-test'):
        self.p.prepare(digest, action, expiry, at, owner)
        result = self.p.commit_witness()
        self.assertEqual(self.p.finalize(), 'ACKNOWLEDGED')
        return result

    def snapshots(self):
        copies = []
        for path in (self.w.path, self.p.path):
            copy = self.root / (path.stem + '.bak')
            shutil.copy2(path, copy)
            copies.append((path,copy))
        return copies

    def test_empty_witness_is_genesis_and_no_market(self):
        self.assertEqual(self.w.head(), (0,ZERO))
        self.assertIsNone(self.p.read_status(100))

    def test_publication_requires_both_commit_and_ack(self):
        self.p.prepare(D1,'PUBLISHED',1000,100,'owner-test')
        self.assertIsNone(self.p.read_status(100))
        self.p.commit_witness()
        self.assertIsNone(self.p.read_status(100))
        self.assertEqual(self.p.finalize(), 'ACKNOWLEDGED')
        self.assertEqual(self.p.read_status(100),'PUBLISHED')

    def test_expired_published_value_not_visible(self):
        self.commit()
        self.assertEqual(self.p.read_status(1000),'PUBLISHED')
        self.assertIsNone(self.p.read_status(1001))

    def test_future_witness_not_visible(self):
        self.commit()
        self.assertIsNone(self.p.read_status(99))

    def test_abandoned_always_non_numeric_and_is_immutable(self):
        self.commit(D1, 'ABANDONED', 1000, 1001)
        self.assertIsNone(self.p.read_status(1001))
        self.assertEqual(self.w.rows()[0][3],'ABANDONED')

    def test_expiry_boundary_blocks_early_abandon(self):
        self.p.prepare(D1,'ABANDONED',1000,1000,'owner-test')
        with self.assertRaises(Denied): self.p.commit_witness()
        self.assertIsNone(self.p.read_status(1000))

    def test_late_publication_is_rejected(self):
        self.p.prepare(D1,'PUBLISHED',1000,1001,'owner-test')
        with self.assertRaises(Denied): self.p.commit_witness()
        self.assertIsNone(self.p.read_status(1001))

    def test_new_intent_blocked_when_prior_pending(self):
        self.p.prepare(D1,'PUBLISHED',1000,100,'owner-test')
        with self.assertRaises(Denied): self.p.prepare(D2,'PUBLISHED',2000,200,'owner-test')

    def test_pending_after_witness_can_be_finalized_once(self):
        self.p.prepare(D1,'PUBLISHED',1000,100,'owner-test')
        self.p.commit_witness()
        self.assertIsNone(self.p.read_status(101))
        self.assertEqual(self.p.finalize(),'ACKNOWLEDGED')
        self.assertEqual(self.p.finalize(),'ALREADY_ACKNOWLEDGED')
        self.assertEqual(self.p.read_status(101),'PUBLISHED')

    def test_finalize_before_witness_rejected(self):
        self.p.prepare(D1,'PUBLISHED',1000,100,'owner-test')
        with self.assertRaises(Denied): self.p.finalize()

    def test_two_generations_preserve_chain(self):
        first=self.commit()
        second=self.commit(D2,'ABANDONED',1100,1101)
        self.assertNotEqual(first,second)
        self.assertEqual(self.w.rows()[1][7],first[1])
        self.assertIsNone(self.p.read_status(1101))

    def test_stale_expected_head_rejected(self):
        self.commit()
        with self.assertRaises(Denied):
            self.w.append((0,ZERO),D2,'PUBLISHED',2000,200,'owner-test',approval(1,D2,'PUBLISHED',2000,200,'owner-test'))

    def test_wrong_owner_signature_rejected(self):
        expected=self.w.head()
        with self.assertRaises(Denied):
            self.w.append(expected,D1,'PUBLISHED',1000,100,'owner-test',approval(1,D1,'PUBLISHED',1000,100,'someone-else'))
        self.assertEqual(self.w.head(),expected)

    def test_duplicate_threaded_witness_cas_only_one_wins(self):
        b=threading.Barrier(2)
        expected=self.w.head()
        grant=approval(1,D1,'PUBLISHED',1000,100,'owner-test')
        def contender(_):
            b.wait(timeout=3)
            try:
                self.w.append(expected,D1,'PUBLISHED',1000,100,'owner-test',grant)
                return 'OK'
            except Denied:
                return 'DENIED'
        with ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(contender,(1,2)))
        self.assertCountEqual(results,['OK','DENIED'])
        self.assertEqual(self.w.head()[0],1)
        self.assertIsNone(self.p.read_status(100))

    def test_immutable_witness_sql_trigger(self):
        self.commit()
        with self.assertRaises(sqlite3.IntegrityError):
            with closing(sqlite3.connect(self.w.path)) as db, db:
                db.execute('DELETE FROM anchors WHERE seq=1')

    def test_tampered_witness_digest_rejected(self):
        self.commit()
        with closing(sqlite3.connect(self.w.path)) as db, db:
            db.execute('DROP TRIGGER no_anchor_update')
            db.execute('UPDATE anchors SET digest=? WHERE seq=1',(D2,))
        with self.assertRaises(Denied): self.w.head()
        self.assertIsNone(self.p.read_status(100))

    def test_primary_rollback_detected_by_newer_witness(self):
        self.commit()
        snap=self.snapshots()
        self.commit(D2,'PUBLISHED',2000,1100)
        shutil.copy2(snap[1][1],snap[1][0])
        self.assertIsNone(self.p.read_status(1200))

    def test_witness_rollback_detected_by_newer_primary(self):
        self.commit()
        snap=self.snapshots()
        self.commit(D2,'PUBLISHED',2000,1100)
        shutil.copy2(snap[0][1],snap[0][0])
        self.assertIsNone(self.p.read_status(1200))

    def test_joint_rollback_looks_consistent_without_outer_pin(self):
        self.commit()
        snap=self.snapshots()
        self.commit(D2,'ABANDONED',1100,1101)
        for path, backup in snap: shutil.copy2(backup,path)
        self.assertEqual(self.w.head()[0],1)
        self.assertEqual(self.p.read_status(200),'PUBLISHED')  # explicit limitation

    def test_joint_rollback_rejected_with_retain_pin(self):
        self.commit()
        snap=self.snapshots()
        pin=self.commit(D2,'ABANDONED',1100,1101)
        for path, backup in snap: shutil.copy2(backup,path)
        self.w.external_pin=pin
        with self.assertRaises(Denied): self.w.head()
        self.assertIsNone(self.p.read_status(200))

    def test_lost_witness_fails_closed(self):
        self.commit()
        self.w.path.unlink()
        self.assertIsNone(self.p.read_status(200))

    def test_invalid_pin_rejected(self):
        self.commit()
        self.w.external_pin=(1,D2)
        with self.assertRaises(Denied): self.w.head()
        self.assertIsNone(self.p.read_status(200))

    def test_old_pin_remains_valid_when_new_chain_extends_it(self):
        first=self.commit()
        self.w.external_pin=first
        self.commit(D2,'PUBLISHED',2000,1100)
        self.assertEqual(self.w.head()[0],2)
        self.assertEqual(self.p.read_status(1200),'PUBLISHED')

    def test_primary_receipt_tampering_blocks(self):
        self.commit()
        with closing(sqlite3.connect(self.p.path)) as db, db:
            db.execute('DROP TRIGGER no_receipt_update')
            db.execute('UPDATE receipts SET witness_tag=?',(D2,))
        self.assertIsNone(self.p.read_status(200))

    def test_no_automatic_repair_of_pending_intent(self):
        self.p.prepare(D1,'PUBLISHED',1000,100,'owner-test')
        self.assertIsNone(self.p.read_status(100))
        self.assertEqual(self.w.head()[0],0)


if __name__ == '__main__':
    unittest.main()
