# REMURA Experience v0.23 LAB — 20/11/2026 CET
# Synthetic isolated fixture; no real keys, credentials, authority, network or deployment.
import hashlib
from contextlib import closing
import hmac
import json
import sqlite3
from pathlib import Path

GEN = 'fixture-v023-abandonment'
AK, JK, UK, OK = (bytes([n]) * 32 for n in (61, 62, 63, 64))  # PUBLIC TEST KEYS
ZERO = '0' * 64


def canonical(obj):
    return json.dumps(obj, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False)


def mac(key, fields):
    return hmac.new(key, canonical(fields).encode('ascii'), hashlib.sha256).hexdigest()


def digest(raw):
    return hashlib.sha256(raw.encode('ascii')).hexdigest()


def permit(seq, intent, candidate_digest, action, reason, owner, timestamp):
    """Test-only owner approval. In production a protected signer is required."""
    values = [GEN, seq, intent, candidate_digest, action, reason, owner, timestamp]
    return mac(OK, values)


class Rejected(Exception):
    pass


class AbandonmentLab:
    def __init__(self, root, external_pin=None):
        self.root = Path(root)
        self.archive = self.root / 'archive' / 'archive.sqlite'
        self.journal = self.root / 'journal' / 'journal.sqlite'
        self.authority = self.root / 'authority' / 'authority.sqlite'
        self.external_pin = external_pin  # externally retained (seq, tag), NOT stored here
        self.revoked = set()

    def initialize(self):
        if self.root.exists():
            raise Rejected('fixture already exists')
        for path, schema in (
            (self.archive, 'CREATE TABLE candidates(seq INTEGER PRIMARY KEY, gen TEXT NOT NULL, intent TEXT UNIQUE NOT NULL, raw TEXT NOT NULL, digest TEXT NOT NULL, tag TEXT NOT NULL)'),
            (self.journal, 'CREATE TABLE entries(seq INTEGER PRIMARY KEY, digest TEXT NOT NULL, prev TEXT NOT NULL, tag TEXT NOT NULL)'),
            (self.authority, 'CREATE TABLE intents(seq INTEGER PRIMARY KEY, gen TEXT NOT NULL, intent TEXT UNIQUE NOT NULL, digest TEXT NOT NULL, expiry INTEGER NOT NULL, prev TEXT NOT NULL, tag TEXT NOT NULL); CREATE TABLE decisions(seq INTEGER PRIMARY KEY, intent TEXT UNIQUE NOT NULL, action TEXT NOT NULL, digest TEXT NOT NULL, journal_tag TEXT NOT NULL, prev TEXT NOT NULL, reason TEXT NOT NULL, owner TEXT NOT NULL, timestamp INTEGER NOT NULL, tag TEXT NOT NULL)')
        ):
            path.parent.mkdir(parents=True, mode=0o700)
            with closing(sqlite3.connect(path)) as db:
                db.executescript(schema)
                for table in ('candidates',) if path == self.archive else ('entries',) if path == self.journal else ('intents', 'decisions'):
                    for verb in ('UPDATE', 'DELETE'):
                        db.execute(f'CREATE TRIGGER block_{table}_{verb.lower()} BEFORE {verb} ON {table} BEGIN SELECT RAISE(ABORT,"immutable fixture"); END')

    @staticmethod
    def rows(path, sql):
        with closing(sqlite3.connect(path)) as db:
            return db.execute(sql).fetchall()

    def inspect(self):
        """Fail-closed complete chain validation; no market payload is returned."""
        i = self.rows(self.authority, 'SELECT seq,gen,intent,digest,expiry,prev,tag FROM intents ORDER BY seq')
        c = self.rows(self.archive, 'SELECT seq,gen,intent,raw,digest,tag FROM candidates ORDER BY seq')
        j = self.rows(self.journal, 'SELECT seq,digest,prev,tag FROM entries ORDER BY seq')
        e = self.rows(self.authority, 'SELECT seq,intent,action,digest,journal_tag,prev,reason,owner,timestamp,tag FROM decisions ORDER BY seq')
        if len(i) != len(c) or len(c) not in (len(e),len(e)+1) or len(j) not in (len(e),len(e)+1) or len(j)>len(c) or len(e)>32:
            raise Rejected('state cardinality')
        previous_auth = ZERO
        previous_journal = ZERO
        for n, (intent_row, candidate_row) in enumerate(zip(i,c), 1):
            seq, gen, intent, d, expiry, prior, tag = intent_row
            cs, cg, ci, raw, cd, ct = candidate_row
            if (seq != n or cs != n or gen != GEN or cg != GEN or not isinstance(expiry,int) or expiry < 0
                or prior != previous_auth or ci != intent or d != cd or digest(raw) != d
                or not hmac.compare_digest(tag, mac(UK,[seq,gen,intent,d,expiry,prior]))
                or not hmac.compare_digest(ct,mac(AK,[cs,cg,ci,raw,cd]))):
                raise Rejected('intent or candidate integrity')
            payload = json.loads(raw)
            if (type(payload) is not dict or set(payload) != {'schema','revision','as_of','market'}
                or payload['schema'] != 'REMURA_V023_SYNTHETIC_ONLY' or payload['revision'] != n
                or type(payload['as_of']) is not int or type(payload['market']) is not dict
                or canonical(payload) != raw):
                raise Rejected('candidate schema')
            if n <= len(j):
                js, jd, jp, jt = j[n-1]
                if (js != n or jd != d or jp != previous_journal or
                    not hmac.compare_digest(jt,mac(JK,[js,jd,jp]))):
                    raise Rejected('journal integrity')
                previous_journal=jt
            if n <= len(e):
                es, ei, action, ed, ej, ep, reason, owner, timestamp, et=e[n-1]
                if (es != n or ei != intent or action not in ('PUBLISHED','ABANDONED')
                    or ed != d or n>len(j) or ej != j[n-1][3] or ep != previous_auth
                    or type(timestamp) is not int or not owner
                    or (action == 'ABANDONED' and (reason != 'EXPIRED_PENDING' or timestamp <= expiry))
                    or (action == 'PUBLISHED' and (reason != 'APPROVED_SYNTHETIC' or timestamp > expiry))
                    or not hmac.compare_digest(et,mac(UK,[es,ei,action,ed,ej,ep,reason,owner,timestamp]))):
                    raise Rejected('authority decision integrity')
                previous_auth=et
        if self.external_pin is not None:
            pin_seq,pin_tag=self.external_pin
            if type(pin_seq) is not int or pin_seq<0 or pin_seq>len(e) or (e[pin_seq-1][9] if pin_seq else ZERO)!=pin_tag:
                raise Rejected('external monotonic pin mismatch')
        return {'intents':i,'candidates':c,'journal':j,'decisions':e,'head':(len(e),previous_auth)}

    def stage(self, intent, market, now, expiry, stage='archive'):
        if (type(intent) is not str or not 1<=len(intent)<=64 or type(market) is not dict
            or type(now) is not int or type(expiry) is not int or now>=expiry
            or stage not in ('archive','journal')):
            raise Rejected('invalid stage')
        state=self.inspect()
        seq=len(state['decisions'])+1
        if (len(state['candidates'])!=len(state['decisions']) or seq>32 or
            (state['decisions'] and now < state['decisions'][-1][8]) or
            any(r[2]==intent for r in state['intents'])):
            raise Rejected('pending or duplicate')
        raw=canonical({'schema':'REMURA_V023_SYNTHETIC_ONLY','revision':seq,'as_of':now,'market':market})
        if len(raw)>8192:
            raise Rejected('payload cap')
        d=digest(raw)
        prior=state['head'][1]
        with closing(sqlite3.connect(self.authority)) as db:
            db.execute('INSERT INTO intents VALUES(?,?,?,?,?,?,?)',(seq,GEN,intent,d,expiry,prior,mac(UK,[seq,GEN,intent,d,expiry,prior])))
            db.commit()
        with closing(sqlite3.connect(self.archive)) as db:
            db.execute('INSERT INTO candidates VALUES(?,?,?,?,?,?)',(seq,GEN,intent,raw,d,mac(AK,[seq,GEN,intent,raw,d])))
            db.commit()
        if stage=='journal':
            self._append_journal(seq,d)
        self.inspect()
        return d

    def _append_journal(self,seq,d):
        entries=self.rows(self.journal,'SELECT seq,digest,prev,tag FROM entries ORDER BY seq')
        if len(entries)!=seq-1:
            raise Rejected('journal append sequence')
        prior=entries[-1][3] if entries else ZERO
        with closing(sqlite3.connect(self.journal)) as db:
            db.execute('INSERT INTO entries VALUES(?,?,?,?)',(seq,d,prior,mac(JK,[seq,d,prior])))
            db.commit()

    def decide(self, intent, action, reason, owner, timestamp, approval, before_cas=None, interrupt=False):
        """Explicit authenticated synthetic approval; no automatic expiry adoption."""
        if (action not in ('ABANDONED','PUBLISHED') or type(timestamp) is not int or
            type(owner) is not str or not 1<=len(owner)<=64 or type(interrupt) is not bool):
            raise Rejected('invalid decision')
        s=self.inspect()
        seq=len(s['decisions'])+1
        if len(s['candidates'])!=seq:
            raise Rejected('no pending candidate')
        ir=s['intents'][-1]
        if intent!=ir[2] or (s['decisions'] and timestamp < s['decisions'][-1][8]) or action=='ABANDONED' and (reason!='EXPIRED_PENDING' or timestamp<=ir[4]):
            raise Rejected('intent or expiry')
        if action=='PUBLISHED' and (reason!='APPROVED_SYNTHETIC' or timestamp>ir[4]):
            raise Rejected('publication no longer fresh')
        d=ir[3]
        expected=permit(seq,intent,d,action,reason,owner,timestamp)
        if (type(approval) is not str or not hmac.compare_digest(approval,expected)
            or (seq,intent) in self.revoked):
            raise Rejected('owner approval')
        if len(s['journal'])==seq-1:
            self._append_journal(seq,d)  # retained on interrupted operation
        if interrupt:
            return 'INTERRUPTED'
        if before_cas is not None:
            before_cas()
        if (seq,intent) in self.revoked:
            raise Rejected('revoked before CAS')
        s=self.inspect()
        if len(s['decisions'])!=seq-1 or len(s['journal'])!=seq:
            raise Rejected('authority CAS precondition')
        journal_tag=s['journal'][-1][3]
        prior=s['head'][1]
        fields=[seq,intent,action,d,journal_tag,prior,reason,owner,timestamp]
        tag=mac(UK,fields)
        with closing(sqlite3.connect(self.authority)) as db:
            db.execute('BEGIN IMMEDIATE')
            last=db.execute('SELECT seq,tag FROM decisions ORDER BY seq DESC LIMIT 1').fetchone()
            if (last or (0,ZERO)) != (seq-1,prior):
                raise Rejected('authority compare-and-swap')
            db.execute('INSERT INTO decisions VALUES(?,?,?,?,?,?,?,?,?,?)',(*fields,tag))
            db.commit()
        self.inspect()
        return action

    def deliver(self, now):
        """V0.23 fixture result, NOT a V2 wire response or production integration."""
        try:
            s=self.inspect()
            if not s['decisions'] or len(s['decisions'])!=len(s['candidates']):
                return None
            event=s['decisions'][-1]
            if (event[2]!='PUBLISHED' or type(now) is not int or now<event[8] or
                now>s['intents'][-1][4]):
                return None
            return json.loads(s['candidates'][-1][3])
        except (Rejected,sqlite3.Error,ValueError,TypeError,KeyError):
            return None
