"""REMURA V30.4 LAB — 26/11/2026 06:57 CET.
Private local commitment ledger candidate. Not an independent timestamp witness.
No live use, external requests, or prospective admission.
"""
import hashlib,json,sqlite3
ARMS={"price_only","footprint_only","footprint_plus_cot"}
def canonical(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode()
def digest(raw):
    return hashlib.sha256(raw).hexdigest()
def initialize(db):
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if names-{"v304_commitments"}:raise ValueError("not_dedicated_db")
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS v304_commitments(
        id INTEGER PRIMARY KEY, frozen_ms INTEGER NOT NULL UNIQUE,
        previous TEXT NOT NULL, payload BLOB NOT NULL, commitment TEXT NOT NULL UNIQUE)""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS v304_no_update BEFORE UPDATE ON v304_commitments BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute("""CREATE TRIGGER IF NOT EXISTS v304_no_delete BEFORE DELETE ON v304_commitments BEGIN SELECT RAISE(ABORT,'append_only'); END""")
def record(db,decision,source_digests,clock,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    if db.in_transaction:raise ValueError("transaction")
    if decision.get("status")!="EXPLORATORY_RULE" or decision.get("prospective_admitted") is not False:
        raise ValueError("decision")
    sides=decision.get("sides",{})
    if set(sides)!=ARMS or any(type(x) is not int or x not in (-1,0,1) for x in sides.values()):raise ValueError("sides")
    if set(source_digests)!={"price","footprint","cot"} or any(type(v) is not str or len(v)!=64 or any(c not in "0123456789abcdef" for c in v) for v in source_digests.values()):raise ValueError("digests")
    now=clock()
    if type(now) is not int or now<=0:raise ValueError("clock")
    db.execute("BEGIN IMMEDIATE")
    try:
        last=db.execute("SELECT frozen_ms,commitment FROM v304_commitments ORDER BY id DESC LIMIT 1").fetchone()
        if last and now<=last[0]:raise ValueError("clock_regression")
        prev=last[1] if last else "0"*64
        # No future caller may supply a backdated freeze timestamp.
        payload=canonical({"schema":"remura-v304-local-freeze-v1","symbol":"EURUSD","frozen_ms":now,
            "rule":"v303_science_candidate","sides":sides,"source_sha256":source_digests,
            "previous":prev,"prospective_admitted":False})
        h=digest(payload)
        db.execute("INSERT INTO v304_commitments(frozen_ms,previous,payload,commitment) VALUES(?,?,?,?)",(now,prev,payload,h))
        db.commit()
    except BaseException:
        db.rollback();raise
    return {"commitment":h,"status":"LOCAL_COMMIT_ONLY","prospective_admitted":False}
def verify_chain(db):
    prev="0"*64; last=0;n=0
    for t,p,raw,h in db.execute("SELECT frozen_ms,previous,payload,commitment FROM v304_commitments ORDER BY id"):
        obj=json.loads(raw)
        if p!=prev or digest(raw)!=h or obj["previous"]!=prev or obj["frozen_ms"]!=t or t<=last or obj["prospective_admitted"] is not False:
            raise ValueError("chain")
        prev=h;last=t;n+=1
    return {"records":n,"local_integrity":True,"independent_witness":False,"prospective_admitted":False}
