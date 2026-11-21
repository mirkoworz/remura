# REMURA Contributors v0.60 LAB — 21/11/2026 CET
# NEW negative controls on the exact pinned D1 candidate schema; no live D1 calls.
import concurrent.futures
import hashlib
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from contextlib import closing
from test_d1_amendment_v059_lab import A, B, O, EA, EB, EO, K, T, BEFORE, AFTER, NEXT
from test_d1_amendment_queries_v059_lab import Q

ROOT = Path(__file__).parent
BASE_SHA = '9ed38b6ed83755186af05f1bf28b4608cdc5f901'

def git_blob(content):
    return hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()


class D1FullSchemaConcurrentLab(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = str(Path(self.temp.name) / 'fixture.sqlite')
        db = self.connection()
        try:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript((ROOT / 'd1_access_candidate.sql').read_text())
            db.executescript((ROOT / 'd1_amendment_v059_lab.sql').read_text())
            db.execute('BEGIN IMMEDIATE')
            db.execute('INSERT INTO lab_owner(id,subject,email_tag) VALUES(1,?,?)', (O,EO))
            db.executemany('INSERT INTO lab_identities(subject,email_tag,slot) VALUES(?,?,?)', [(A,EA,'friend-a'),(B,EB,'friend-b')])
            db.execute('INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)',K+('fixture-fx',))
            db.execute('UPDATE lab_state SET write_enabled=1,read_enabled=1,recovery_enabled=1')
            for i,s in enumerate((A,B),1):
                db.execute('''INSERT INTO lab_entries(subject,request_id,market,provider,ticker,product,contract,period,kind,
                    price,anchor_utc,observed_utc,received_utc,note,source_group)
                    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (s,f'00000000-0000-4000-8000-{i:012d}',*K,'DAY','DELTA_PEAK','1.123',BEFORE,BEFORE,T,'fixture','fixture-fx'))
            db.execute('INSERT INTO lab_reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)',(1,O,'APPROVED',T,'fixture'))
            db.commit()
        finally:
            db.close()

    def tearDown(self):
        self.temp.cleanup()

    def connection(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=5000')
        return db

    @staticmethod
    def amendment_sql():
        return '''INSERT INTO lab_level_amendments_v059
            (subject,source_entry_id,request_id,price,observed_utc,received_utc,note)
            VALUES(?,?,?,?,?,?,?)'''

    def insert(self,db,n,subject=A,source=1):
        return db.execute(self.amendment_sql(),(subject,source,f'00000000-0000-4000-8000-{n:012d}', '1.234',T,AFTER,'fixture')).lastrowid

    def approve(self,db,aid):
        return db.execute('''INSERT INTO lab_level_amendment_reviews_v059(amendment_id,owner,action,at_utc,reason)
          VALUES(?,?,?,?,?)''', (aid,O,'APPROVED',NEXT,'fixture'))

    def test_01_schema_exact_pinned_blob(self):
        data=(ROOT/'d1_access_candidate.sql').read_bytes()
        self.assertEqual(git_blob(data),BASE_SHA)

    def test_02_no_cloud_d1_required(self):
        db=self.connection()
        try:
            self.assertEqual(db.execute('PRAGMA database_list').fetchall()[0][2],self.path)
        finally:db.close()

    def test_03_cross_connection_commit_visible(self):
        a=self.connection();b=self.connection()
        try:
            a.execute('BEGIN IMMEDIATE');self.insert(a,3);a.commit()
            self.assertEqual(b.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],1)
        finally:a.close();b.close()

    def test_04_rolled_back_insert_not_visible(self):
        a=self.connection();b=self.connection()
        try:
            a.execute('BEGIN IMMEDIATE');self.insert(a,3)
            self.assertEqual(b.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],0)
            a.rollback();self.assertEqual(b.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],0)
        finally:a.close();b.close()

    def test_05_duplicate_request_id_two_connections_one_winner(self):
        barrier=threading.Barrier(2)
        def contender(_):
            d=self.connection()
            try:
                barrier.wait(3)
                try:
                    with d:self.insert(d,3)
                    return 'OK'
                except sqlite3.IntegrityError:return 'DENIED'
                except sqlite3.OperationalError:return 'LOCKED'
            finally:d.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(contender,range(2)))
        self.assertEqual(results.count('OK'),1)
        self.assertTrue(set(results)<= {'OK','DENIED','LOCKED'})
        with closing(self.connection()) as d:
            self.assertEqual(d.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],1)

    def test_06_parallel_distinct_amendments_without_overwrite(self):
        barrier=threading.Barrier(2)
        def submit(n):
            d=self.connection()
            try:
                barrier.wait(3)
                with d:self.insert(d,n)
                return n
            finally:d.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            values=list(pool.map(submit,[3,4]))
        self.assertEqual(sorted(values),[3,4])
        with closing(self.connection()) as d:
            self.assertEqual(d.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],2)

    def test_07_two_simultaneous_approvals_one_winner(self):
        d=self.connection()
        with d:self.insert(d,3);self.insert(d,4)
        d.close()
        barrier=threading.Barrier(2)
        def review(aid):
            c=self.connection()
            try:
                barrier.wait(3)
                try:
                    with c:self.approve(c,aid)
                    return 'OK'
                except sqlite3.IntegrityError:return 'DENIED'
                except sqlite3.OperationalError:return 'LOCKED'
            finally:c.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(review,[1,2]))
        self.assertEqual(results.count('OK'),1)
        with closing(self.connection()) as c:
            self.assertEqual(c.execute("SELECT count(*) FROM lab_level_amendment_reviews_v059 WHERE action='APPROVED'").fetchone()[0],1)

    def test_08_revocation_commits_before_late_amendment(self):
        a=self.connection();b=self.connection()
        try:
            a.execute('BEGIN IMMEDIATE')
            a.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,))
            a.commit()
            with self.assertRaises(sqlite3.IntegrityError):self.insert(b,3)
        finally:a.close();b.close()

    def test_09_close_write_gate_before_new_intent(self):
        a=self.connection();b=self.connection()
        try:
            a.execute('UPDATE lab_state SET write_enabled=0')
            with self.assertRaises(sqlite3.IntegrityError):self.insert(b,3)
        finally:a.close();b.close()

    def test_10_revoke_author_before_owner_approval(self):
        a=self.connection();b=self.connection()
        try:
            with a:self.insert(a,3)
            a.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,))
            with self.assertRaises(sqlite3.IntegrityError):self.approve(b,1)
        finally:a.close();b.close()

    def test_11_read_scope_rechecks_revocation(self):
        a=self.connection();b=self.connection()
        try:
            with a:self.insert(a,3)
            self.assertEqual(len(b.execute(Q['own'],(A,EA,0)).fetchall()),1)
            a.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,))
            self.assertEqual(b.execute(Q['own'],(A,EA,0)).fetchall(),[])
        finally:a.close();b.close()

    def test_12_read_approved_projection_after_source_revoke(self):
        a=self.connection();b=self.connection()
        try:
            self.assertEqual(len(b.execute(Q['approved'],(B,EB)).fetchall()),1)
            a.execute('UPDATE lab_identities SET revoked=1 WHERE subject=?',(A,))
            self.assertEqual(b.execute(Q['approved'],(B,EB)).fetchall(),[])
        finally:a.close();b.close()

    def test_13_pending_amendment_does_not_change_published_value(self):
        a=self.connection();b=self.connection()
        try:
            with a:self.insert(a,3)
            self.assertEqual(b.execute(Q['approved'],(B,EB)).fetchone()[8],'1.123')
        finally:a.close();b.close()

    def test_14_parallel_sibling_approval_foreign_keys_clean(self):
        d=self.connection()
        try:
            with d:self.insert(d,3);self.insert(d,4)
            with d:self.approve(d,1)
            with self.assertRaises(sqlite3.IntegrityError):self.approve(d,2)
            self.assertEqual(d.execute('PRAGMA foreign_key_check').fetchall(),[])
        finally:d.close()

    def test_15_no_action_on_ambiguous_write_failure(self):
        a=self.connection()
        try:
            with a:self.insert(a,3)
            with self.assertRaises(sqlite3.IntegrityError):self.insert(a,3)
            self.assertEqual(a.execute('SELECT count(*) FROM lab_level_amendments_v059').fetchone()[0],1)
        finally:a.close()

if __name__=='__main__':unittest.main()
