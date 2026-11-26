"""REMURA V31.1 LAB — 26/11/2026. Private, unwitnessed same-feed science.
No network or orders. All price outcomes use only TradingView M5-derived M15.
"""
import hashlib,json,sqlite3
from v310_multifeed import tv_bar,m15,TV,M15
from v294_footprint_cvd import derive
from v299_source_correlation import cot_context
from v310_science_adapter import prepare,outcomes
HOURS=(1,4,24)
COSTS=(0,1,2)
def canonical(v):
    return json.dumps(v,sort_keys=True,separators=(",",":"),allow_nan=False).encode()
def digest(v):return hashlib.sha256(v).hexdigest()
def initialize(db):
    with db:
        db.execute("CREATE TABLE events(close_ms INTEGER PRIMARY KEY, received_ms INTEGER NOT NULL, seen_ms INTEGER NOT NULL, metadata BLOB NOT NULL, raw BLOB NOT NULL, digest TEXT NOT NULL)")
        db.execute("CREATE TABLE observations(id TEXT PRIMARY KEY, input_close_ms INTEGER UNIQUE NOT NULL, frozen_ms INTEGER NOT NULL, packet BLOB NOT NULL, cot BLOB NOT NULL, manifest BLOB NOT NULL)")
        db.execute("CREATE TABLE outcomes(id TEXT NOT NULL,hours INTEGER NOT NULL,cost INTEGER NOT NULL,asof_ms INTEGER NOT NULL,result BLOB NOT NULL,evidence BLOB NOT NULL,PRIMARY KEY(id,hours,cost),FOREIGN KEY(id) REFERENCES observations(id))")
        for t in ("events","observations","outcomes"):
            for op in ("UPDATE","DELETE"):
                db.execute("CREATE TRIGGER "+t+"_no_"+op.lower()+" BEFORE "+op+" ON "+t+" BEGIN SELECT RAISE(ABORT,'append_only'); END")
def ingest(db,rows,now):
    if len(rows)>576:raise ValueError("window")
    new=0
    with db:
        for m,raw,h in rows:
            tv_bar(m,raw,h,now)
            meta=canonical(m)
            old=db.execute("SELECT metadata,raw,digest FROM events WHERE close_ms=?",(m["bar_close_ms"],)).fetchone()
            if old is not None:
                if old!=(meta,raw,h):raise ValueError("conflicting_event")
                continue
            db.execute("INSERT INTO events VALUES(?,?,?,?,?,?)",(m["bar_close_ms"],m["received_at_ms"],now,meta,raw,h))
            new+=1
    return new
def records(db,asof,lower):
    return [(json.loads(m),raw,h) for m,raw,h in db.execute("SELECT metadata,raw,digest FROM events WHERE close_ms>? AND close_ms<=? AND received_ms<=? AND seen_ms<=? ORDER BY close_ms",(lower,asof,asof,asof))]
def observe_tick(db,cot_raw,manifest,clock,start_ms):
    now=clock()
    if now<start_ms:raise ValueError("clock")
    rows=records(db,now,now-86400000)
    if not rows:return "WAIT_TV"
    bars=m15([tv_bar(*r,now) for r in rows],now)
    if not bars:return "WAIT_COMPLETE_TV_M15"
    close=bars[-1]["close_ms"]
    if db.execute("SELECT 1 FROM observations WHERE input_close_ms=?",(close,)).fetchone():return "ALREADY_OBSERVED_BAR"
    f=derive([{"metadata":m,"original":raw,"sha256":h} for m,raw,h in rows],now)
    if not f:return "WAIT_FOOTPRINT"
    context=cot_context(json.loads(cot_raw),now)
    d=prepare(rows,now,{"status":"DESCRIPTIVE_ONLY",**f[-1]},context)
    if d["status"]!="TV_LOCAL_CANDIDATE_ONLY":return d["status"]
    freeze=clock()
    if not 0<=freeze-now<=5000 or freeze//M15!=now//M15 or (freeze//M15+1)*M15-freeze<5000:return "WAIT_FREEZE_BOUNDARY"
    # Record all source rows used, not only the final four M15 price bars.
    d.update({"frozen_ms":freeze,"entry_ms":(freeze//M15+1)*M15,
        "capture_ms":now,"input_close_ms":close,"source_records":[[m["bar_close_ms"],h] for m,raw,h in rows],
        "cot_sha256":digest(cot_raw),"manifest_sha256":digest(manifest)})
    blob=canonical(d);h=digest(blob)
    with db:db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?)",(h,close,freeze,blob,cot_raw,manifest))
    return "LOCAL_RECORDED_UNWITNESSED"
def evaluate_tick(db,now):
    saved=0;missing=0
    for h,freeze,blob,cot,manifest in db.execute("SELECT id,frozen_ms,packet,cot,manifest FROM observations ORDER BY frozen_ms").fetchall():
        d=json.loads(blob)
        if digest(blob)!=h or d["frozen_ms"]!=freeze or d["cot_sha256"]!=digest(cot) or d["manifest_sha256"]!=digest(manifest):raise ValueError("packet_integrity")
        historical=records(db,d["capture_ms"],d["capture_ms"]-86400000)
        if [[m["bar_close_ms"],sha] for m,raw,sha in historical]!=d["source_records"]:raise ValueError("input_integrity")
        for hours in HOURS:
            end=d["entry_ms"]+hours*3600000
            if end>now:continue
            rows=records(db,now,d["entry_ms"])
            rows=[r for r in rows if r[0]["bar_close_ms"]<=end]
            evidence=canonical([[m["bar_close_ms"],sha] for m,raw,sha in rows])
            with db:
                for cost in COSTS:
                    if db.execute("SELECT 1 FROM outcomes WHERE id=? AND hours=? AND cost=?",(h,hours,cost)).fetchone():continue
                    result=outcomes(d,rows,now,cost,hours)
                    if result["status"]!="RETROSPECTIVE_ONLY":
                        missing+=1;continue
                    db.execute("INSERT INTO outcomes VALUES(?,?,?,?,?,?)",(h,hours,cost,now,canonical(result),evidence));saved+=1
    return {"new_outcome_rows":saved,"missing_cost_horizons":missing}
def totals(db,now):
    rows=records(db,now,0)
    return {"m5":len(rows),"m15":len(m15([tv_bar(*r,now) for r in rows],now)),
        "local_observations":db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
        "outcome_rows":db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0],
        "certified_observations":0,"prospective_admitted":False}
