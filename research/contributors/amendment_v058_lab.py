# REMURA Contributors v0.58 LAB — 21/11/2026 CET
# Synthetic SQLite fixture only; actor identity is trusted IN-PROCESS, NEVER HTTP input.
import hashlib
import json
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal

PERIODS = {'DAY', 'WEEK', 'CURRENT_MONTH', 'PREVIOUS_MONTH'}
KINDS = {'DELTA_PEAK', 'EFFORT_RESULT', 'OTHER_VOLUME_LEVEL'}
FIELDS = {'market','provider','ticker','product','contract','period','kind','price','anchor_utc','observed_utc','note'}
STAMP = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z\Z')
REQ = re.compile(r'[a-f0-9]{8}(-[a-f0-9]{4}){3}-[a-f0-9]{12}\Z')
PRICE = re.compile(r'(?:0|[1-9]\d{0,7})(?:\.\d{1,8})?\Z')

class Denied(Exception):
    pass

def utc(value):
    if type(value) is not str or not STAMP.fullmatch(value):
        raise Denied('invalid UTC')
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc)
    except ValueError as e:
        raise Denied('invalid UTC') from e

def normalized(data, at):
    if type(data) is not dict or set(data) != FIELDS or any(type(v) is not str for v in data.values()):
        raise Denied('invalid fields')
    if not re.fullmatch(r'[A-Z0-9_]{1,24}', data['market']) or not re.fullmatch(r'[A-Z0-9_]{1,16}', data['provider']) or not re.fullmatch(r'[A-Z0-9_.!-]{1,24}', data['ticker']):
        raise Denied('instrument')
    if data['product'] not in {'SPOT','CFD','INDEX','FUTURE'} or (data['product'] == 'FUTURE' and (not re.fullmatch(r'[A-Z0-9_.-]{1,24}',data['contract']) or '!' in data['ticker'])) or (data['product'] != 'FUTURE' and data['contract'] != ''):
        raise Denied('contract')
    if data['period'] not in PERIODS or data['kind'] not in KINDS:
        raise Denied('classification')
    p = data['price'].replace(',', '.')
    if not PRICE.fullmatch(p) or Decimal(p) <= 0:
        raise Denied('price')
    if len(data['note']) > 280 or any(ord(ch) < 32 or 0x7f <= ord(ch) <= 0x9f for ch in data['note']):
        raise Denied('note')
    if not utc(data['anchor_utc']) <= utc(data['observed_utc']) <= utc(at):
        raise Denied('clock')
    return dict(data, price=format(Decimal(p).normalize(),'f'))

class AmendmentLab:
    def __init__(self):
        self.db = sqlite3.connect(':memory:', isolation_level=None)
        self.db.execute('PRAGMA foreign_keys=ON')
        self.db.executescript('''
          CREATE TABLE identities(subject TEXT PRIMARY KEY, role TEXT NOT NULL CHECK(role IN ('OWNER','CONTRIBUTOR')), revoked INT NOT NULL DEFAULT 0 CHECK(revoked IN (0,1)));
          CREATE TABLE entries(id INTEGER PRIMARY KEY, subject TEXT NOT NULL REFERENCES identities(subject), request_id TEXT NOT NULL,
            base_id INTEGER REFERENCES entries(id), predecessor_sha TEXT, payload TEXT NOT NULL, created_utc TEXT NOT NULL,
            UNIQUE(subject,request_id),CHECK((base_id IS NULL AND predecessor_sha IS NULL) OR (base_id IS NOT NULL AND length(predecessor_sha)=64)));
          CREATE TABLE reviews(entry_id INTEGER PRIMARY KEY REFERENCES entries(id), owner TEXT NOT NULL REFERENCES identities(subject), action TEXT NOT NULL CHECK(action IN ('APPROVED','REJECTED')), at_utc TEXT NOT NULL);
          CREATE TRIGGER entries_no_update BEFORE UPDATE ON entries BEGIN SELECT RAISE(ABORT,'immutable'); END;
          CREATE TRIGGER entries_no_delete BEFORE DELETE ON entries BEGIN SELECT RAISE(ABORT,'immutable'); END;
          CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT,'immutable'); END;
          CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT,'immutable'); END;
        ''')
        self.db.executemany('INSERT INTO identities(subject,role) VALUES (?,?)', [('fixture-owner','OWNER'),('fixture-a','CONTRIBUTOR'),('fixture-b','CONTRIBUTOR')])

    def close(self): self.db.close()

    @contextmanager
    def txn(self):
        self.db.execute('BEGIN IMMEDIATE')
        try:
            yield
            self.db.execute('COMMIT')
        except BaseException:
            self.db.execute('ROLLBACK')
            raise

    def gate(self, actor, role):
        if type(actor) is not str:
            raise Denied('identity')
        row = self.db.execute('SELECT role,revoked FROM identities WHERE subject=?',(actor,)).fetchone()
        if row != (role,0):
            raise Denied('permission')

    def submit(self, actor, request_id, payload, now_utc, base_id=None):
        # No browser-supplied subject or role. All writes and gates share one transaction.
        if type(request_id) is not str or not REQ.fullmatch(request_id): raise Denied('request')
        if base_id is not None and (type(base_id) is not int or base_id < 1): raise Denied('parent')
        data = normalized(payload, now_utc)
        encoded = json.dumps(data,sort_keys=True,separators=(',', ':'),ensure_ascii=True)
        with self.txn():
            self.gate(actor,'CONTRIBUTOR')
            previous = self.db.execute('SELECT id,base_id,predecessor_sha,payload FROM entries WHERE subject=? AND request_id=?',(actor,request_id)).fetchone()
            if previous:
                parent_sha = self._parent_digest(actor,base_id)
                if previous[1] != base_id or previous[2] != parent_sha or previous[3] != encoded:
                    raise Denied('idempotency-conflict')
                return {'id':previous[0],'state':'UNREVIEWED_OR_REVIEWED','duplicate':True}
            parent_sha = self._parent_digest(actor,base_id)
            cur = self.db.execute('INSERT INTO entries(subject,request_id,base_id,predecessor_sha,payload,created_utc) VALUES(?,?,?,?,?,?)',
                (actor,request_id,base_id,parent_sha,encoded,now_utc))
            return {'id':cur.lastrowid,'state':'PENDING_REVIEW','duplicate':False}

    def _parent_digest(self,actor,base_id):
        if base_id is None: return None
        row = self.db.execute('SELECT subject,base_id,payload FROM entries WHERE id=?',(base_id,)).fetchone()
        # Amend only original (one level) and only own original; no cross-user existence disclosure.
        if not row or row[0] != actor or row[1] is not None: raise Denied('parent')
        return hashlib.sha256(row[2].encode('ascii')).hexdigest()

    def review(self,actor,entry_id,action,now_utc):
        if type(entry_id) is not int or entry_id < 1 or action not in ('APPROVED','REJECTED'): raise Denied('review')
        utc(now_utc)
        with self.txn():
            self.gate(actor,'OWNER')
            row = self.db.execute('SELECT base_id,created_utc,subject FROM entries WHERE id=?',(entry_id,)).fetchone()
            if not row or utc(now_utc) < utc(row[1]): raise Denied('review')
            if action == 'APPROVED' and self.db.execute('SELECT revoked FROM identities WHERE subject=?',(row[2],)).fetchone() != (0,): raise Denied('revoked source')
            if self.db.execute('SELECT 1 FROM reviews WHERE entry_id=?',(entry_id,)).fetchone(): raise Denied('already reviewed')
            if action == 'APPROVED' and row[0] is not None:
                if not self.db.execute('SELECT 1 FROM reviews WHERE entry_id=? AND action=?',(row[0],'APPROVED')).fetchone(): raise Denied('base unapproved')
                if self.db.execute("SELECT 1 FROM entries e JOIN reviews r ON e.id=r.entry_id WHERE e.base_id=? AND r.action='APPROVED'",(row[0],)).fetchone(): raise Denied('another approved amendment')
            self.db.execute('INSERT INTO reviews VALUES (?,?,?,?)',(entry_id,actor,action,now_utc))
            return {'id':entry_id,'action':action}

    def revoke(self, actor, subject):
        with self.txn():
            self.gate(actor,'OWNER')
            cursor = self.db.execute("UPDATE identities SET revoked=1 WHERE subject=? AND role='CONTRIBUTOR' AND revoked=0",(subject,))
            if cursor.rowcount != 1: raise Denied('revoke')

    def own_receipts(self,actor):
        self.gate(actor,'CONTRIBUTOR')
        return self.db.execute('''SELECT e.id,e.base_id,COALESCE(r.action,'UNREVIEWED') AS review
            FROM entries e LEFT JOIN reviews r ON r.entry_id=e.id WHERE e.subject=? ORDER BY e.id''',(actor,)).fetchall()

    def owner_queue(self,actor):
        self.gate(actor,'OWNER')
        return self.db.execute('SELECT id,subject,base_id FROM entries ORDER BY id').fetchall()
