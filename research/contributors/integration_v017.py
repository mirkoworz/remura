# REMURA Experience v0.17 LAB — 20/11/2026, 17:54 CET
# Local synthetic integration only; no network, production identity or real secrets.
import fcntl
import hashlib
import json
import os
import sqlite3
from contextlib import contextmanager, ExitStack, closing
from pathlib import Path
import journal_v015 as journal
import witness_v016 as witness

SCHEMA = Path(__file__).with_name('snapshot_v014.sql').read_text()
JKEY, WKEY = b'j' * 32, b'w' * 32
DATES = ('2026-11-20T16:00:00Z', '2026-11-20T16:01:00Z')
ERRORS = (ValueError, TypeError, OSError, sqlite3.Error, OverflowError)


def body(rev, stamp, value):
    if type(rev) is not int or not 1 <= rev <= 32 or stamp not in DATES or type(value) is not int or not 0 <= value <= 100:
        raise ValueError('fixture fields')
    return journal.canonical({'schema':'REMURA_INTEGRATION_FIXTURE_V017','revision':rev,'as_of':stamp,'value':value}).decode('ascii')


def digest(text):
    return hashlib.sha256(text.encode('ascii')).hexdigest()


class Fixture:
    # Trusted local directory and cooperating processes only. Not an OS sandbox.
    def __init__(self, root):
        self.root = Path(root)
        self.archive = self.root / 'archive.sqlite'
        self.chain = self.root / 'journal.sqlite'
        self.anchor = self.root / 'witness.sqlite'
        self.lock = self.root / 'publish.lock'

    def initialize(self):
        # Explicit creation only, never automatic recovery.
        self.root.mkdir(mode=0o700, exist_ok=False)
        for path in (self.lock, self.archive):
            os.close(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600))
        with closing(self._archive()) as db:
            db.executescript(SCHEMA)
        with closing(journal.open_journal(self.chain, create=True)), closing(witness.open_witness(self.anchor, WKEY, create=True)):
            pass

    def _archive(self):
        if not self.archive.is_file() or self.archive.is_symlink():
            raise ValueError('archive missing')
        db = sqlite3.connect(self.archive, isolation_level=None)
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA synchronous=FULL')
        return db

    @contextmanager
    def _open(self):
        # One local lock spanning all DB operations and the final authorization check.
        fd = os.open(self.lock, os.O_RDWR | os.O_NOFOLLOW)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            with ExitStack() as stack:
                a = stack.enter_context(closing(self._archive()))
                j = stack.enter_context(closing(journal.open_journal(self.chain)))
                w = stack.enter_context(closing(witness.open_witness(self.anchor, WKEY)))
                yield a, j, w
        finally:
            os.close(fd)

    def _verified(self, a, j, w):
        pin = witness.read(w, WKEY)
        if journal.scan(j, JKEY) != pin[:2]:
            raise ValueError('journal mismatch')
        rows = a.execute('SELECT revision,generation,as_of,digest,payload FROM fixture_revision ORDER BY revision LIMIT 33').fetchall()
        heads = a.execute('SELECT id,revision,generation,digest FROM fixture_head LIMIT 2').fetchall()
        links = j.execute('SELECT record FROM chain ORDER BY seq LIMIT 33').fetchall()
        if len(rows) != pin[0] or len(links) != pin[0]:
            raise ValueError('revision mismatch')
        previous = ''
        for i, (rev, gen, stamp, sha, payload) in enumerate(rows, 1):
            parsed = json.loads(payload)
            if (type(parsed) is not dict or rev != i or gen != 'fixture-v014' or stamp < previous
                    or payload != body(i, stamp, parsed.get('value')) or digest(payload) != sha
                    or json.loads(links[i-1][0])['snapshot_digest'] != sha):
                raise ValueError('archive linkage')
            previous = stamp
        if not rows:
            if heads or pin != witness.EMPTY:
                raise ValueError('empty mismatch')
            return pin, None, ''
        if heads != [(1,pin[0],'fixture-v014',pin[2])] or rows[-1][3] != pin[2]:
            raise ValueError('head mismatch')
        return pin, rows[-1][4], previous

    def publish(self, expected, stamp, value, authorize, interrupt=None):
        # authorize is a trusted synthetic adapter, never a request field.
        try:
            if authorize() != 'OWNER' or type(expected) is not int or interrupt not in (None,'archive','journal','witness'):
                return 'DENIED'
            payload = body(expected+1, stamp, value)
            sha = digest(payload)
            with self._open() as (a,j,w):
                pin, _, previous = self._verified(a,j,w)
                if expected != pin[0] or stamp < previous or authorize() != 'OWNER':
                    return 'BLOCKED'
                a.execute('BEGIN IMMEDIATE')
                a.execute('INSERT INTO fixture_revision VALUES(?,?,?,?,?)',(expected+1,'fixture-v014',stamp,sha,payload))
                if expected == 0:
                    a.execute('INSERT INTO fixture_head VALUES(1,?,?,?)',(1,'fixture-v014',sha))
                else:
                    a.execute('UPDATE fixture_head SET revision=?,digest=? WHERE id=1',(expected+1,sha))
                a.commit()
                if interrupt == 'archive':
                    return 'INTERRUPTED'
                next_head = journal.append(j,JKEY,pin[:2],sha,True)
                if next_head is None or interrupt == 'journal':
                    return 'INTERRUPTED'
                if journal.scan(j,JKEY) != next_head or authorize() != 'OWNER':
                    return 'BLOCKED'
                candidate = (*next_head,sha)
                if not witness.advance(w,WKEY,pin,candidate,True):
                    return 'BLOCKED'
                if interrupt == 'witness':
                    return 'ACK_LOST'
                verified, result, _ = self._verified(a,j,w)
                return 'PUBLISHED' if verified == candidate and result == payload else 'BLOCKED'
        except ERRORS:
            return 'BLOCKED'

    def read(self, authorize):
        try:
            if authorize() != 'CONTRIBUTOR':
                return None
            with self._open() as (a,j,w):
                pin, payload, _ = self._verified(a,j,w)
                if payload is None or authorize() != 'CONTRIBUTOR':
                    return None
                return witness.checked_payload(w,WKEY,pin[:2],pin[0],payload.encode('ascii'),True)
        except ERRORS:
            return None
