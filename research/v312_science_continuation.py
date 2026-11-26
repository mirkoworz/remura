"""V31.2 LAB — bounded continuation of the V31.1 same-feed ledger.
Only a dedicated private copy of the completed pilot may be modified.
No scheduler, provider requests or external timestamp.
"""
import json,sqlite3
from v311_science import records,canonical,digest,observe_tick,ingest,HOURS,COSTS
from v310_science_adapter import outcomes
M5=300000
GRACE=48*3600000
def prepare(db):
    names={x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if not {"events","observations","outcomes"}<=names or names-{"events","observations","outcomes","terminal_missing"}:raise ValueError("schema")
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS terminal_missing(id TEXT,hours INTEGER,recorded_ms INTEGER,reason TEXT NOT NULL,PRIMARY KEY(id,hours),FOREIGN KEY(id) REFERENCES observations(id))")
        for op in ("UPDATE","DELETE"):
            db.execute("CREATE TRIGGER IF NOT EXISTS terminal_missing_no_"+op.lower()+" BEFORE "+op+" ON terminal_missing BEGIN SELECT RAISE(ABORT,'append_only'); END")
def evaluate_pending(db,now,limit=32):
    if type(now) is not int or now<=0 or type(limit) is not int or not 1<=limit<=32:raise ValueError("scope")
    saved=terminal=waiting=0
    for hours in HOURS:
        rows=db.execute("""SELECT o.id,o.frozen_ms,o.packet,o.cot,o.manifest
          FROM observations o
          WHERE CAST(json_extract(o.packet,'$.entry_ms') AS INTEGER)+?<=?
          AND NOT EXISTS(SELECT 1 FROM terminal_missing m WHERE m.id=o.id AND m.hours=?)
          AND (SELECT COUNT(*) FROM outcomes x WHERE x.id=o.id AND x.hours=?)<3
          ORDER BY o.frozen_ms LIMIT ?""",(hours*3600000,now,hours,hours,limit)).fetchall()
        for h,freeze,blob,cot,manifest in rows:
            d=json.loads(blob)
            if digest(blob)!=h or d["frozen_ms"]!=freeze or d["cot_sha256"]!=digest(cot) or d["manifest_sha256"]!=digest(manifest) or d["prospective_admitted"] is not False:raise ValueError("packet")
            hist=records(db,d["capture_ms"],d["capture_ms"]-86400000)
            if [[m["bar_close_ms"],sha] for m,raw,sha in hist]!=d["source_records"]:raise ValueError("input_integrity")
            entry=d["entry_ms"];end=entry+hours*3600000
            future=[r for r in records(db,now,entry) if r[0]["bar_close_ms"]<=end]
            complete=[r[0]["bar_close_ms"] for r in future]==list(range(entry+M5,end+1,M5))
            if not complete:
                if now>=end+GRACE:
                    with db:db.execute("INSERT INTO terminal_missing VALUES(?,?,?,?)",(h,hours,now,"M5_COVERAGE_UNAVAILABLE"))
                    terminal+=1
                else:waiting+=1
                continue
            evidence=canonical([[m["bar_close_ms"],sha] for m,raw,sha in future])
            with db:
                for cost in COSTS:
                    if db.execute("SELECT 1 FROM outcomes WHERE id=? AND hours=? AND cost=?",(h,hours,cost)).fetchone():continue
                    result=outcomes(d,future,now,cost,hours)
                    if result["status"]!="RETROSPECTIVE_ONLY":raise ValueError("evaluator")
                    db.execute("INSERT INTO outcomes VALUES(?,?,?,?,?,?)",(h,hours,cost,now,canonical(result),evidence))
                    saved+=1
    return {"new_outcome_rows":saved,"waiting_horizons":waiting,"terminal_missing_added":terminal,"prospective_admitted":False}
def summary(db):
    return {"m5":db.execute("SELECT COUNT(*) FROM events").fetchone()[0],
       "local_observations":db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
       "outcome_rows":db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0],
       "terminal_missing":db.execute("SELECT COUNT(*) FROM terminal_missing").fetchone()[0],
       "certified_observations":0,"prospective_admitted":False}
