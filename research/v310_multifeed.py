"""V31.0 LAB — 26/11/2026. Pure feed-normalization and comparison.
No provider access, persistence, execution or prospective admission.
"""
from decimal import Decimal
import hashlib,json
M5=300000
M15=900000
TV="TRADINGVIEW:FX:EURUSD"
CT="CTRADER:EURUSD"
def num(x):
    if type(x) not in (int,float,Decimal,str):raise ValueError("number")
    d=Decimal(str(x))
    if not d.is_finite() or d<=0:raise ValueError("price")
    return d
def ohlc(o,h,l,c):
    o,h,l,c=map(num,(o,h,l,c))
    if h<max(o,l,c) or l>min(o,h,c):raise ValueError("ohlc")
    return o,h,l,c
def tv_bar(meta,raw,digest,asof):
    if type(asof) is not int or asof<=0:raise ValueError("asof")
    if type(raw) is not bytes or hashlib.sha256(raw).hexdigest()!=digest:raise ValueError("digest")
    p=json.loads(raw,parse_float=Decimal)
    if p.get("schema")!="remura.tv.flow.cvd.preview.v1":raise ValueError("envelope")
    s=p["snapshot"]
    if s.get("schema")!="remura.tv.flow.cvd.snapshot.preview.v1":raise ValueError("snapshot")
    if tuple(meta.get(k) for k in ("symbol","timeframe","version"))!=("FX:EURUSD","5","0.9.1-cvd-lab"):raise ValueError("scope")
    if tuple(s.get(k) for k in ("symbol","timeframe","version"))!=("FX:EURUSD","5","0.9.1-cvd-lab") or s.get("feed")!="FX":raise ValueError("identity")
    t,c,r=s["bar_open_ms"],s["bar_close_ms"],meta["received_at_ms"]
    if any(type(x) is not int for x in (t,c,r)) or t<=0 or t%M5 or c!=t+M5 or c!=meta["bar_close_ms"] or not c<=r<=asof:raise ValueError("clock")
    if s.get("confirmed") is not True or s.get("realtime") is not True or s.get("quality",{}).get("bar_closed") is not True:raise ValueError("confirmation")
    v=s["ohlc"]
    if any(type(v[k]) not in (int,Decimal) for k in ("open","high","low","close")):raise ValueError("numeric_json")
    o,h,l,z=ohlc(*(v[k] for k in ("open","high","low","close")))
    return {"source":TV,"open_ms":t,"close_ms":c,"available_ms":r,"o":o,"h":h,"l":l,"c":z,"evidence":(digest,)}
def m15(bars,asof):
    groups={};seen=set()
    for b in bars:
        t=b["open_ms"]
        if b["source"]!=TV or type(t) is not int or t%M5 or b["close_ms"]!=t+M5 or not b["close_ms"]<=b["available_ms"]<=asof:raise ValueError("scope_clock")
        if t in seen:raise ValueError("duplicate")
        seen.add(t);groups.setdefault(t//M15*M15,[]).append(b)
    result=[]
    for t,group in sorted(groups.items()):
        g=sorted(group,key=lambda b:b["open_ms"])
        if [b["open_ms"] for b in g]!=[t,t+M5,t+2*M5]:continue
        result.append({"source":TV,"open_ms":t,"close_ms":t+M15,
            "available_ms":max(b["available_ms"] for b in g),"o":g[0]["o"],
            "h":max(b["h"] for b in g),"l":min(b["l"] for b in g),"c":g[-1]["c"],
            "evidence":tuple(x for b in g for x in b["evidence"])})
    return result
def compare(tv,ct,asof):
    """Same UTC interval; compare sources, never splice or substitute."""
    def index(rows,source):
        d={}
        for b in rows:
            t=b["open_ms"]
            if b["source"]!=source or type(t) is not int or t%M15 or b["close_ms"]!=t+M15 or not b["close_ms"]<=b["available_ms"]<=asof or t in d:raise ValueError("comparison_scope")
            d[t]=ohlc(*(b[k] for k in ("o","h","l","c")))
        return d
    a,b=index(tv,TV),index(ct,CT)
    matched=sorted(a.keys()&b.keys())
    diffs=[abs(x-y)*10000 for t in matched for x,y in zip(a[t],b[t])]
    closes=[abs(a[t][3]-b[t][3])*10000 for t in matched]
    return {"matched_m15":len(matched),"tv_only":len(a.keys()-b.keys()),"ct_only":len(b.keys()-a.keys()),
            "max_ohlc_diff_pips":str(max(diffs)) if diffs else None,
            "mean_close_diff_pips":str(sum(closes)/len(closes)) if closes else None,
            "max_close_diff_pips":str(max(closes)) if closes else None,"interchangeable":False,"prospective_admitted":False}
