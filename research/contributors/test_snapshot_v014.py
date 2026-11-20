# REMURA Experience v0.14 LAB — 20/11/2026
# Synthetic SQLite rehearsal. Journal pin is simulated in memory, not durable.
import hashlib
import json
import sqlite3
from pathlib import Path

SCHEMA = Path(__file__).with_name('snapshot_v014.sql').read_text()
GEN = 'fixture-v014'
EMPTY = (GEN, 0, '')


def digest(body):
    return hashlib.sha256(body.encode('utf-8')).hexdigest()


def connect():
    db = sqlite3.connect(':memory:', isolation_level=None)
    db.executescript(SCHEMA)
    return db


def read_head(db):
    row = db.execute('SELECT h.generation,h.revision,h.digest,r.payload,r.as_of FROM fixture_head h JOIN fixture_revision r ON (h.revision,h.generation,h.digest)=(r.revision,r.generation,r.digest) WHERE h.id=1').fetchone()
    if row is None:
        if db.execute('SELECT count(*) FROM fixture_revision').fetchone()[0]:
            raise ValueError('orphan')
        return EMPTY, None, None
    gen, rev, pin, body, as_of = row
    if digest(body) != pin:
        raise ValueError('digest')
    if db.execute('SELECT max(revision),count(*) FROM fixture_revision').fetchone() != (rev, rev):
        raise ValueError('history')
    return (gen, rev, pin), body, as_of


def checked_read(db, independent_pin):
    try:
        pin, body, _ = read_head(db)
        return body if pin == independent_pin else None
    except (ValueError, sqlite3.Error):
        return None


def publish(db, independent_pin, expected, as_of, value, approved, interrupt=False):
    # Only fixed test payload, never a financial-data validator or real authority.
    if approved is not True or type(value) is not int or not 0 <= value <= 100:
        return 'DENIED', independent_pin
    if type(as_of) is not str or as_of not in ('2026-11-20T16:00:00Z', '2026-11-20T16:01:00Z'):
        return 'DENIED', independent_pin
    body = json.dumps({'schema':'REMURA_SQL_FIXTURE','as_of':as_of,'value':value}, separators=(',',':'))
    try:
        db.execute('BEGIN IMMEDIATE')
        pin, _, previous = read_head(db)
        if pin != independent_pin or type(expected) is not int or expected != pin[1] or expected >= 32 or (previous and as_of < previous):
            db.rollback()
            return 'BLOCKED', independent_pin
        rev, sha = expected + 1, digest(body)
        db.execute('INSERT INTO fixture_revision VALUES(?,?,?,?,?)', (rev, GEN, as_of, sha, body))
        if expected == 0:
            db.execute('INSERT INTO fixture_head VALUES(1,?,?,?)', (rev, GEN, sha))
        else:
            cur = db.execute('UPDATE fixture_head SET revision=?,digest=? WHERE id=1 AND revision=? AND digest=?', (rev,sha,expected,pin[2]))
            if cur.rowcount != 1:
                raise ValueError('CAS')
        db.commit()
        # The independently held pin is advanced by the test harness only.
        # Crash before that point: fail closed, no repair or automatic adoption.
        return ('INTERRUPTED', independent_pin) if interrupt else ('PUBLISHED', (GEN,rev,sha))
    except (ValueError, sqlite3.Error):
        db.rollback()
        return 'BLOCKED', independent_pin


def run():
    checks = 0
    def ok(v):
        nonlocal checks
        assert v, f'check {checks+1}'
        checks += 1
    a, b = '2026-11-20T16:00:00Z', '2026-11-20T16:01:00Z'
    db = connect()
    ok(checked_read(db, EMPTY) is None)
    status, pin1 = publish(db, EMPTY, 0, a, 10, True)
    ok(status == 'PUBLISHED' and pin1[1] == 1)
    ok(json.loads(checked_read(db,pin1))['value'] == 10)
    backup = sqlite3.connect(':memory:', isolation_level=None)
    db.backup(backup)
    backup.execute('PRAGMA foreign_keys=ON')
    ok(publish(db,pin1,0,a,11,True)[0] == 'BLOCKED')
    ok(publish(db,pin1,1,a,11,False)[0] == 'DENIED')
    ok(publish(db,pin1,1,a,True,True)[0] == 'DENIED')
    status,pin2 = publish(db,pin1,1,b,20,True)
    ok(status == 'PUBLISHED' and pin2[1] == 2)
    ok(checked_read(db,pin1) is None and checked_read(backup,pin2) is None)
    ok(json.loads(checked_read(db,pin2))['value'] == 20)
    ok(publish(db,pin2,2,a,30,True)[0] == 'BLOCKED')
    ok(publish(backup,pin2,1,b,30,True)[0] == 'BLOCKED')
    for sql in ["UPDATE fixture_revision SET payload='x' WHERE revision=1", 'DELETE FROM fixture_revision WHERE revision=1', 'DELETE FROM fixture_head', 'UPDATE fixture_head SET revision=1', 'UPDATE fixture_head SET digest=\'bad\'']:
        try:
            db.execute(sql)
        except sqlite3.Error:
            ok(True)
        else:
            ok(False)
    status,unchanged = publish(db,pin2,2,b,30,True,interrupt=True)
    ok(status == 'INTERRUPTED' and unchanged == pin2)
    ok(checked_read(db,pin2) is None)
    ok(publish(db,pin2,2,b,40,True)[0] == 'BLOCKED')
    ok(checked_read(db,None) is None)
    # An administrator who alters both database and independent pin is outside this model.
    db2 = connect(); pin = EMPTY
    for i in range(32):
        status,pin = publish(db2,pin,i,a,i,True)
        assert status == 'PUBLISHED'
    ok(pin[1] == 32 and publish(db2,pin,32,a,33,True)[0] == 'BLOCKED')
    ok(db2.execute('SELECT count(*) FROM fixture_revision').fetchone()[0] == 32)
    ok(db2.execute('PRAGMA integrity_check').fetchone()[0] == 'ok')
    print(f'REMURA_SQL_FIXTURE_PASS={checks}; SQLITE={sqlite3.sqlite_version}')


if __name__ == '__main__':
    run()
