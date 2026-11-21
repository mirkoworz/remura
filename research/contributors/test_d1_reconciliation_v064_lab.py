# REMURA v0.64 LAB — complete original D1 SQL; no Cloudflare requests.
import concurrent.futures
import hashlib
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
P=Path(__file__).parent
A,B,O='a'*64,'b'*64,'c'*64
EA,EB,EO='1'*64,'2'*64,'3'*64
T='2026-11-21T09:40:00Z'; R='2026-11-21T09:41:00Z'; W='2026-11-21T09:42:00Z'; X='2026-11-21T09:43:00Z'; F='2026-11-21T09:44:00Z'
K=('EURUSD','OANDA','EURUSD','SPOT','')
def req(n):return '00000000-0000-4000-8000-'+str(n).zfill(12)
class ReconTest(unittest.TestCase):
 def connect(self):
  c=sqlite3.connect(self.path,timeout=10,isolation_level=None)
  c.execute('PRAGMA foreign_keys=ON');c.execute('PRAGMA busy_timeout=10000');return c
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.path=str(Path(self.temp.name)/'case.sqlite');self.db=self.connect()
  self.db.execute('PRAGMA journal_mode=WAL')
  for n in ('d1_access_candidate.sql','d1_amendment_v059_lab.sql','d1_reconciliation_v064_lab.sql'):
   self.db.executescript((P/n).read_text())
  with self.db:
   self.db.execute('INSERT INTO lab_owner VALUES(1,?,?,0)',(O,EO))
   self.db.executemany('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)',[(A,EA,'friend-a'),(B,EB,'friend-b')])
   self.db.execute('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)',K+('fixture-fx',))
   self.db.execute('UPDATE lab_state SET write_enabled=1,read_enabled=1,recovery_enabled=1')
   for i,s in [(1,A),(2,B)]:
    self.db.execute('INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,price,anchor_utc,observed_utc,received_utc,note,source_group) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)',(s,req(i),*K,'DAY','DELTA_PEAK','1.123','2026-11-21T08:00:00Z','2026-11-21T08:30:00Z','2026-11-21T09:00:00Z','fixture','fixture-fx'))
   self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'APPROVED','2026-11-21T09:01:00Z','fixture'))
   self.db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(2,O,'APPROVED','2026-11-21T09:01:00Z','fixture'))
 def tearDown(self):self.db.close();self.temp.cleanup()
 def reserve(self,c=None,s=A,src=1,n=3,price='1.234',note='fixture',at=T):
  return (c or self.db).execute('INSERT INTO lab_amend_attempts_v064(subject,request_id,source_entry_id,price,observed_utc,note,reserved_utc) VALUES(?,?,?,?,?,?,?)',(s,req(n),src,price,'2026-11-21T09:35:00Z',note,at)).lastrowid
 def amend(self,c=None,s=A,src=1,n=3,price='1.234',note='fixture',at=R):
  return (c or self.db).execute('INSERT INTO lab_level_amendments_v059(subject,source_entry_id,request_id,price,observed_utc,received_utc,note) VALUES(?,?,?,?,?,?,?)',(s,src,req(n),price,'2026-11-21T09:35:00Z',at,note)).lastrowid
 def review(self,c=None,id=1,action='APPROVED',at=W):
  return (c or self.db).execute('INSERT INTO lab_level_amendment_reviews_v059(amendment_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(id,O,action,at,'fixture')).lastrowid
 def release(self,c=None,aid=1,disposition='REVIEWED',owner=O,at=X):
  return (c or self.db).execute('INSERT INTO lab_amend_releases_v064(attempt_id,owner,disposition,reason,released_utc) VALUES(?,?,?,?,?)',(aid,owner,disposition,'verified manually',at)).lastrowid
 def deny(self,fn):
  with self.assertRaises(sqlite3.IntegrityError):fn()
 def test_01_original_schema_exact_pin(self):
  data=(P/'d1_access_candidate.sql').read_bytes();self.assertEqual(hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest(),'9ed38b6ed83755186af05f1bf28b4608cdc5f901')
 def test_02_reserve_pending(self):self.assertEqual(self.reserve(),1)
 def test_03_unapproved_parent(self):
  self.db.execute("UPDATE lab_catalog SET active=0");self.reserve() # Parent approval is not catalog-gated here; mutation remains blocked v059
 def test_04_wrong_parent(self):self.deny(lambda:self.reserve(src=999))
 def test_05_other_owner_source(self):self.deny(lambda:self.reserve(s=B,src=1))
 def test_06_unknown_subject(self):self.deny(lambda:self.reserve(s='d'*64))
 def test_07_owner_cannot_contribute(self):self.deny(lambda:self.reserve(s=O))
 def test_08_revoked_author(self):
  self.db.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,));self.deny(self.reserve)
 def test_09_write_disabled(self):
  self.db.execute('UPDATE lab_state SET write_enabled=0');self.deny(self.reserve)
 def test_10_second_outstanding_request_blocked(self):self.reserve();self.deny(lambda:self.reserve(n=4))
 def test_11_same_request_replay_blocked(self):self.reserve();self.deny(self.reserve)
 def test_12_bob_separate_outstanding_can_reserve(self):self.reserve();self.assertEqual(self.reserve(s=B,src=2,n=4),2)
 def test_13_reservation_immutable(self):self.reserve();self.deny(lambda:self.db.execute('UPDATE lab_amend_attempts_v064 SET price=?',('9',)))
 def test_14_reservation_cannot_delete(self):self.reserve();self.deny(lambda:self.db.execute('DELETE FROM lab_amend_attempts_v064'))
 def test_15_direct_old_v059_insert_blocked(self):self.deny(self.amend)
 def test_16_reserved_exact_insert_allowed(self):self.reserve();self.assertEqual(self.amend(),1)
 def test_17_changed_price_blocked(self):self.reserve();self.deny(lambda:self.amend(price='1.333'))
 def test_18_changed_note_blocked(self):self.reserve();self.deny(lambda:self.amend(note='modified'))
 def test_19_changed_request_id_blocked(self):self.reserve();self.deny(lambda:self.amend(n=4))
 def test_20_changed_source_blocked(self):self.reserve();self.deny(lambda:self.amend(src=2))
 def test_21_received_before_reservation_blocked(self):self.reserve();self.deny(lambda:self.amend(at='2026-11-21T09:39:00Z'))
 def test_22_one_result_per_reserved_request(self):self.reserve();self.amend();self.deny(self.amend)
 def test_23_uncommitted_attempt_cannot_release_as_reviewed(self):self.reserve();self.deny(self.release)
 def test_24_committed_unreviewed_cannot_release(self):self.reserve();self.amend();self.deny(self.release)
 def test_25_approved_amendment_can_release(self):self.reserve();self.amend();self.review();self.assertEqual(self.release(),1)
 def test_26_rejected_amendment_can_release(self):self.reserve();self.amend();self.review(action='REJECTED');self.release()
 def test_27_abandoned_attempt_can_be_explicitly_closed_by_owner(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.assertEqual(self.db.execute('SELECT count(*) FROM lab_amend_releases_v064').fetchone()[0],1)
 def test_28_committed_cannot_be_aborted(self):self.reserve();self.amend();self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER'))
 def test_29_contributor_cannot_release(self):self.reserve();self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER',owner=A))
 def test_30_unknown_owner_cannot_release(self):self.reserve();self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER',owner='d'*64))
 def test_31_recovery_gate_closed(self):self.reserve();self.db.execute('UPDATE lab_state SET recovery_enabled=0');self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER'))
 def test_32_revoked_owner_cannot_release(self):self.reserve();self.db.execute('UPDATE lab_owner SET revoked=1');self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER'))
 def test_33_release_before_reservation_blocked(self):self.reserve();self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER',at='2026-11-21T09:39:00Z'))
 def test_34_release_immutable(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.deny(lambda:self.db.execute("UPDATE lab_amend_releases_v064 SET reason='changed'"))
 def test_35_release_cannot_delete(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.deny(lambda:self.db.execute('DELETE FROM lab_amend_releases_v064'))
 def test_36_release_cannot_repeat(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.deny(lambda:self.release(disposition='ABORTED_BY_OWNER'))
 def test_37_next_attempt_after_clearance(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.assertEqual(self.reserve(n=4,at=F),2)
 def test_38_delayed_old_mutation_after_clearance_rejected(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.deny(self.amend)
 def test_39_delayed_old_mutation_after_new_reservation_rejected(self):self.reserve();self.release(disposition='ABORTED_BY_OWNER');self.reserve(n=4,at=F);self.deny(self.amend)
 def test_40_unreleased_request_remains_after_refresh(self):
  self.reserve();self.db.close();self.db=self.connect();self.deny(lambda:self.reserve(n=4))
 def test_41_original_entry_immutable(self):
  self.reserve();self.amend();self.assertEqual(self.db.execute('SELECT price FROM lab_entries WHERE id=1').fetchone()[0],'1.123')
 def test_42_foreign_keys_clean(self):self.reserve();self.amend();self.review();self.release();self.assertEqual(self.db.execute('PRAGMA foreign_key_check').fetchall(),[])
 def test_43_rollback_does_not_commit_reservation(self):
  c=self.connect();c.execute('BEGIN IMMEDIATE');self.reserve(c);c.rollback();c.close();self.assertEqual(self.db.execute('SELECT count(*) FROM lab_amend_attempts_v064').fetchone()[0],0)
 def test_44_simultaneous_two_reservations_one_winner(self):
  barrier=threading.Barrier(2)
  def attempt(n):
   c=self.connect()
   try:
    barrier.wait(5)
    try:
     with c:self.reserve(c,n=n)
     return 'OK'
    except sqlite3.IntegrityError:return 'DENIED'
   finally:c.close()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:r=list(e.map(attempt,(3,4)))
  self.assertEqual(sorted(r),['DENIED','OK'])
 def test_45_release_competing_with_delayed_insert_cannot_both_succeed(self):
  self.reserve();barrier=threading.Barrier(2)
  def competitor(kind):
   c=self.connect()
   try:
    barrier.wait(5)
    try:
     with c:
      if kind=='abort':self.release(c,disposition='ABORTED_BY_OWNER')
      else:self.amend(c)
     return kind
    except sqlite3.IntegrityError:return 'BLOCKED'
   finally:c.close()
  with concurrent.futures.ThreadPoolExecutor(max_workers=2) as e:results=list(e.map(competitor,('abort','commit')))
  self.assertIn('BLOCKED',results);self.assertNotEqual(sorted(results),['abort','commit'])
 def test_46_old_v059_trigger_remains(self):self.assertIn('immutable_amendment',self.db.execute("SELECT sql FROM sqlite_master WHERE name='lab_amendment_no_update_v059'").fetchone()[0])
 def test_47_sql_does_not_drop_or_alter_original(self):
  s=(P/'d1_reconciliation_v064_lab.sql').read_text().upper();self.assertNotIn('DROP TABLE',s);self.assertNotIn('ALTER TABLE',s)
 def test_48_approved_review_then_clearance_then_next_request(self):self.reserve();self.amend();self.review();self.release();self.assertEqual(self.reserve(n=4,at=F),2)

if __name__=='__main__':unittest.main()
