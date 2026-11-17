# REMURA v0.8.124 LAB — 17/11/2026 08:24 CET
"""Closed synthetic snapshot fingerprint and exact restore comparison.
No real DB access, backup transfer, independent authority or restore permission.
"""
import hashlib,hmac,json,re,sqlite3
from contextlib import closing
from pathlib import Path
from level_transport_receiver_lab_v1 import decode,digest
ROOT=Path(__file__).parent/"gateway-lab"
SCHEMAS=("level_admission_candidate.sql","level_receipt_candidate.sql","level_permit_ledger_candidate.sql")
HEX=re.compile(r"[0-9a-f]{64}")
MAX_MS=4102444800000
def need(ok):
    if not ok:raise ValueError("custody_fixture_denied")
def hex64(x):return type(x) is str and HEX.fullmatch(x) is not None
def integer(x,low,high):return type(x) is int and low<=x<=high
def canonical(x):
    raw=json.dumps(x,ensure_ascii=True,sort_keys=True,separators=(",",":"),allow_nan=False).encode("ascii")
    need(len(raw)<=2*1024*1024)
    return raw
def hashobj(x):return hashlib.sha256(canonical(x)).hexdigest()
def catalog(db):
    return [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name LIMIT 65")]
def expected_catalog():
    with closing(sqlite3.connect(":memory:")) as db:
        for f in SCHEMAS:db.executescript((ROOT/f).read_text())
        return catalog(db)
def bounded_rows(db,query,limit):
    rows=[tuple(r) for r in db.execute(query+" LIMIT ?",(limit+1,))]
    need(len(rows)<=limit)
    return rows
def snapshot(db,*,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and isinstance(db,sqlite3.Connection) and not db.in_transaction)
    # Synthetic snapshots may only be inspected in an isolated memory connection.
    # In-memory provenance does not itself prove the records are synthetic.
    need([tuple(r) for r in db.execute("PRAGMA database_list")]==[(0,"main","")])
    need(db.execute("PRAGMA query_only").fetchone()[0]==1)
    db.execute("BEGIN")
    try:
        schema=catalog(db)
        need(schema==expected_catalog())
        need([tuple(r) for r in db.execute("PRAGMA quick_check")]==[("ok",)])
        need(db.execute("PRAGMA foreign_key_check").fetchone() is None)
        a=bounded_rows(db,"SELECT id,pin,enabled,attempts,last_ms,window_count,allowed FROM level_admission_v1 ORDER BY id",1)
        s=bounded_rows(db,"SELECT id,pin,config_digest,chart_type,timezone,session_name,cutoff_ms FROM level_receipt_session_v1 ORDER BY id",1)
        need(len(a)==len(s)==1)
        _,pin,enabled,attempts,last,window,allowed=a[0]
        _,sp,cfg,chart,zone,session,cutoff=s[0]
        need(hex64(pin) and pin==sp and hex64(cfg) and enabled==allowed==0)
        need(integer(attempts,0,48) and integer(window,0,min(20,attempts)))
        need((attempts==0 and last is None and window==0) or (attempts>0 and integer(last,1,MAX_MS-1) and window>0))
        need(integer(cutoff,1,MAX_MS-1) and cutoff%300000==0)
        need(all(type(x) is str and 1<=len(x)<=100 for x in (chart,zone,session)))
        need(not bounded_rows(db,"SELECT close_ms FROM level_receipts_v1",0))
        permits=bounded_rows(db,"SELECT attempt,pin,received_ms FROM level_permits_v2 ORDER BY attempt",48)
        finals=bounded_rows(db,"SELECT attempt,completed_ms,outcome,close_ms,received_ms,sender_ms,digest,body,present_levels FROM level_finalizations_v2 ORDER BY attempt",48)
        lookup={};previous=0;minute_counts={}
        for attempt,p,received in permits:
            need(integer(attempt,1,attempts) and p==pin and attempt not in lookup and integer(received,1,MAX_MS-1))
            need(last is not None and previous<=received<=last)
            minute=received//60000
            minute_counts[minute]=minute_counts.get(minute,0)+1
            need(minute_counts[minute]<=20)
            lookup[attempt]=received;previous=received
        stored={};seen=set()
        for attempt,done,outcome,close,received,sender,body_hash,body,n in finals:
            need(attempt in lookup and attempt not in seen and received==lookup[attempt])
            seen.add(attempt)
            need(integer(done,received,min(received+5000,MAX_MS-1)) and integer(close,cutoff+1,MAX_MS-1) and close%300000==0)
            need(integer(received,close,min(close+120000,MAX_MS-1)) and integer(sender,close,received) and hex64(body_hash) and integer(n,0,6))
            need(outcome in ("STORED_SYNTHETIC","DUPLICATE","CONFLICT","CAPACITY_OR_ORDER"))
            if outcome=="STORED_SYNTHETIC":
                need(type(body) is str and 1<=len(body.encode("utf-8"))<=15000 and digest(body)==body_hash and close not in stored)
                row,_,valid=decode(body)
                need((row["snapshot_close_ms"],row["sender_clock_ms"],row["chart_type"],row["timezone"],row["session"],valid["configuration_digest"],valid["present_levels"])==(close,sender,chart,zone,session,cfg,n))
                stored[close]=(received,body_hash)
            else:need(body is None)
        need(len(stored)<=12)
        ordered=[stored[k][0] for k in sorted(stored)]
        need(ordered==sorted(ordered))
        for _,_,outcome,close,_,_,body_hash,_,_ in finals:
            if outcome=="DUPLICATE":need(close in stored and stored[close][1]==body_hash)
            elif outcome=="CONFLICT":need(close in stored and stored[close][1]!=body_hash)
        # Exact logical snapshot: covers even burned attempts without a permit,
        # unused permits, STOP state, schema and every stored/non-stored finalization.
        manifest={"schema":"remura.tv.level.synthetic.custody.v1","catalog_digest":hashobj(schema),
                  "state_digest":hashobj([a,s,permits,finals]),"attempts":attempts,"permits":len(permits),
                  "finalizations":len(finals),"receipts":len(stored),"closed":True}
        return manifest,hashobj(manifest)
    finally:db.rollback()
def verify_snapshot(db,expected_pin,*,synthetic=False,ingress_closed=False):
    need(hex64(expected_pin))
    m,p=snapshot(db,synthetic=synthetic,ingress_closed=ingress_closed)
    need(hmac.compare_digest(p,expected_pin))
    return {"status":"SYNTHETIC_EXACT_SNAPSHOT_MATCH","receipts":m["receipts"],"attempts":m["attempts"],
            "independent_pin_verified":False,"backup_encrypted":False,"restore_authorized":False,
            "may_open":False,"scientific_admission":False}
