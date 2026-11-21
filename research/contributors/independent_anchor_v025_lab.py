# REMURA Experience v0.25 LAB — 21/11/2026 07:21 CET
# Synthetic single-machine simulation of two restore domains. NOT independent custody.
import hashlib
import hmac
import json
import sqlite3
from contextlib import closing
from pathlib import Path

GEN = 'REMURA_MONOTONIC_FIXTURE_V025'
ZERO = '0' * 64
KEY_WITNESS = b'remura-v025-public-witness-fixture-key'
KEY_OWNER = b'remura-v025-public-owner-fixture-key'


class Denied(ValueError):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False)


def tag(key, values):
    return hmac.new(key, canonical(values).encode('ascii'), hashlib.sha256).hexdigest()


def hex64(value):
    return type(value) is str and len(value) == 64 and all(c in '0123456789abcdef' for c in value)


def approval(seq, digest, disposition, expiry, at, owner):
    return tag(KEY_OWNER, [GEN, seq, digest, disposition, expiry, at, owner])


def row_fields(row):
    return list(row[:-1])


class WitnessFixture:
    """Witness stored separately *by path*, NOT independent against host rollback."""
    def __init__(self, path, external_pin=None):
        self.path = Path(path)
        self.external_pin = external_pin

    def initialize(self):
        if self.path.exists():
            raise Denied('existing witness')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.executescript("""
              CREATE TABLE anchors(seq INTEGER PRIMARY KEY, generation TEXT NOT NULL,
                digest TEXT NOT NULL, disposition TEXT NOT NULL, expiry INTEGER NOT NULL,
                accepted_at INTEGER NOT NULL, owner TEXT NOT NULL, prior TEXT NOT NULL,
                tag TEXT NOT NULL);
              CREATE TRIGGER no_anchor_update BEFORE UPDATE ON anchors BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
              CREATE TRIGGER no_anchor_delete BEFORE DELETE ON anchors BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
            """)

    def _verified(self, db):
        rows = db.execute('SELECT seq,generation,digest,disposition,expiry,accepted_at,owner,prior,tag FROM anchors ORDER BY seq').fetchall()
        if len(rows) > 64:
            raise Denied('too many anchors')
        previous = ZERO
        for seq, row in enumerate(rows, 1):
            n, gen, d, disp, expiry, at, owner, prior, mac = row
            if (type(n) is not int or n != seq or gen != GEN or not hex64(d)
                or disp not in ('PUBLISHED', 'ABANDONED') or type(expiry) is not int
                or type(at) is not int or min(expiry, at) < 0
                or not isinstance(owner, str) or not 1 <= len(owner) <= 64
                or (disp == 'PUBLISHED' and at > expiry)
                or (disp == 'ABANDONED' and at <= expiry)
                or prior != previous or not hmac.compare_digest(mac, tag(KEY_WITNESS, row_fields(row)))):
                raise Denied('invalid witness chain')
            previous = mac
        if self.external_pin is not None:
            pin_seq, pin_tag = self.external_pin
            if (type(pin_seq) is not int or not 0 <= pin_seq <= len(rows)
                or not hex64(pin_tag) or (rows[pin_seq - 1][-1] if pin_seq else ZERO) != pin_tag):
                raise Denied('external monotonic pin rejected')
        return rows

    def rows(self):
        with closing(sqlite3.connect(self.path)) as db:
            return self._verified(db)

    def head(self):
        rows = self.rows()
        return (len(rows), rows[-1][-1] if rows else ZERO)

    def append(self, expected, digest, disposition, expiry, accepted_at, owner, permit):
        if (type(expected) is not tuple or len(expected) != 2 or
            type(expiry) is not int or type(accepted_at) is not int or
            not hex64(digest) or disposition not in ('PUBLISHED', 'ABANDONED') or
            type(owner) is not str or not 1 <= len(owner) <= 64 or
            not isinstance(permit, str)):
            raise Denied('invalid request')
        with closing(sqlite3.connect(self.path, timeout=3)) as db:
            db.execute('BEGIN IMMEDIATE')
            rows = self._verified(db)
            head = (len(rows), rows[-1][-1] if rows else ZERO)
            if expected != head or head[0] >= 64:
                raise Denied('witness compare-and-swap failed')
            seq = head[0] + 1
            if not hmac.compare_digest(permit, approval(seq, digest, disposition, expiry, accepted_at, owner)):
                raise Denied('approval mismatch')
            if (disposition == 'PUBLISHED' and accepted_at > expiry or
                disposition == 'ABANDONED' and accepted_at <= expiry):
                raise Denied('invalid expiry disposition')
            row = (seq, GEN, digest, disposition, expiry, accepted_at, owner, head[1])
            next_tag = tag(KEY_WITNESS, row)
            db.execute('INSERT INTO anchors VALUES (?,?,?,?,?,?,?,?,?)', (*row, next_tag))
            db.commit()
            return (seq, next_tag)


class PrimaryFixture:
    """Separate simulated restore domain; never treats intent alone as committed."""
    def __init__(self, path, witness):
        self.path = Path(path)
        self.witness = witness

    def initialize(self):
        if self.path.exists():
            raise Denied('existing primary')
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path)) as db:
            db.executescript("""
              CREATE TABLE intents(seq INTEGER PRIMARY KEY, digest TEXT NOT NULL,
                disposition TEXT NOT NULL, expiry INTEGER NOT NULL,
                accepted_at INTEGER NOT NULL, owner TEXT NOT NULL,
                previous_tag TEXT NOT NULL, permit TEXT NOT NULL);
              CREATE TABLE receipts(seq INTEGER PRIMARY KEY, witness_tag TEXT NOT NULL);
              CREATE TRIGGER no_intent_update BEFORE UPDATE ON intents BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
              CREATE TRIGGER no_intent_delete BEFORE DELETE ON intents BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
              CREATE TRIGGER no_receipt_update BEFORE UPDATE ON receipts BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
              CREATE TRIGGER no_receipt_delete BEFORE DELETE ON receipts BEGIN
                SELECT RAISE(ABORT, 'immutable fixture'); END;
            """)

    def _state(self):
        anchors = self.witness.rows()  # unavailable witness => fail closed
        with closing(sqlite3.connect(self.path)) as db:
            intents = db.execute('SELECT seq,digest,disposition,expiry,accepted_at,owner,previous_tag,permit FROM intents ORDER BY seq').fetchall()
            receipts = db.execute('SELECT seq,witness_tag FROM receipts ORDER BY seq').fetchall()
        if len(intents) > 64 or len(receipts) > len(intents) or len(anchors) > len(intents):
            raise Denied('invalid primary cardinality')
        for i, intent in enumerate(intents, 1):
            seq, d, disp, expiry, at, owner, prev, permit = intent
            if (seq != i or not hex64(d) or disp not in ('PUBLISHED','ABANDONED')
                or type(expiry) is not int or type(at) is not int or
                type(owner) is not str or not 1 <= len(owner) <= 64
                or not hex64(prev) or not isinstance(permit, str)
                or not hmac.compare_digest(permit, approval(seq, d, disp, expiry, at, owner))):
                raise Denied('invalid intent')
            if i <= len(anchors):
                a = anchors[i - 1]
                if (a[0] != seq or a[2:7] != (d,disp,expiry,at,owner) or a[7] != prev):
                    raise Denied('witness primary divergence')
        for i, receipt in enumerate(receipts, 1):
            if (receipt[0] != i or i > len(anchors) or receipt[1] != anchors[i-1][-1]):
                raise Denied('invalid receipt')
        return anchors, intents, receipts

    def prepare(self, digest, disposition, expiry, at, owner):
        anchors, intents, receipts = self._state()
        if len(intents) != len(receipts) or len(anchors) != len(receipts):
            raise Denied('unresolved prior intent')
        head = self.witness.head()
        seq = head[0] + 1
        permit = approval(seq, digest, disposition, expiry, at, owner)
        # Structural validation before recording intent.
        if (not hex64(digest) or disposition not in ('PUBLISHED','ABANDONED')
            or type(expiry) is not int or type(at) is not int or min(expiry,at) < 0
            or type(owner) is not str or not 1 <= len(owner) <= 64):
            raise Denied('invalid intent input')
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('INSERT INTO intents VALUES (?,?,?,?,?,?,?,?)',
                       (seq,digest,disposition,expiry,at,owner,head[1],permit))
            db.commit()
        return seq

    def commit_witness(self):
        anchors, intents, _ = self._state()
        if len(intents) != len(anchors) + 1:
            raise Denied('no outstanding intent')
        seq, d, disp, expiry, at, owner, prev, permit = intents[-1]
        return self.witness.append((len(anchors),prev),d,disp,expiry,at,owner,permit)

    def finalize(self):
        anchors, intents, receipts = self._state()
        if len(intents) != len(anchors):
            raise Denied('witness not committed')
        if len(receipts) == len(anchors):
            return 'ALREADY_ACKNOWLEDGED'
        if len(receipts) + 1 != len(anchors):
            raise Denied('gap in receipts')
        with closing(sqlite3.connect(self.path)) as db:
            db.execute('INSERT INTO receipts VALUES (?,?)', (len(anchors), anchors[-1][-1]))
            db.commit()
        return 'ACKNOWLEDGED'

    def read_status(self, now):
        try:
            anchors, intents, receipts = self._state()
            if (type(now) is not int or not anchors or len(anchors) != len(receipts)
                or len(intents) != len(anchors)):
                return None
            last = anchors[-1]
            if now < last[5] or now > last[4]:
                return None
            return 'PUBLISHED' if last[3] == 'PUBLISHED' else None
        except (Denied, OSError, sqlite3.Error, ValueError, TypeError):
            return None
