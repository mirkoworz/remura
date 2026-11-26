"""REMURA V30.7 LAB, 26 November 2026.
Local scientific queue. No external requests, no orders, no scheduler installation.
Only locally prepared, NOT independently witnessed observations.
"""
import hashlib,json,sqlite3
from v299_source_correlation import ms
from v308_observation_assemble import assemble
from v304_local_freeze import canonical
from v300_paired_outcomes import evaluate
M15=900000
COSTS=("0","1","2")
HORIZONS=(1,4,24)
def digest(b):return hashlib.sha256(b).hexdigest()
def initialize(db):
    if db.in_transaction:raise ValueError("transaction")
    names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    if names-{"observations","outcomes","price_snapshots","price_bars","bar_conflicts","terminal_missing"}:raise ValueError("dedicated_db")
    with db:
        db.execute("""CREATE TABLE IF NOT EXISTS observations(
         commitment TEXT PRIMARY KEY, price_close_ms INTEGER NOT NULL UNIQUE,
         prepared_ms INTEGER NOT NULL, packet BLOB NOT NULL,
         price BLOB NOT NULL, footprint BLOB NOT NULL, cot BLOB NOT NULL,
         rule BLOB NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS outcomes(
         commitment TEXT NOT NULL, hours INTEGER NOT NULL, cost TEXT NOT NULL,
         observed_ms INTEGER NOT NULL, price BLOB NOT NULL, result BLOB NOT NULL,
         PRIMARY KEY(commitment,hours,cost), FOREIGN KEY(commitment) REFERENCES observations(commitment))""")
        for table in ("observations","outcomes"):
            for action in ("UPDATE","DELETE"):
                db.execute("CREATE TRIGGER IF NOT EXISTS "+table+"_no_"+action.lower()+" BEFORE "+action+" ON "+table+" BEGIN SELECT RAISE(ABORT,'append_only'); END")
def price_view(raw,captured):
    symbol,source,broker,updated,payload=json.loads(raw)
    p=json.loads(payload)
    if symbol!="EURUSD" or source!="ctrader" or not broker or p.get("providerSymbol")!=broker or p.get("provider")!="ctrader":raise ValueError("identity")
    updated=ms(updated)
    if not 0<updated<=captured:raise ValueError("price_clock")
    rows=p["timeframes"]["M15"]
    if not isinstance(rows,list) or len(rows)>10000:raise ValueError("bars")
    bars=[];prev=None
    for v in rows:
        t=ms(v["t"])
        if t%M15 or (prev is not None and t<=prev):raise ValueError("bar_order")
        prev=t
        if t+M15<=updated:
            bars.append({"open_ms":t,**{k:v[k] for k in ("o","h","l","c")}})
    return updated,bars
def capture_tick(db,raw,captured,clock,rule,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    if db.in_transaction:raise ValueError("transaction")
    now=clock()
    if type(captured) is not int or type(now) is not int or not 0<=now-captured<=30000:raise ValueError("capture")
    if set(raw)!={"price","footprint","cot"} or any(type(v) is not bytes or not 0<len(v)<=4000000 for v in raw.values()):raise ValueError("sources")
    updated,bars=price_view(raw["price"],captured)
    if not bars or now-updated>1800000 or now-bars[-1]["open_ms"]-M15>1800000:
        return {"status":"WAIT_FRESH_PRICE","prospective_admitted":False}
    close=bars[-1]["open_ms"]+M15
    if db.execute("SELECT 1 FROM observations WHERE price_close_ms=?",(close,)).fetchone():
        return {"status":"ALREADY_OBSERVED_BAR","prospective_admitted":False}
    result=assemble(raw,captured,clock,rule,enabled=True)
    if result["status"]!="PREPARED_ONLY":return {"status":"INELIGIBLE","prospective_admitted":False}
    packet=result["packet"];blob=canonical(packet);h=digest(blob)
    if h!=result["commitment"] or packet["source_sha256"]!={k:digest(v) for k,v in raw.items()} or packet["rule_sha256"]!=digest(rule):raise ValueError("binding")
    with db:
        db.execute("INSERT INTO observations VALUES(?,?,?,?,?,?,?,?)",(h,close,packet["prepared_ms"],blob,raw["price"],raw["footprint"],raw["cot"],rule))
    return {"status":"LOCAL_RECORDED_UNWITNESSED","prospective_admitted":False}
def summary(db):
    return {"local_observations":db.execute("SELECT COUNT(*) FROM observations").fetchone()[0],
            "outcome_rows":db.execute("SELECT COUNT(*) FROM outcomes").fetchone()[0],
            "certified_observations":0,"prospective_admitted":False}
