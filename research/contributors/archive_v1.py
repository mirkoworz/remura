# REMURA Contributors v0.4 LAB — 14/11/2026 23:32 CET
"""Synthetic-only durable archive; trusted single-host caller, no HTTP/auth.
Never point at a production directory. Fixed LAB filename and application ID.
No automatic export, signal, promotion, migration or provider request.
"""
import json
import os
import re
import sqlite3
import stat
from contextlib import contextmanager
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from uuid import UUID
from ledger_v1 import Principal, PERIODS, KINDS, PRICE, _time

FILENAME = "contributors-synthetic-lab.sqlite3"
APP_ID = 0x52454D45
MAX_BYTES = 8 * 1024 * 1024
MAX_DAILY = 20
MAX_TOTAL = 200
ID = re.compile(r"[A-Za-z0-9_.-]{1,64}")
MARKET = re.compile(r"[A-Z0-9_]{1,24}")
PROVIDER = re.compile(r"[A-Z0-9_]{1,16}")
TICKER = re.compile(r"[A-Z0-9_.!-]{1,24}")
PRODUCTS = frozenset({"SPOT", "CFD", "FUTURE", "INDEX"})
FIELDS = frozenset({"request_id", "market", "provider", "ticker", "product", "contract",
                    "period", "kind", "price", "anchor_utc", "observed_utc", "note"})
SCHEMA = """
CREATE TABLE entries(
 id INTEGER PRIMARY KEY, subject TEXT NOT NULL, request_id TEXT NOT NULL,
 received_utc TEXT NOT NULL, payload TEXT NOT NULL, semantic TEXT NOT NULL,
 UNIQUE(subject,request_id), UNIQUE(subject,semantic));
CREATE TABLE reviews(
 id INTEGER PRIMARY KEY, entry_id INTEGER NOT NULL REFERENCES entries(id),
 owner TEXT NOT NULL, action TEXT NOT NULL CHECK(action IN ('APPROVED','REJECTED','REVOKED')),
 at_utc TEXT NOT NULL, reason TEXT NOT NULL);
CREATE TRIGGER entries_no_update BEFORE UPDATE ON entries BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER entries_no_delete BEFORE DELETE ON entries BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER reviews_no_update BEFORE UPDATE ON reviews BEGIN SELECT RAISE(ABORT,'immutable'); END;
CREATE TRIGGER reviews_no_delete BEFORE DELETE ON reviews BEGIN SELECT RAISE(ABORT,'immutable'); END;
"""

@dataclass(frozen=True)
class CatalogEntry:
    market: str
    provider: str
    ticker: str
    product: str
    contract: str
    source_group: str  # configured common source, not verified independence

    def key(self):
        return (self.market,self.provider,self.ticker,self.product,self.contract)

def _match(pattern, value):
    return type(value) is str and pattern.fullmatch(value) is not None

def _catalog(entry):
    if (type(entry) is not CatalogEntry or not _match(MARKET,entry.market)
        or not _match(PROVIDER,entry.provider) or not _match(TICKER,entry.ticker)
        or type(entry.product) is not str or entry.product not in PRODUCTS
        or not _match(ID,entry.source_group)
        or type(entry.contract) is not str
        or (entry.product=="FUTURE" and
            (not _match(TICKER,entry.contract) or "!" in entry.contract or "!" in entry.ticker))
        or (entry.product!="FUTURE" and entry.contract!="")):
        raise ValueError("catalog_entry")

def _text(value, *, required=False):
    if (type(value) is not str or len(value)>280
        or any(ord(c)<32 or 127<=ord(c)<=159 or 0xD800<=ord(c)<=0xDFFF for c in value)
        or (required and not value.strip())):
        raise ValueError("text")

def _json(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=True,separators=(",",":"))

class Archive:
    def __init__(self, root, *, catalog, contributors, owners, synthetic=False):
        if synthetic is not True:
            raise ValueError("synthetic_only")
        self.contributors=frozenset(contributors); self.owners=frozenset(owners)
        if (not self.contributors or not self.owners or self.contributors & self.owners
            or any(not _match(ID,x) for x in self.contributors | self.owners)):
            raise ValueError("roles")
        self.catalog={}
        for e in catalog:
            _catalog(e)
            if e.key() in self.catalog: raise ValueError("catalog_conflict")
            self.catalog[e.key()]=e
        if not self.catalog: raise ValueError("catalog_empty")
        root=Path(root)
        if not root.is_absolute() or root.resolve()!=root:
            raise ValueError("private_absolute_root")
        st=root.lstat()
        if not stat.S_ISDIR(st.st_mode) or st.st_uid!=os.getuid() or stat.S_IMODE(st.st_mode)!=0o700:
            raise ValueError("private_root")
        path=root/FILENAME
        # Do not silently consume another database or stale sidecars.
        if any(os.path.lexists(str(path)+suffix) for suffix in ("-wal","-shm","-journal")):
            raise ValueError("unexpected_sidecar")
        created=False
        try:
            fd=os.open(path,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        except FileExistsError:
            pass
        else:
            os.close(fd); created=True
        st=path.lstat()
        if (not stat.S_ISREG(st.st_mode) or st.st_uid!=os.getuid() or st.st_nlink!=1
            or stat.S_IMODE(st.st_mode)!=0o600 or st.st_size>MAX_BYTES):
            raise ValueError("private_file")
        self.db=sqlite3.connect(path.as_uri()+"?mode=rw",uri=True,timeout=1,isolation_level=None)
        self.db.row_factory=sqlite3.Row
        try:
            self.db.execute("PRAGMA trusted_schema=OFF")
            self.db.execute("PRAGMA foreign_keys=ON")
            if created:
                self.db.executescript("BEGIN IMMEDIATE;"+SCHEMA+
                    "PRAGMA application_id="+str(APP_ID)+";PRAGMA user_version=1;COMMIT;")
            if (self.db.execute("PRAGMA application_id").fetchone()[0]!=APP_ID
                or self.db.execute("PRAGMA user_version").fetchone()[0]!=1
                or self.db.execute("PRAGMA quick_check").fetchone()[0]!="ok"):
                raise ValueError("archive_identity")
            if self.db.execute("PRAGMA journal_mode").fetchone()[0].lower()!="delete":
                raise ValueError("journal_mode")
            pagesize=self.db.execute("PRAGMA page_size").fetchone()[0]
            self.db.execute("PRAGMA max_page_count="+str(MAX_BYTES//pagesize))
        except Exception:
            self.db.close()
            raise

    @contextmanager
    def _write(self):
        self.db.execute("BEGIN IMMEDIATE")
        try:
            yield
            self.db.execute("COMMIT")
        except BaseException:
            self.db.execute("ROLLBACK")
            raise

    def _role(self,p,role):
        allowed=self.contributors if role=="CONTRIBUTOR" else self.owners
        if type(p) is not Principal or p.role!=role or p.subject not in allowed:
            raise PermissionError("role_required")

    def _status(self,eid):
        row=self.db.execute("SELECT action,at_utc FROM reviews WHERE entry_id=? ORDER BY id DESC LIMIT 1",(eid,)).fetchone()
        return (row["action"],row["at_utc"]) if row else ("UNREVIEWED",None)

    def submit(self, principal, payload, *, received_utc):
        self._role(principal,"CONTRIBUTOR")
        received=_time(received_utc)
        if type(payload) is not dict or set(payload)!=FIELDS or any(type(v) is not str for v in payload.values()):
            raise ValueError("payload")
        req=payload["request_id"]
        if len(req)!=36 or str(UUID(req))!=req: raise ValueError("request_id")
        key=tuple(payload[k] for k in ("market","provider","ticker","product","contract"))
        entry=self.catalog.get(key)
        if entry is None: raise ValueError("mapping_not_authorized")
        if payload["period"] not in PERIODS or payload["kind"] not in KINDS:
            raise ValueError("classification")
        if not PRICE.fullmatch(payload["price"]) or Decimal(payload["price"])<=0: raise ValueError("price")
        _text(payload["note"])
        if not _time(payload["anchor_utc"])<=_time(payload["observed_utc"])<=received:
            raise ValueError("chronology")
        normalized=dict(payload,price=format(Decimal(payload["price"]).normalize(),"f"),
                        source_group=entry.source_group)
        encoded=_json(normalized)
        # Same author's same level, period anchor and exact source cannot inflate evidence.
        semantic=_json({k:v for k,v in normalized.items()
                        if k not in ("request_id","note","observed_utc","source_group")})
        with self._write():
            row=self.db.execute("SELECT id,payload,received_utc FROM entries WHERE subject=? AND request_id=?",(principal.subject,req)).fetchone()
            if row:
                if row["payload"]!=encoded or received_utc<row["received_utc"]:
                    raise ValueError("idempotency_conflict")
                return {"id":row["id"],"status":self._status(row["id"])[0],"duplicate":True}
            if self.db.execute("SELECT 1 FROM entries WHERE subject=? AND semantic=?",(principal.subject,semantic)).fetchone():
                raise ValueError("semantic_duplicate")
            count=self.db.execute("SELECT COUNT(*) FROM entries WHERE subject=? AND substr(received_utc,1,10)=?",(principal.subject,received_utc[:10])).fetchone()[0]
            total=self.db.execute("SELECT COUNT(*) FROM entries").fetchone()[0]
            if count>=MAX_DAILY or total>=MAX_TOTAL: raise ValueError("lab_capacity")
            last=self.db.execute("SELECT MAX(received_utc) FROM entries").fetchone()[0]
            if last is not None and received_utc<last: raise ValueError("receipt_clock_regression")
            cur=self.db.execute("INSERT INTO entries(subject,request_id,received_utc,payload,semantic) VALUES(?,?,?,?,?)",
                                (principal.subject,req,received_utc,encoded,semantic))
            return {"id":cur.lastrowid,"status":"UNREVIEWED","duplicate":False}

    def review(self, principal, eid, action, *, at_utc, reason):
        self._role(principal,"OWNER")
        if type(eid) is not int or eid<=0: raise ValueError("entry_id")
        _time(at_utc); _text(reason,required=True)
        with self._write():
            row=self.db.execute("SELECT received_utc,payload FROM entries WHERE id=?",(eid,)).fetchone()
            if row is None: raise ValueError("entry_unknown")
            status,previous=self._status(eid)
            permitted={"UNREVIEWED":("APPROVED","REJECTED"),"APPROVED":("REVOKED",)}
            if action not in permitted.get(status,()): raise ValueError("review_transition")
            last=self.db.execute("SELECT MAX(at_utc) FROM reviews").fetchone()[0]
            if at_utc<row["received_utc"] or (previous and at_utc<=previous) or (last and at_utc<last):
                raise ValueError("review_clock")
            if action=="APPROVED":
                p=json.loads(row["payload"])
                current=self.catalog.get(tuple(p[k] for k in ("market","provider","ticker","product","contract")))
                if current is None or current.source_group!=p["source_group"]:
                    raise ValueError("mapping_changed")
            self.db.execute("INSERT INTO reviews(entry_id,owner,action,at_utc,reason) VALUES(?,?,?,?,?)",
                            (eid,principal.subject,action,at_utc,reason))
        return {"id":eid,"status":action,"scientific_admission":False}

    def receipts(self, principal):
        self._role(principal,"CONTRIBUTOR")
        return self._list(principal.subject)

    def queue(self, principal):
        self._role(principal,"OWNER")
        return self._list(None)

    def _list(self,subject):
        sql="SELECT id,subject,received_utc,payload FROM entries"
        rows=self.db.execute(sql+(" WHERE subject=?" if subject is not None else "")+" ORDER BY id DESC",
                             (subject,) if subject is not None else ()).fetchall()
        result=[]
        for row in rows:
            status,at=self._status(row["id"])
            item={"id":row["id"],"received_utc":row["received_utc"],"data":json.loads(row["payload"]),"status":status,"reviewed_utc":at}
            if subject is None:
                item["subject"]=row["subject"]
                item["history"]=[dict(r) for r in self.db.execute("SELECT owner,action,at_utc,reason FROM reviews WHERE entry_id=? ORDER BY id",(row["id"],))]
            result.append(item)
        return result

    def close(self):
        self.db.close()
