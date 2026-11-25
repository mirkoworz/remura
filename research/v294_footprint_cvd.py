"""REMURA V29.4 LAB — Footprint cumulative delta, 25/11/2026.
Pure observation-only feature, not native M1 CVD or exchange order flow.
Input: custody records available as of a fixed timestamp; no network or writes.
"""
import json
import hashlib
from decimal import Decimal
from datetime import datetime, timezone

M5=300000
SOURCE="TV_FOOTPRINT_CLASSIFIED_FX_EURUSD_M5"
VERSION="0.9.1-cvd-lab"

def _num(v):
    return type(v) in (int,Decimal) and Decimal(v).is_finite()

def derive(records, asof_ms):
    if type(asof_ms) is not int or asof_ms<=0:
        raise ValueError("asof")
    by_close={}
    for row in records:
        m=row["metadata"]
        c,r=m["bar_close_ms"],m["received_at_ms"]
        if type(c) is not int or type(r) is not int or c<=0 or c%M5 or r<c:
            raise ValueError("clock")
        if r>asof_ms:
            continue
        if (m["symbol"],m["timeframe"],m["version"],m["is_timely"])!=("FX:EURUSD","5",VERSION,0):
            raise ValueError("scope")
        if c in by_close:
            if by_close[c]!=row:
                raise ValueError("conflict")
            continue
        by_close[c]=row
    result=[]
    prev=None
    day=None
    total=Decimal(0)
    count=0
    config=None
    for c,row in sorted(by_close.items()):
        m=row["metadata"]
        if type(row["original"]) is not bytes or hashlib.sha256(row["original"]).hexdigest()!=row["sha256"]:
            raise ValueError("custody_digest")
        p=json.loads(row["original"],parse_float=Decimal)
        if p.get("schema")!="remura.tv.flow.cvd.preview.v1":
            raise ValueError("schema")
        s=p["snapshot"]
        if (s.get("symbol"),s.get("timeframe"),s.get("version"),s.get("bar_close_ms"))!=("FX:EURUSD","5",VERSION,c):
            raise ValueError("identity")
        f=s.get("footprint",{})
        d=f.get("delta")
        buy,sell=f.get("buy"),f.get("sell")
        cfg=p["configuration"]
        if type(cfg) is not dict:
            raise ValueError("configuration")
        thisday=datetime.fromtimestamp((c-M5)/1000,timezone.utc).date()
        valid=(s.get("confirmed") is True and f.get("available") is True
               and _num(d) and _num(buy) and _num(sell)
               and buy>=0 and sell>=0 and abs(Decimal(buy)-Decimal(sell)-Decimal(d))<=Decimal("0.000001"))
        if prev is None or c-prev!=M5 or day!=thisday or cfg!=config:
            total=Decimal(0)
            count=0
        if not valid:
            total=Decimal(0)
            count=0
            prev=None
            continue
        total+=Decimal(d)
        count+=1
        prev,day,config=c,thisday,cfg
        result.append({"source":SOURCE,"bar_close_ms":c,"observed_asof_ms":asof_ms,
                       "receipt_ms":m["received_at_ms"],"segment_bars":count,
                       "segment_cvd":str(total),"utc_day":str(day),
                       "observation_only":True,"prospective_admitted":False})
    return result
