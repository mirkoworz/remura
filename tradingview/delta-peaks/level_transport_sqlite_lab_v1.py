# REMURA v0.8.111 LAB — 16/11/2026 17:39 CET
"""Disposable SQLite receipt-store rehearsal, synthetic only. No HTTP or live adapter.
Stores only fixture payloads. Not authenticated custody, independent backup or production readiness.
"""
import json,os,re,hmac,sqlite3
from pathlib import Path
from level_local_probe_v1 import clock,need
from level_local_probe_batch_v1 import IDENTITY
from level_transport_receiver_lab_v1 import decode,digest,CAPACITY,LAG_MS

DDL_META="CREATE TABLE session (id INTEGER PRIMARY KEY CHECK(id=1), pin TEXT NOT NULL, enabled INTEGER NOT NULL CHECK(enabled IN (0,1)))"
DDL_ROWS="CREATE TABLE receipts (close_ms INTEGER PRIMARY KEY, first_received_ms INTEGER NOT NULL, body_digest TEXT NOT NULL, body TEXT NOT NULL, present_levels INTEGER NOT NULL CHECK(present_levels BETWEEN 0 AND 6))"
class PersistentReceiver:
    """Fixture-only single SQLite session. Every accepted write is one transaction.
    Reopening never rearms a stopped session. New store requires explicit create.
    Filesystem tampering, replacement and power-loss are not covered by this lab.
    """
    def __init__(self,path,*,key_hash,expected_identity,after_close_ms,now,
                 create=False,enabled=False,synthetic=False):
        need(synthetic is True and type(create) is bool and type(enabled) is bool and callable(now))
        need(create or not enabled)
        need(type(key_hash) is str and re.fullmatch(r"[0-9a-f]{64}",key_hash) is not None)
        need(type(expected_identity) is tuple and len(expected_identity)==len(IDENTITY)+1)
        self.cutoff=clock(after_close_ms);need(self.cutoff%300000==0)
        self._key=key_hash;self._identity=expected_identity;self._now=now
        self.path=Path(path).absolute()
        self.pin=digest(json.dumps([key_hash,expected_identity,self.cutoff],separators=(",",":"),allow_nan=False))
        need(self.path.name.endswith(".sqlite") and not self.path.is_symlink())
        if create:
            fd=os.open(self.path,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600);os.close(fd)
            # No auto-delete on initialization failure: retain for diagnosis.
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                db.execute(DDL_META);db.execute(DDL_ROWS)
                db.execute("INSERT INTO session VALUES(1,?,?)",(self.pin,int(enabled)))
        with self._connection() as db:
            self._check(db)
    def _connection(self):
        need(self.path.is_file() and not self.path.is_symlink())
        return _ClosingConnection(self.path.as_uri()+"?mode=rw",uri=True,timeout=2)
    def _check(self,db):
        rows=db.execute("SELECT id,pin,enabled FROM session").fetchall()
        need(len(rows)==1 and rows[0][0]==1 and rows[0][1]==self.pin and rows[0][2] in (0,1))
        data=db.execute("SELECT close_ms,first_received_ms,body_digest,body,present_levels FROM receipts ORDER BY close_ms LIMIT 13").fetchall()
        need(len(data)<=CAPACITY)
        prev_close=self.cutoff;prev_receive=None
        for close,received,body_hash,body,present in data:
            row,identity,validated=decode(body)
            need(identity==self._identity and close==row["snapshot_close_ms"] and close>prev_close)
            need(clock(received,whole_second=False)>=row["sender_clock_ms"] and received-close<=LAG_MS)
            need(prev_receive is None or received>=prev_receive)
            need(hmac.compare_digest(body_hash,digest(body)) and present==validated["present_levels"])
            prev_close=close;prev_receive=received
        return bool(rows[0][2]),data
    def stop(self):
        with self._connection() as db:
            db.execute("BEGIN IMMEDIATE")
            self._check(db)
            db.execute("UPDATE session SET enabled=0 WHERE id=1")
    def receive(self,raw,*,capability):
        try:
            with self._connection() as db:
                db.execute("BEGIN IMMEDIATE")
                # Read session before payload. Auth before reading fixture bodies.
                s=db.execute("SELECT pin,enabled FROM session WHERE id=1").fetchone()
                need(s is not None and s[0]==self.pin and s[1] in (0,1))
                if not s[1]:return {"status":"OFF"}
                if (type(capability) is not str or re.fullmatch(r"[0-9a-f]{64}",capability) is None
                    or not hmac.compare_digest(digest(capability),self._key)):
                    return {"status":"DENIED"}
                received=clock(self._now(),whole_second=False)
                row,identity,v=decode(raw);cl=row["snapshot_close_ms"]
                need(identity==self._identity and self.cutoff<cl<=row["sender_clock_ms"]<=received and received-cl<=LAG_MS)
                _,rows=self._check(db)
                body=digest(raw)
                for old in rows:
                    if old[0]!=cl:continue
                    if hmac.compare_digest(old[2],body):
                        return {"status":"DUPLICATE","first_received_ms":old[1]}
                    return {"status":"CONFLICT"}
                need(not rows or (cl>rows[-1][0] and received>=rows[-1][1]))
                if len(rows)>=CAPACITY:return {"status":"CAPACITY"}
                db.execute("INSERT INTO receipts VALUES(?,?,?,?,?)",(cl,received,body,raw,v["present_levels"]))
                return {"status":"ACCEPTED_SYNTHETIC","first_received_ms":received}
        except (sqlite3.Error,OSError):
            return {"status":"STORAGE_UNAVAILABLE"}
        except (ValueError,TypeError,OverflowError,RecursionError,KeyError):
            return {"status":"INVALID"}
    def summary(self):
        with self._connection() as db:
            db.execute("BEGIN")
            enabled,rows=self._check(db)
            return {"schema":"remura.tv.level.transport.sqlite.synthetic.audit.v1","accepted":len(rows),
                "present_slots":sum(r[4] for r in rows),"enabled":enabled,"capacity":CAPACITY,
                "origin":"SYNTHETIC","transactional_fixture_store":True,"durable_receipt":False,
                "receipt_authenticated":False,"source_attested":False,"scientific_admission":False,
                "comparison_admitted":False,"operational_signal":False}

class _ClosingConnection:
    def __init__(self,*args,**kw):
        self.db=sqlite3.connect(*args,**kw)
        try:self.db.execute("PRAGMA synchronous=FULL")
        except BaseException:self.db.close();raise
    def __enter__(self):return self.db
    def __exit__(self,typ,value,tb):
        try:
            if typ is None:self.db.commit()
            else:self.db.rollback()
        finally:self.db.close()
