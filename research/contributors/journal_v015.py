# REMURA Experience v0.15 LAB — 20/11/2026
# Local synthetic journal. A trusted external checkpoint is mandatory.
import hashlib
import hmac
import json
import os
import sqlite3

ZERO = '0' * 64
GEN = 'fixture-v015'
MAX_RECORDS = 32


def canonical(obj):
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def mac(key, rec):
    return hmac.new(key, b'REMURA-FIXTURE-JOURNAL-V015\x00' + canonical(rec), hashlib.sha256).hexdigest()


def hex64(x):
    return type(x) is str and len(x) == 64 and all(c in '0123456789abcdef' for c in x)


def open_journal(path, create=False):
    if create:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    if not os.path.isfile(path) or os.path.islink(path):
        raise ValueError('journal missing or invalid')
    db = sqlite3.connect(path, isolation_level=None)
    db.execute('PRAGMA synchronous=FULL')
    if create:
        db.execute('CREATE TABLE chain (seq INTEGER PRIMARY KEY CHECK(seq BETWEEN 1 AND 32), record TEXT NOT NULL CHECK(length(record)<=1024), tag TEXT NOT NULL CHECK(length(tag)=64)) STRICT')
    return db


def scan(db, key):
    if type(key) is not bytes or len(key) != 32:
        raise ValueError('key')
    rows = db.execute('SELECT seq,record,tag FROM chain ORDER BY seq LIMIT 33').fetchall()
    if len(rows) > MAX_RECORDS:
        raise ValueError('cap')
    previous = ZERO
    for i, (seq, text, tag) in enumerate(rows, 1):
        rec = json.loads(text)
        if (seq != i or type(rec) is not dict or set(rec) != {'generation','revision','snapshot_digest','prev'}
                or rec['generation'] != GEN or type(rec['revision']) is not int or rec['revision'] != i
                or rec['prev'] != previous or not hex64(rec['snapshot_digest']) or not hex64(tag)
                or canonical(rec).decode('ascii') != text or not hmac.compare_digest(mac(key, rec), tag)):
            raise ValueError('chain invalid')
        previous = tag
    return len(rows), previous


def verify(db, key, trusted):
    try:
        return trusted is not None and scan(db, key) == trusted
    except (sqlite3.Error, ValueError, TypeError):
        return False


def append(db, key, trusted, snapshot_digest, approved):
    if approved is not True or not hex64(snapshot_digest):
        return None
    try:
        db.execute('BEGIN IMMEDIATE')
        head = scan(db, key)
        if head != trusted or head[0] >= MAX_RECORDS:
            db.rollback()
            return None
        rec = {'generation':GEN,'revision':head[0]+1,'snapshot_digest':snapshot_digest,'prev':head[1]}
        tag = mac(key, rec)
        db.execute('INSERT INTO chain VALUES(?,?,?)', (rec['revision'],canonical(rec).decode('ascii'),tag))
        db.commit()
        # Candidate only. An independent authority must commit this pin before release.
        return rec['revision'], tag
    except (sqlite3.Error, ValueError, TypeError):
        db.rollback()
        return None
