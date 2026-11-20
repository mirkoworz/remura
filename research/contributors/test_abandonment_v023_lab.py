# REMURA Experience v0.23 LAB — 20/11/2026 CET
# Synthetic-only tests in temporary local SQLite stores.
import shutil
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from abandonment_v023_lab import AbandonmentLab, Rejected, permit


class AbandonmentTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.lab=AbandonmentLab(Path(self.tmp.name)/'v023')
        self.lab.initialize()

    def tearDown(self):
        self.tmp.cleanup()

    def approve(self, intent, d, action, reason, timestamp, **kw):
        seq=next((r[0] for r in self.lab.inspect()['intents'] if r[2]==intent),len(self.lab.inspect()['intents']))
        return self.lab.decide(intent,action,reason,kw.get('owner','owner-fixture'),timestamp,
                               kw.get('approval',permit(seq,intent,d,action,reason,'owner-fixture',timestamp)),
                               before_cas=kw.get('before_cas'),interrupt=kw.get('interrupt',False))

    def published(self):
        d=self.lab.stage('first',{'price':1.25},1000,2000,stage='journal')
        self.assertEqual(self.approve('first',d,'PUBLISHED','APPROVED_SYNTHETIC',1100),'PUBLISHED')
        return d

    def pending(self, stage='archive'):
        self.published()
        return self.lab.stage('second',{'price':999},1200,1300,stage=stage)

    def abandoned(self,stage='archive'):
        d=self.pending(stage)
        self.assertEqual(self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301),'ABANDONED')
        return d

    def test_archive_only_expired_abandonment(self):
        self.abandoned()
        self.assertEqual([r[2] for r in self.lab.inspect()['decisions']],['PUBLISHED','ABANDONED'])
        self.assertIsNone(self.lab.deliver(1301))

    def test_journal_ahead_expired_abandonment(self):
        self.abandoned('journal')
        self.assertEqual(len(self.lab.inspect()['journal']),2)
        self.assertIsNone(self.lab.deliver(1100))  # even when clock moves back

    def test_expiry_boundary_and_explicit_approval(self):
        d=self.pending()
        with self.assertRaises(Rejected): self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1300)
        self.assertIsNone(self.lab.deliver(1299))
        self.assertEqual(self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301),'ABANDONED')

    def test_wrong_digest_approval(self):
        d=self.pending()
        with self.assertRaises(Rejected): self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301,approval='a'*64)
        self.assertEqual(len(self.lab.inspect()['decisions']),1)

    def test_wrong_owner_approval(self):
        d=self.pending()
        with self.assertRaises(Rejected): self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301,owner='different-owner')

    def test_wrong_intent(self):
        d=self.pending()
        with self.assertRaises(Rejected): self.approve('missing',d,'ABANDONED','EXPIRED_PENDING',1301)

    def test_missing_intent_archive_cannot_be_adopted(self):
        d=self.pending()
        with closing(sqlite3.connect(self.lab.authority)) as db, db:
            db.execute('DROP TRIGGER block_intents_delete')
            db.execute('DELETE FROM intents WHERE seq=2')
        with self.assertRaises(Rejected): self.lab.inspect()
        self.assertIsNone(self.lab.deliver(1301))

    def test_wrong_generation(self):
        self.pending()
        with closing(sqlite3.connect(self.lab.archive)) as db, db:
            db.execute('DROP TRIGGER block_candidates_update')
            db.execute("UPDATE candidates SET gen='legacy' WHERE seq=2")
        with self.assertRaises(Rejected): self.lab.inspect()

    def test_interruption_retains_journal_and_evidence(self):
        d=self.pending()
        self.assertEqual(self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301,interrupt=True),'INTERRUPTED')
        before=self.lab.inspect()
        self.assertEqual((len(before['candidates']),len(before['journal']),len(before['decisions'])),(2,2,1))
        self.assertIsNone(self.lab.deliver(1301))
        self.assertEqual(self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301),'ABANDONED')
        self.assertEqual(before['journal'],self.lab.inspect()['journal'])
        self.assertEqual(before['candidates'],self.lab.inspect()['candidates'])

    def test_duplicate_acknowledgment_is_rejected(self):
        d=self.abandoned()
        with self.assertRaises(Rejected): self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301)

    def test_stale_publication_rejected(self):
        d=self.pending()
        with self.assertRaises(Rejected): self.approve('second',d,'PUBLISHED','APPROVED_SYNTHETIC',1301)
        self.assertIsNone(self.lab.deliver(1301))

    def test_revocation_at_cas(self):
        d=self.pending()
        def revoke(): self.lab.revoked.add((2,'second'))
        with self.assertRaises(Rejected): self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301,before_cas=revoke)
        self.assertEqual(len(self.lab.inspect()['decisions']),1)
        self.assertIsNone(self.lab.deliver(1301))

    def test_immutable_candidates_and_decisions(self):
        self.abandoned()
        for path,sql in ((self.lab.archive,'DELETE FROM candidates WHERE seq=2'),(self.lab.authority,"UPDATE decisions SET action='PUBLISHED' WHERE seq=2")):
            with self.assertRaises(sqlite3.IntegrityError):
                with closing(sqlite3.connect(path)) as db, db: db.execute(sql)

    def test_tamper_journal_rejected(self):
        self.abandoned()
        with closing(sqlite3.connect(self.lab.journal)) as db, db:
            db.execute('DROP TRIGGER block_entries_update')
            db.execute("UPDATE entries SET digest=? WHERE seq=2",('f'*64,))
        with self.assertRaises(Rejected): self.lab.inspect()
        self.assertIsNone(self.lab.deliver(1100))

    def test_rollback_archive_and_journal_against_authority(self):
        self.published()
        copies=[]
        for p in (self.lab.archive,self.lab.journal):
            snap=p.with_suffix('.bak');shutil.copy2(p,snap);copies.append((p,snap))
        d=self.lab.stage('second',{'price':999},1200,1300)
        self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301)
        for p,snap in copies:shutil.copy2(snap,p)
        with self.assertRaises(Rejected): self.lab.inspect()
        self.assertIsNone(self.lab.deliver(1100))

    def test_rollback_authority_alone(self):
        self.published()
        snap=self.lab.authority.with_suffix('.bak');shutil.copy2(self.lab.authority,snap)
        d=self.lab.stage('second',{'price':999},1200,1300,stage='journal')
        self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301)
        shutil.copy2(snap,self.lab.authority)
        with self.assertRaises(Rejected): self.lab.inspect()
        self.assertIsNone(self.lab.deliver(1100))

    def test_rollback_all_requires_external_monotonic_pin(self):
        self.published()
        copies=[]
        for p in (self.lab.archive,self.lab.journal,self.lab.authority):
            snap=p.with_suffix('.bak');shutil.copy2(p,snap);copies.append((p,snap))
        d=self.lab.stage('second',{'price':999},1200,1300)
        self.approve('second',d,'ABANDONED','EXPIRED_PENDING',1301)
        pin=self.lab.inspect()['head']
        for p,snap in copies:shutil.copy2(snap,p)
        self.assertEqual(self.lab.inspect()['head'][0],1)  # known limitation without an external pin
        self.lab.external_pin=pin
        with self.assertRaises(Rejected): self.lab.inspect()
        self.assertIsNone(self.lab.deliver(1100))

    def test_new_sequence_after_abandonment(self):
        self.abandoned()
        self.assertIsNone(self.lab.deliver(1301))
        d=self.lab.stage('third',{'price':3.0},1400,2000,stage='journal')
        self.assertIsNone(self.lab.deliver(1450))
        self.assertEqual(self.approve('third',d,'PUBLISHED','APPROVED_SYNTHETIC',1450),'PUBLISHED')
        self.assertEqual(self.lab.deliver(1450)['revision'],3)
        self.assertEqual(self.lab.deliver(1450)['market']['price'],3.0)
        self.assertEqual([e[2] for e in self.lab.inspect()['decisions']],['PUBLISHED','ABANDONED','PUBLISHED'])

    def test_duplicate_intent_and_pending_blocked(self):
        self.pending()
        with self.assertRaises(Rejected): self.lab.stage('second',{'price':2},1200,1400)
        with self.assertRaises(Rejected): self.lab.stage('third',{'price':2},1200,1400)

    def test_expired_market_snapshot_never_published(self):
        self.published()
        self.assertIsNone(self.lab.deliver(2001))

    def test_no_external_calls_needed(self):
        self.assertEqual(self.lab.inspect()['head'],(0,'0'*64))


if __name__ == '__main__':
    unittest.main()
