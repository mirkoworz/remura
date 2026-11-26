"""V30.8 bounded local historical archive and paired evaluator.
No provider access; no prospective admission. Conflicting bars excluded.
"""
import json
from decimal import Decimal
from v308_queue import initialize as init_queue,price_view,digest,canonical,HORIZONS,COSTS,summary,M15
from v300_paired_outcomes import evaluate,dec
MAX_OBS=64
GRACE=48*3600000
def initialize(db):
    init_queue(db)
    with db:
        db.execute("CREATE TABLE IF NOT EXISTS price_snapshots(hash TEXT PRIMARY KEY,captured_ms INTEGER NOT NULL,updated_ms INTEGER NOT NULL,raw BLOB NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS price_bars(open_ms INTEGER PRIMARY KEY,bar BLOB NOT NULL,source_hash TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS bar_conflicts(open_ms INTEGER PRIMARY KEY,source_hash TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS terminal_missing(commitment TEXT,hours INTEGER,recorded_ms INTEGER,PRIMARY KEY(commitment,hours))")
        for table in ("price_snapshots","price_bars","bar_conflicts","terminal_missing"):
            for action in ("UPDATE","DELETE"):
                db.execute("CREATE TRIGGER IF NOT EXISTS "+table+"_no_"+action.lower()+" BEFORE "+action+" ON "+table+" BEGIN SELECT RAISE(ABORT,'append_only'); END")
def archive(db,raw,captured):
    if type(raw) is not bytes or not 0<len(raw)<=4000000:raise ValueError("size")
    updated,bars=price_view(raw,captured)
    h=digest(raw)
    if db.execute("SELECT 1 FROM price_snapshots WHERE hash=?",(h,)).fetchone():return 0
    with db:
        db.execute("INSERT INTO price_snapshots VALUES(?,?,?,?)",(h,captured,updated,raw))
        for v in bars:
            o,hi,lo,c=(dec(v[k]) for k in ("o","h","l","c"))
            if min(o,hi,lo,c)<=0 or hi<max(o,lo,c) or lo>min(o,hi,c):raise ValueError("ohlc")
            bar=canonical({"open_ms":v["open_ms"],**{k:str(dec(v[k]).normalize()) for k in ("o","h","l","c")}})
            previous=db.execute("SELECT bar FROM price_bars WHERE open_ms=?",(v["open_ms"],)).fetchone()
            if previous is None:db.execute("INSERT INTO price_bars VALUES(?,?,?)",(v["open_ms"],bar,h))
            elif previous[0]!=bar:db.execute("INSERT OR IGNORE INTO bar_conflicts VALUES(?,?)",(v["open_ms"],h))
    return 1
def evaluate_pending(db,now):
    if type(now) is not int or now<=0:raise ValueError("clock")
    pending=db.execute("SELECT commitment,prepared_ms,packet,price,footprint,cot,rule FROM observations ORDER BY prepared_ms LIMIT ?",(MAX_OBS+1,)).fetchall()
    if len(pending)>MAX_OBS:raise ValueError("pilot_capacity")
    saved=missing=terminal=0
    for h,t,blob,p,f,c,r in pending:
        pkt=json.loads(blob)
        if digest(blob)!=h or pkt["prepared_ms"]!=t or pkt["prospective_admitted"] is not False or pkt["source_sha256"]!={"price":digest(p),"footprint":digest(f),"cot":digest(c)} or pkt["rule_sha256"]!=digest(r):raise ValueError("custody")
        entry=(t//M15+1)*M15
        if pkt["entry_not_before_ms"]!=entry:raise ValueError("entry")
        for horizon in HORIZONS:
            end=entry+horizon*3600000
            if end>now:continue
            if db.execute("SELECT 1 FROM terminal_missing WHERE commitment=? AND hours=?",(h,horizon)).fetchone():continue
            if db.execute("SELECT COUNT(*) FROM outcomes WHERE commitment=? AND hours=?",(h,horizon)).fetchone()[0]==3:continue
            rows=db.execute("""SELECT b.bar,b.source_hash FROM price_bars b WHERE b.open_ms>=? AND b.open_ms<? AND NOT EXISTS(SELECT 1 FROM bar_conflicts x WHERE x.open_ms=b.open_ms) ORDER BY b.open_ms""",(entry,end)).fetchall()
            bars=[json.loads(x[0]) for x in rows]
            if len(bars)!=horizon*4:
                missing+=1
                if now>=end+GRACE:
                    with db:db.execute("INSERT INTO terminal_missing VALUES(?,?,?)",(h,horizon,now))
                    terminal+=1
                continue
            evidence=canonical({"bars":bars,"source_hashes":[x[1] for x in rows]})
            with db:
                for cost in COSTS:
                    if db.execute("SELECT 1 FROM outcomes WHERE commitment=? AND hours=? AND cost=?",(h,horizon,cost)).fetchone():continue
                    result=evaluate({"symbol":"EURUSD","mode":"TEST_DESCRIPTIVE_ONLY","frozen_ms":t,"sides":pkt["sides"]},bars,now,cost,horizon)
                    if result["status"]!="RETROSPECTIVE_ONLY":raise ValueError("evaluator")
                    db.execute("INSERT INTO outcomes VALUES(?,?,?,?,?,?)",(h,horizon,cost,now,evidence,canonical(result)))
                    saved+=1
    return {"saved_cost_horizon_rows":saved,"pending_missing_horizons":missing,"new_terminal_missing":terminal,"prospective_admitted":False}
def totals(db):
    invalidated=db.execute("""SELECT COUNT(*) FROM outcomes x JOIN observations o ON x.commitment=o.commitment WHERE EXISTS (SELECT 1 FROM bar_conflicts c WHERE c.open_ms>=(o.prepared_ms/900000+1)*900000 AND c.open_ms<(o.prepared_ms/900000+1)*900000+x.hours*3600000)""").fetchone()[0]
    return {**summary(db),"invalidated_outcome_rows":invalidated,"price_snapshots":db.execute("SELECT COUNT(*) FROM price_snapshots").fetchone()[0],"historical_m15":db.execute("SELECT COUNT(*) FROM price_bars").fetchone()[0],"conflicted_bars":db.execute("SELECT COUNT(*) FROM bar_conflicts").fetchone()[0],"terminal_missing_horizons":db.execute("SELECT COUNT(*) FROM terminal_missing").fetchone()[0]}
