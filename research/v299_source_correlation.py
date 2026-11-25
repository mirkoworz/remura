"""REMURA V29.9 LAB — 25/11/2026 Europe/Rome.
Descriptive source join only. No I/O, trade side, score or prospective admission.
Input records from V29.6 custody; COT from public B V22.3 handoff;
price snapshot from cTrader. Caller must supply actual snapshot capture times.
"""
from datetime import datetime,timezone
from decimal import Decimal
import json,math
from v294_footprint_cvd import derive

LEVELS=("day1","day2","day3","previous_day","week","current_month","previous_month")
M15=900000

def ms(t):
    d=datetime.fromisoformat(t.replace("Z","+00:00"))
    if d.tzinfo is None:
        raise ValueError("naive_timestamp")
    return int(d.timestamp()*1000)

def number(x):
    return type(x) in (int,float) and math.isfinite(x)

def cot_context(doc,asof):
    if doc.get("schema")!="remura-b-v223-public-export-only-v1":
        raise ValueError("cot_schema")
    published_read=ms(doc["publicReadAtUtc"])
    if published_read>asof:
        return {"status":"NOT_AVAILABLE_ASOF"}
    d=doc["dashboard"]
    matches=[x for x in d["factors"] if x["currency"]=="EUR" and x["cftcContractCode"]=="099741"]
    if len(matches)!=1:
        raise ValueError("cot_identity")
    f=matches[0]
    v=f["weeklyAssetManagerChangePp"]
    if not number(v):
        raise ValueError("cot_numeric")
    return {"status":"PUBLIC_DESCRIPTIVE_ONLY","report_date":f["reportDate"],
            "public_read_ms":published_read,"asset_manager_weekly_change_pp":v,
            "private_first_seen_verified":False}

def price_context(doc,updated_at,captured_ms,asof):
    if doc.get("provider")!="ctrader":
        raise ValueError("price_provider")
    if type(captured_ms) is not int or not 0<captured_ms<=asof:
        return {"status":"NOT_AVAILABLE_ASOF"}
    updated=ms(updated_at)
    if not 0<updated<=captured_ms:
        raise ValueError("price_clock")
    if asof-updated>1800000:
        return {"status":"STALE"}
    rows=doc.get("timeframes",{}).get("M15")
    if type(rows) is not list:
        raise ValueError("price_rows")
    last=None
    prev=None
    for row in rows:
        t=ms(row["t"])
        o,h,l,c=(row[k] for k in ("o","h","l","c"))
        if (t%M15 or (prev is not None and t<=prev) or
            not all(number(v) and v>0 for v in (o,h,l,c)) or
            h<max(o,l,c) or l>min(o,h,c)):
            raise ValueError("price_bar")
        prev=t
        if t+M15<=min(asof,captured_ms,updated):
            last=(t,c)
    if last is None:
        return {"status":"NO_CLOSED_BAR"}
    if asof-(last[0]+M15)>1800000:
        return {"status":"STALE_BAR"}
    return {"status":"DESCRIPTIVE_ONLY","bar_close_ms":last[0]+M15,"close":last[1]}

def observe(records,cot,price,updated_at,captured_ms,asof):
    if type(asof) is not int or asof<=0:
        raise ValueError("asof")
    features=derive(records,asof)
    out={"mode":"TEST_DESCRIPTIVE_ONLY","prospective_admitted":False,
         "asof_ms":asof,"symbol":"EURUSD","cot":cot_context(cot,asof),
         "price":price_context(price,updated_at,captured_ms,asof),
         "footprint":{"status":"NO_VALID_FEATURE"},"levels":{},
         "sentiment":{"status":"NOT_JOINED"}}
    if not features:
        return out
    f=features[-1]
    candidates=[r for r in records if r["metadata"]["bar_close_ms"]==f["bar_close_ms"] and r["metadata"]["received_at_ms"]<=asof]
    if not candidates:
        raise ValueError("source_missing")
    s=json.loads(candidates[0]["original"])["snapshot"]
    if asof-f["bar_close_ms"]>600000:
        out["footprint"]={"status":"STALE"}
        return out
    out["footprint"]={"status":"DESCRIPTIVE_ONLY",**f}
    for k in LEVELS:
        v=s.get("levels",{}).get(k)
        t=s.get("level_origin_ms",{}).get(k)
        if number(v) and v>0 and type(t) is int and 0<t<=f["bar_close_ms"]:
            out["levels"][k]={"value":v,"origin_ms":t,
                              "known_before_current_bar":t<=f["bar_close_ms"]-300000}
    return out
