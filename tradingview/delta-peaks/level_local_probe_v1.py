# REMURA v0.8.108 LAB — 16/11/2026
"""Untrusted local Pine log structural diagnostic; never an E wire or receipt."""
import json, math, re
from hashlib import sha256
from decimal import Decimal
SCHEMA="remura.tv.level.local.probe.v1"
FIELDS=set("schema version mode symbol feed ticker chart_type timezone session timeframe calendar product_status contract snapshot_open_ms snapshot_close_ms sender_clock_ms receive_clock_ms history_complete method_er configuration levels".split())
CF=set("lower_tf lookback multiplier max_efficiency min_peak_gap daily_min_effort daily_anchor fp_ticks fp_imbalance_pct fp_value_area_pct atr_length delta_library price_decimal_places_max".split())
LF=set("period rank price peak_origin_close_ms period_start_ms period_end_ms boundary_observed method".split())
ORDER=[("DAY",1),("DAY",2),("DAY",3),("WEEK",1),("CURRENT_MONTH",1),("PREVIOUS_OBSERVED_MONTH",1)]
def need(ok):
    if not ok:raise ValueError("local_level_probe_invalid")
def clock(v, *, whole_second=True):
    need(type(v) is int and 0<v<4102444800000 and (not whole_second or v%1000==0))
    return v
def unique(items):
    result={}
    for k,v in items:
        need(k not in result);result[k]=v
    return result
def parse(raw):
    need(type(raw) is str and len(raw.encode("utf-8"))<=12000)
    p=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda x: (_ for _ in ()).throw(ValueError("nonfinite")))
    need(type(p) is dict and set(p)==FIELDS)
    need(p["schema"]==SCHEMA and p["version"]=="0.9.2-level-lab")
    need(p["mode"] in ("REALTIME_LOCAL_LOG","HISTORICAL_RECONSTRUCTION"))
    need((p["symbol"],p["feed"],p["ticker"],p["timeframe"])==("FX:EURUSD","FX","EURUSD","5"))
    need(p["calendar"]=="TRADINGVIEW_CHART_PERIOD_V1" and p["product_status"]=="UNATTESTED"
         and p["contract"] is None and p["receive_clock_ms"] is None and p["history_complete"] is False
         and p["method_er"]=="SIGNED_BODY_ATR_OVER_RELATIVE_ABS_DELTA_V1")
    need(all(type(p[k]) is str and 0<len(p[k])<=100 for k in ("chart_type","timezone","session")))
    op,cl=clock(p["snapshot_open_ms"]),clock(p["snapshot_close_ms"])
    # Pine timenow is an epoch millisecond clock, not a bar timestamp.
    clock(p["sender_clock_ms"],whole_second=False)
    need(0<cl-op<=300000 and cl<=p["sender_clock_ms"])
    c=p["configuration"]
    need(type(c) is dict and set(c)==CF)
    need(c["lower_tf"]=="1" and c["daily_anchor"] in ("HL2","POC FOOTPRINT")
        and c["delta_library"]=="TradingView/ta/14" and c["price_decimal_places_max"]==10
        and c["atr_length"]==14 and c["fp_value_area_pct"]==70)
    for k in ("lookback","min_peak_gap","fp_ticks","fp_value_area_pct","atr_length","price_decimal_places_max"):
        need(type(c[k]) is int)
    need(c["lookback"]>=5 and 0<=c["min_peak_gap"]<=100 and c["fp_ticks"]>=1)
    for k in ("multiplier","max_efficiency","daily_min_effort","fp_imbalance_pct"):
        need(type(c[k]) in (int,float) and math.isfinite(c[k]))
    need(c["multiplier"]>=1 and -1<=c["max_efficiency"]<=1 and c["daily_min_effort"]>=0 and c["fp_imbalance_pct"]>=100)
    levels=p["levels"];need(type(levels) is list and len(levels)==6)
    present=0
    for i,(row,(period,rank)) in enumerate(zip(levels,ORDER)):
        need(type(row) is dict and set(row)==LF and row["period"]==period and type(row["rank"]) is int and row["rank"]==rank)
        method=("DAY_TOP3_ABS_DELTA_HL2" if c["daily_anchor"]=="HL2" else "DAY_TOP3_ABS_DELTA_FP_POC") if period=="DAY" else "PERIOD_MAX_ABS_DELTA_HL2"
        need(row["method"]==method and type(row["boundary_observed"]) is bool)
        start,end=row["period_start_ms"],row["period_end_ms"]
        origin,price=row["peak_origin_close_ms"],row["price"]
        if start is None or end is None:
            need(period=="PREVIOUS_OBSERVED_MONTH" and start is None and end is None and origin is None and price is None and not row["boundary_observed"])
            continue
        start,end=clock(start),clock(end);need(start<end)
        if period=="PREVIOUS_OBSERVED_MONTH":
            need(end<=cl and start<levels[4]["period_start_ms"])
        else:need(start<=op<cl<=end)
        if period=="DAY" and i>0:
            need(all(row[k]==levels[0][k] for k in ("period_start_ms","period_end_ms","boundary_observed")))
        need((origin is None)==(price is None))
        if origin is not None:
            need(start<clock(origin)<=min(end,cl))
            need(type(price) is str and re.fullmatch(r"[0-9]{1,8}(?:\.[0-9]{1,10})?",price) and Decimal(price)>0)
            if period=="DAY" and i>0:need(levels[i-1]["price"] is not None)
            present+=1
    fingerprint=sha256(json.dumps(c,sort_keys=True,separators=(",",":"),allow_nan=False).encode()).hexdigest()
    return {"schema":"remura.tv.level.local.probe.diagnostic.v1","mode":p["mode"],
        "symbol":p["symbol"],"configuration_digest":fingerprint,"present_levels":present,
        "missing_levels":6-present,"source_attested":False,"receipt_authenticated":False,
        "calendar_equivalence_attested":False,"comparison_admitted":False,"operational_signal":False}
