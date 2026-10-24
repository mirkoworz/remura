#!/usr/bin/env python3
"""REMURA private Squalincome observer (v1.33).

Read-only analysis of verified cTrader OHLC and locally stored official CFTC
futures. A SQLite baseline is required before any transition can be recorded.
No browser, Google, retail, trades, API tokens, webhooks or notifications.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sqlite3

from price_feed import MARKETS, parse_time, utcnow
from price_store import connect, latest, audit_market

FX_CODES={"EUR":"099741","GBP":"096742","JPY":"097741","AUD":"232741",
          "CAD":"090741","CHF":"092741","NZD":"112741"}
OTHER={
    "XAUUSD":("disagg","088691"),"XAGUSD":("disagg","084691"),
    "USOIL":("disagg","067651"),
    "US500":("tff","13874A"),"NAS100":("tff","209742"),"US30":("tff","124603")
}
DURATIONS={"M15":900,"H1":3600,"H4":14400}
MIN_COT_DELTA=.45
EVENT_KEEP_DAYS=90
MIN_FRAMES=55


def monitored_symbols():
    """DXY is macro context; GER30, VIX and UKOIL lack direct COT proxies."""
    return tuple(sorted(sym for sym in MARKETS if sym in OTHER or
           (len(sym)==6 and sym.isalpha() and
            sym[:3] in FX_CODES | {"USD":None} and sym[3:] in FX_CODES | {"USD":None})))


def ensure_tables(db):
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_observations(
        symbol TEXT PRIMARY KEY, state TEXT NOT NULL, side INTEGER NOT NULL,
        report_date TEXT NOT NULL, price_time TEXT NOT NULL,
        price_state TEXT NOT NULL, observed_at TEXT NOT NULL)""")
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_events(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL, event_type TEXT NOT NULL, side INTEGER NOT NULL,
        report_date TEXT NOT NULL, price_time TEXT NOT NULL, observed_at TEXT NOT NULL,
        detail TEXT NOT NULL,
        UNIQUE(symbol,event_type,report_date,price_time))""")
    db.commit()


def spec_series(db, dataset, code):
    sql=("SELECT report_date,oi,first_long,first_short,second_long,second_short "
         "FROM cot_reports WHERE dataset=? AND code=? ORDER BY report_date DESC LIMIT 8")
    records=db.execute(sql,(dataset,code)).fetchall()
    values={}
    for date,oi,a_long,a_short,b_long,b_short in reversed(records):
        if not oi or oi<=0:continue
        a=100*(a_long-a_short)/oi
        b=100*(b_long-b_short)/oi
        if all(math.isfinite(x) and abs(x)<=200 for x in (a,b)):
            values[date]=(a,b)
    return values


def cot_series(db, symbol):
    if symbol in OTHER:
        dataset,code=OTHER[symbol]
        records=spec_series(db,dataset,code)
        return [(date,*value) for date,value in sorted(records.items())]
    base,quote=symbol[:3],symbol[3:]
    left=spec_series(db,"tff",FX_CODES[base]) if base!="USD" else None
    right=spec_series(db,"tff",FX_CODES[quote]) if quote!="USD" else None
    if left is None and right is None:return []
    if left is not None and right is not None:
        dates=sorted(left.keys() & right.keys())
        return [(d,left[d][0]-right[d][0],left[d][1]-right[d][1]) for d in dates]
    rows=left if left is not None else right
    sign=1 if left is not None else -1
    return [(d,sign*row[0],sign*row[1]) for d,row in sorted(rows.items())]


def cot_view(series, symbol, now):
    if len(series)<2:return None
    date,a,b=series[-1]
    age=(now.date()-dt.date.fromisoformat(date)).days
    if age<0 or age>14:return None
    is_disagg=symbol in OTHER and OTHER[symbol][0]=="disagg"
    specidx=1 if is_disagg else 2
    secidx=2 if is_disagg else 1
    first,previous=series[-1],series[-2]
    # Do not compare skipped weeks or incomparable report dates.
    span=(dt.date.fromisoformat(first[0])-dt.date.fromisoformat(previous[0])).days
    if span<6 or span>10:return None
    delta=first[specidx]-previous[specidx]
    secondary=first[secidx]-previous[secidx]
    side=1 if delta>MIN_COT_DELTA else -1 if delta < -MIN_COT_DELTA else 0
    # Disaggregated Producer/Merchant commonly hedge; only TFF secondary
    # Asset Manager opposing Leveraged Funds means mixed institutional groups.
    opposed=(not is_disagg) and bool(side) and (secondary>MIN_COT_DELTA if side<0 else secondary < -MIN_COT_DELTA)
    if not side or opposed:return None
    sustained=False
    if len(series)>=5:
        direction4=first[specidx]-series[-5][specidx]
        recent=[series[-i][specidx]-series[-i-1][specidx] for i in (1,2,3)]
        rising=sum(x>MIN_COT_DELTA for x in recent)
        falling=sum(x< -MIN_COT_DELTA for x in recent)
        sustained=direction4*side>=1.2 and (rising if side>0 else falling)>=2
    return {"side":side,"report":date,"weekly":round(delta,4),"sustained":sustained}


def ema(series,length):
    if len(series)<length:return None
    value=sum(series[:length])/length
    mult=2/(length+1)
    for close in series[length:]:value=close*mult+value*(1-mult)
    return value


def frame_direction(bars, duration, now):
    if len(bars)<MIN_FRAMES:return None
    times=[parse_time(row["t"]) for row in bars]
    if now<times[-1]+dt.timedelta(seconds=duration)-dt.timedelta(minutes=5):
        return None
    age=(now-times[-1]-dt.timedelta(seconds=duration)).total_seconds()
    if age < -300 or age > (5*3600 if duration==14400 else 2*3600 if duration==3600 else 3*3600):
        return None
    closes=[row["c"] for row in bars]
    e20,e50=ema(closes,20),ema(closes,50)
    if e20 is None or e50 is None:return None
    side=1 if closes[-1]>e20>e50 else -1 if closes[-1]<e20<e50 else 0
    highs=[b["h"] for b in bars[-22:-2]]
    lows=[b["l"] for b in bars[-22:-2]]
    breakout=0
    if bars[-2]["c"]>max(highs) and bars[-1]["c"]>max(highs):breakout=1
    elif bars[-2]["c"]<min(lows) and bars[-1]["c"]<min(lows):breakout=-1
    return {"side":side,"breakout":breakout,"close_time":(times[-1]+dt.timedelta(seconds=duration)).isoformat()}


def price_view(doc, now):
    if not isinstance(doc,dict):return None
    quality=audit_market(doc,now)
    if quality["integrity"]!="verified" or quality["freshness"]!="recent" or not quality["ready"]:
        return None
    frames={}
    for key,seconds in DURATIONS.items():
        record=frame_direction(doc["timeframes"][key],seconds,now)
        if record is None:return None
        frames[key]=record
    h4,h1,m15=(frames[key] for key in ("H4","H1","M15"))
    side=h4["side"] if h4["side"] and h4["side"]==h1["side"] else 0
    if not side:return None
    breakout=(h4["breakout"]==side or h1["breakout"]==side)
    full=breakout and m15["side"]==side and m15["breakout"]==side
    partial=breakout and m15["side"]==side
    state="confirmed" if full else "partial" if partial else "watch"
    return {"side":side,"state":state,"last_m15":m15["close_time"]}


def classify(cot, price):
    if cot is None or price is None:return None
    return {"state":"aligned" if cot["side"]==price["side"] else "divergent",
            "side":cot["side"],"report_date":cot["report"],
            "price_time":price["last_m15"],"price_state":price["state"]}


def transition(previous, current):
    """Only a new verified source observation can create an event."""
    if previous is None or current is None:return None
    if current["report_date"] < previous["report_date"]:return None
    if current["price_time"] < previous["price_time"]:return None
    if current["report_date"] == previous["report_date"] and current["price_time"]==previous["price_time"]:
        return None
    if previous["state"]=="divergent" and current["state"]=="aligned" and current["price_state"]=="confirmed":
        return "new_convergence"
    if previous["state"]=="aligned" and current["state"]=="divergent" and current["price_state"]=="confirmed":
        return "new_divergence"
    if previous["state"]=="aligned" and previous["price_state"]!="confirmed" and \
       current["state"]=="aligned" and current["price_state"]=="confirmed":
        return "confirmation_strengthened"
    return None


def scan_once(db_path,now=None):
    now=now or utcnow()
    # Safe to run even when the upstream collector is not ready: no invented report.
    db=connect(db_path)
    ensure_tables(db)
    from cot_monitor import ensure_table as ensure_cot_table
    ensure_cot_table(db)
    examined=baselines=events=0
    try:
        for symbol in monitored_symbols():
            try:
                cot=cot_view(cot_series(db,symbol),symbol,now)
                document=latest(db,symbol)
                price=price_view(document,now) if document else None
                current=classify(cot,price)
                if current is None:continue
                examined+=1
                row=db.execute("SELECT state,side,report_date,price_time,price_state,observed_at "
                               "FROM squalincome_observations WHERE symbol=?",(symbol,)).fetchone()
                prior=dict(zip(("state","side","report_date","price_time","price_state","observed_at"),row)) if row else None
                if prior and (current["report_date"]<prior["report_date"] or
                              current["price_time"]<prior["price_time"]):
                    continue
                change=transition(prior,current)
                stamp=now.isoformat()
                with db:
                    if change:
                        cur=db.execute("INSERT OR IGNORE INTO squalincome_events"
                           "(symbol,event_type,side,report_date,price_time,observed_at,detail) VALUES(?,?,?,?,?,?,?)",
                           (symbol,change,current["side"],current["report_date"],current["price_time"],stamp,
                            "COT futures e struttura OHLC verificata; osservazione, non ordine o previsione."))
                        if cur.rowcount:events+=1
                    if prior is None:baselines+=1
                    db.execute("INSERT INTO squalincome_observations"
                        "(symbol,state,side,report_date,price_time,price_state,observed_at)"
                        " VALUES(?,?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
                        "state=excluded.state,side=excluded.side,report_date=excluded.report_date,"
                        "price_time=excluded.price_time,price_state=excluded.price_state,"
                        "observed_at=excluded.observed_at",
                        (symbol,current["state"],current["side"],current["report_date"],current["price_time"],
                         current["price_state"],stamp))
            except (ValueError,TypeError,KeyError,sqlite3.Error):
                # One malformed market cannot block the remaining private markets.
                continue
        with db:
            db.execute("DELETE FROM squalincome_events WHERE observed_at < ?",
                ((now-dt.timedelta(days=EVENT_KEEP_DAYS)).isoformat(),))
        return {"examined":examined,"baselines":baselines,"newEvents":events}
    finally:db.close()


def status(db_path,enabled=False,now=None):
    now=now or utcnow()
    db=connect(db_path)
    try:
        ensure_tables(db)
        baseline=db.execute("SELECT count(*) FROM squalincome_observations").fetchone()[0]
        events=db.execute("SELECT symbol,event_type,side,report_date,price_time,observed_at,detail "
            "FROM squalincome_events ORDER BY id DESC LIMIT 20").fetchall()
        return {"schema":"remura-squalincome-monitor-v1","enabled":bool(enabled),
                "mode":"observation_only","notificationsEnabled":False,
                "trackedMarkets":len(monitored_symbols()),"baselines":baseline,
                "lastEvents":[dict(zip(("symbol","eventType","side","reportDate","priceTime","observedAt","detail"),r))
                              for r in events],
                "serverTime":now.isoformat()}
    finally:db.close()
