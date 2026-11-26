"""REMURA V30.2 LAB — 26/11/2026 Europe/Rome.
Read-only descriptive adapter for EURUSD, never a signal or prospective freeze.
Caller provides already-open read-only connections and pinned public COT.
No network, no CLI, no output of raw source records.
"""
import json,time
from v299_source_correlation import observe

def describe(custody,prices,cot,clock=lambda:int(time.time()*1000)):
    for db in (custody,prices):
        if db.execute("PRAGMA query_only").fetchone()!=(1,):
            raise ValueError("read_only_required")
    row=prices.execute("SELECT symbol,source,broker_symbol,updated_at,payload FROM prices WHERE symbol=?",("EURUSD",)).fetchone()
    captured=clock()
    if row is None: return {"status":"PRICE_MISSING","prospective_admitted":False}
    symbol,source,broker,updated,payload=row
    p=json.loads(payload)
    if symbol!="EURUSD" or source!="ctrader" or not broker or p.get("providerSymbol")!=broker:
        raise ValueError("price_identity")
    rows=custody.execute("""SELECT metadata,original,sha256 FROM tv_test_custody
      WHERE CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) BETWEEN ? AND ?
      ORDER BY CAST(json_extract(metadata,'$.bar_close_ms') AS INTEGER) LIMIT 289""",
      (captured-86400000,captured)).fetchall()
    if len(rows)>288:raise ValueError("window_capacity")
    records=[{"metadata":json.loads(m),"original":v,"sha256":h} for m,v,h in rows]
    asof=clock()
    if asof<captured:raise ValueError("clock")
    report=observe(records,cot,p,updated,captured,asof,symbol=symbol)
    return {"status":"DESCRIPTIVE_ONLY","footprint_status":report["footprint"]["status"],
            "footprint_segment_bars":report["footprint"].get("segment_bars",0),
            "price_status":report["price"]["status"],"cot_status":report["cot"]["status"],
            "available_level_count":len(report["levels"]),"sentiment_status":"NOT_JOINED",
            "prospective_admitted":False}
