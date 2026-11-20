# REMURA Experience v0.16 LAB — 20/11/2026, 17:50 CET
# Synthetic-only durable witness. Separate authority/process is NOT deployed.
import hashlib
import hmac
import json
import os
import sqlite3

ZERO = '0' * 64
GEN = 'fixture-v016'
EMPTY = (0, ZERO, ZERO)


def valid(pin):
    return (type(pin) is tuple and len(pin) == 3 and type(pin[0]) is int
            and 0 <= pin[0] <= 32 and all(type(x) is str and len(x) == 64
            and all(c in '0123456789abcdef' for c in x) for x in pin[1:])
            and (pin == EMPTY if pin[0] == 0 else ZERO not in pin[1:]))


def tag(key, pin):
    if type(key) is not bytes or len(key) != 32 or not valid(pin):
        raise ValueError('invalid witness input')
    data = json.dumps([GEN, *pin], separators=(',', ':')).encode('ascii')
    return hmac.new(key, b'REMURA-WITNESS-V016\x00' + data, hashlib.sha256).hexdigest()


def open_witness(path, key, create=False):
    if create:
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    if not os.path.isfile(path) or os.path.islink(path):
        raise ValueError('witness unavailable')
    db = sqlite3.connect(path, isolation_level=None)
    try:
        db.execute('PRAGMA synchronous=FULL')
        if create:
            db.execute('BEGIN IMMEDIATE')
            db.execute('CREATE TABLE witness (id INTEGER PRIMARY KEY CHECK(id=1), rev INTEGER NOT NULL, journal TEXT NOT NULL, digest TEXT NOT NULL, auth TEXT NOT NULL) STRICT')
            db.execute('INSERT INTO witness VALUES(1,?,?,?,?)', (*EMPTY, tag(key, EMPTY)))
            db.commit()
        return db
    except Exception:
        db.close()
        raise


def read(db, key):
    rows = db.execute('SELECT id,rev,journal,digest,auth FROM witness LIMIT 2').fetchall()
    if len(rows) != 1 or rows[0][0] != 1:
        raise ValueError('witness missing')
    pin = tuple(rows[0][1:4])
    auth = rows[0][4]
    if type(auth) is not str or not hmac.compare_digest(tag(key, pin), auth):
        raise ValueError('witness authentication')
    return pin


def advance(db, key, expected, candidate, approved):
    # Trusted publisher adapter must verify journal linkage BEFORE calling.
    if approved is not True or not valid(expected) or not valid(candidate) or candidate[0] != expected[0]+1:
        return False
    try:
        db.execute('BEGIN IMMEDIATE')
        if read(db, key) != expected:
            db.rollback()
            return False
        db.execute('UPDATE witness SET rev=?,journal=?,digest=?,auth=? WHERE id=1', (*candidate, tag(key, candidate)))
        db.commit()
        return True
    except (ValueError, sqlite3.Error, TypeError):
        db.rollback()
        return False


def checked_payload(db, key, journal_head, archive_revision, body, authorized):
    # Adapter inputs must originate from verified archive and journal, not client.
    if authorized is not True or type(body) is not bytes or not 1 <= len(body) <= 8192 or type(archive_revision) is not int:
        return None
    try:
        pin = read(db, key)
        if pin[0] == 0 or journal_head != pin[:2] or archive_revision != pin[0] or hashlib.sha256(body).hexdigest() != pin[2]:
            return None
        return body if read(db, key) == pin else None
    except (ValueError, sqlite3.Error, TypeError):
        return None
