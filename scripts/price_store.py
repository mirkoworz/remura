#!/usr/bin/env python3
"""Private REMURA OHLC storage. No web framework or third-party requirements.

SQLite stores only market candles and operational state, never account credentials.
The database is a local PRIVATE file. Each update is atomic.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import os
from pathlib import Path
import sqlite3
from zoneinfo import ZoneInfo

from price_feed import MARKETS, UTC, candle, closed_m15, market_document, parse_time, utcnow

MAX_DAYS = 45
MAX_M15 = MAX_DAYS * 96


def connect(path: str | Path):
    location = Path(path).expanduser().resolve()
    location.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = sqlite3.connect(str(location), timeout=30, check_same_thread=False)
    db.execute("PRAGMA busy_timeout=30000")
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("CREATE TABLE IF NOT EXISTS prices (symbol TEXT PRIMARY KEY, source TEXT NOT NULL, broker_symbol TEXT NOT NULL, updated_at TEXT NOT NULL, payload TEXT NOT NULL)")
    db.execute("CREATE TABLE IF NOT EXISTS status (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
    db.commit()
    # SQLite WAL and SHM inherit directory access; keep the directory private.
    try:
        location.chmod(0o600)
    except OSError:
        pass
    return db


def set_status(db, **values):
    with db:
        for key,value in values.items():
            db.execute("INSERT INTO status(key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                       (key,str(value)))


def get_status(db):
    return dict(db.execute("SELECT key,value FROM status").fetchall())


def latest(db,symbol):
    if symbol not in MARKETS:
        return None
    record=db.execute("SELECT payload FROM prices WHERE symbol=?", (symbol,)).fetchone()
    return json.loads(record[0]) if record else None


def symbols_available(db):
    return [row[0] for row in db.execute("SELECT symbol FROM prices ORDER BY symbol").fetchall()]


def validate_payload(input_doc, now=None):
    now = now or utcnow()
    if not isinstance(input_doc,dict) or input_doc.get("schema")!="remura-price-v1":
        raise ValueError("Formato di prezzi non valido.")
    stamp = parse_time(input_doc.get("generatedAt",""))
    if stamp > now + dt.timedelta(minutes=5) or stamp < now-dt.timedelta(days=2):
        raise ValueError("Esportazione troppo vecchia o nel futuro.")
    markets=input_doc.get("markets",{})
    if not isinstance(markets,dict):
        raise ValueError("Strumenti non validi.")
    return markets


def ingest(db, input_doc, now=None):
    """Merge incremental CLOSED M15 with existing history, regenerate true H1/H4.

    Timestamps: candle open in UTC. Reject broker mix and invalid candles.
    No invented bars are inserted in gaps, including after weekends.
    """
    now=now or utcnow()
    incoming=validate_payload(input_doc,now)
    success={}
    errors={}
    for symbol,market in incoming.items():
        try:
            if symbol not in MARKETS or not isinstance(market,dict) or market.get("symbol")!=symbol:
                raise ValueError("Simbolo REMURA inatteso.")
            source=str(market.get("provider",""))
            broker=str(market.get("providerSymbol","")).strip()
            if source!="ctrader" or not broker or len(broker)>100:
                raise ValueError("Questa raccolta privata accetta solo cTrader con ticker verificato.")
            raw=market.get("timeframes",{}).get("M15",[])
            if not isinstance(raw,list) or not raw or len(raw)>5000:
                raise ValueError("M15 mancanti o quantità anomala.")
            valid=[]
            for row in raw:
                valid.append(candle(row["t"],row["o"],row["h"],row["l"],row["c"]))
            valid=closed_m15(valid,now)
            if not valid:
                raise ValueError("Nessuna candela M15 chiusa.")
            # Reject a response from the future, and keep source-specific history isolated.
            earlier=latest(db,symbol)
            cache=[]
            if earlier and earlier.get("provider")==source and earlier.get("providerSymbol")==broker:
                cache=earlier.get("timeframes",{}).get("M15",[])
            by_date={row["t"]:row for row in cache}
            by_date.update({row["t"]:row for row in valid})
            cutoff=now-dt.timedelta(days=MAX_DAYS)
            cleaned=[row for t,row in sorted(by_date.items())
                     if parse_time(t)>=cutoff and parse_time(t)+dt.timedelta(minutes=15)<=now]
            cleaned=cleaned[-MAX_M15:]
            merged=market_document(symbol,source,broker,cleaned,now)
            payload=json.dumps(merged,ensure_ascii=False,separators=(",",":"))
            with db:
                db.execute("""INSERT INTO prices(symbol,source,broker_symbol,updated_at,payload)
                              VALUES (?,?,?,?,?)
                              ON CONFLICT(symbol) DO UPDATE SET source=excluded.source,
                              broker_symbol=excluded.broker_symbol,updated_at=excluded.updated_at,payload=excluded.payload""",
                           (symbol,source,broker,merged["lastComplete"],payload))
            success[symbol]=len(merged["timeframes"]["M15"])
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            errors[symbol]=str(exc)
    return {"saved":success,"errors":errors}




def audit_market(doc, now=None):
    """Bounded integrity check: OHLC, latest 30 H1/H4 rollups, and freshness.

    Closed-market gaps are informational, not automatically corruption.
    All timestamps are UTC; Friday history is never counted as live.
    """
    now = now or utcnow()
    missing = {"integrity":"missing", "freshness":"missing", "ready":False,
               "h1":{"checked":0,"verified":0,"missingInputs":0,"mismatched":0},
               "h4":{"checked":0,"verified":0,"missingInputs":0,"mismatched":0},
               "recentGaps":0}
    if not isinstance(doc,dict) or doc.get("provider")!="ctrader":
        return missing
    try:
        frames = {}
        for tf,seconds in (("M15",900),("H1",3600),("H4",14400)):
            rows = doc["timeframes"][tf]
            if not isinstance(rows,list):
                raise ValueError("bad_frames")
            previous=None
            clean=[]
            for row in rows:
                if not isinstance(row,dict):
                    raise ValueError("bad_row")
                stamp=parse_time(row["t"])
                if int(stamp.timestamp())%seconds or (previous is not None and stamp<=previous):
                    raise ValueError("bad_timestamps")
                vals=[row[k] for k in ("o","h","l","c")]
                if not all(type(v) in (int,float) and math.isfinite(v) and v>0 for v in vals):
                    raise ValueError("bad_price")
                op,hi,lo,cl=vals
                if hi<max(op,cl,lo) or lo>min(op,cl,hi):
                    raise ValueError("bad_ohlc")
                clean.append((stamp,row))
                previous=stamp
            frames[tf]=clean
        m15=frames["M15"]
        if not m15:
            return missing
        if parse_time(doc["lastComplete"])!=m15[-1][0]:
            raise ValueError("last_complete_mismatch")
        lookup={stamp:row for stamp,row in m15}
        gaps=sum((m15[i][0]-m15[i-1][0]).total_seconds()!=900
                 for i in range(max(1,len(m15)-96),len(m15)))
        def rollup(tf,n):
            rows=frames[tf][-30:]
            status={"checked":len(rows),"verified":0,"missingInputs":0,"mismatched":0}
            for stamp,row in rows:
                samples=[lookup.get(stamp+dt.timedelta(minutes=15*j)) for j in range(n)]
                if any(s is None for s in samples):
                    status["missingInputs"]+=1
                    continue
                expected=(samples[0]["o"],max(s["h"] for s in samples),
                          min(s["l"] for s in samples),samples[-1]["c"])
                observed=tuple(row[k] for k in ("o","h","l","c"))
                if all(math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-9)
                       for a,b in zip(expected,observed)):
                    status["verified"]+=1
                else:
                    status["mismatched"]+=1
            return status
        h1=rollup("H1",4)
        h4=rollup("H4",16)
        ready=all(len(frames[tf])>=55 for tf in ("M15","H1","H4"))
        close=m15[-1][0]+dt.timedelta(minutes=15)
        age=(now-close).total_seconds()/60
        rome=ZoneInfo("Europe/Rome")
        last=close.astimezone(rome)
        today=now.astimezone(rome)
        if -5<=age<=180:
            freshness="recent"
        elif (0<=age<=72*60 and today.weekday() in (5,6)
              and last.weekday()==4 and last.hour>=16):
            freshness="weekend"
        else:
            freshness="stale"
        if age < -5 or h1["mismatched"] or h4["mismatched"]:
            integrity="invalid"
        elif h1["missingInputs"] or h4["missingInputs"]:
            integrity="partial"
        elif not ready:
            integrity="insufficient"
        else:
            integrity="verified"
        return {"integrity":integrity,"freshness":freshness,"ready":ready,
                "h1":h1,"h4":h4,"recentGaps":gaps}
    except (TypeError,ValueError,KeyError,OverflowError,AttributeError,OSError):
        return {**missing,"integrity":"invalid"}

PRICE_OUTCOMES=frozenset((
    "ok","ticker_unavailable","no_historical_bars","incomplete_history",
    "invalid_bars","request_failed","unknown_error"
))


def price_overview(db,now=None):
    """One lightweight metadata-only snapshot for the iPhone dashboard.

    No OHLC payloads, OAuth material, account IDs or private file paths are
    returned. Missing markets are explicit: they never inherit stale prices.
    """
    now=now or utcnow()
    states=get_status(db)
    saved={row[0]:row[1:] for row in db.execute(
        "SELECT symbol,source,broker_symbol,updated_at,payload FROM prices")}
    results=[]
    quality_totals={key:0 for key in ("verified","partial","invalid","insufficient","missing")}
    freshness_totals={key:0 for key in ("recent","weekend","stale","missing")}
    for symbol in sorted(MARKETS):
        record=saved.get(symbol)
        last_complete=None
        provider_symbol=None
        source=None
        counts={"M15":0,"H1":0,"H4":0}
        quality=audit_market(None,now)
        if record:
            source,provider_symbol,last_complete,payload=record
            try:
                doc=json.loads(payload)
                quality=audit_market(doc,now)
                frames=doc.get("timeframes",{})
                for timeframe in counts:
                    bars=frames.get(timeframe,[]) if isinstance(frames,dict) else []
                    counts[timeframe]=len(bars) if isinstance(bars,list) else 0
            except (ValueError,TypeError,AttributeError):
                quality={**quality,"integrity":"invalid","freshness":"missing"}
            source="backup" if (isinstance(provider_symbol,str)
                                  and provider_symbol.startswith("BACKUP · ")) else "primary"
        state={}
        try:
            state=json.loads(states.get("price_attempt:"+symbol,"{}"))
            if not isinstance(state,dict):
                state={}
        except (ValueError,TypeError):
            state={}
        outcome=state.get("outcome")
        stamp=state.get("time")
        quality_totals[quality["integrity"]]+=1
        freshness_totals[quality["freshness"]]+=1
        results.append({
            "symbol":symbol,
            "lastComplete":last_complete if isinstance(last_complete,str) else None,
            "providerSymbol":provider_symbol if isinstance(provider_symbol,str) else None,
            "source":source,
            "counts":counts,
            "quality":quality,
            "lastAttempt":stamp if isinstance(stamp,str) else None,
            "lastOutcome":outcome if outcome in PRICE_OUTCOMES else None
        })
    return {
        "schema":"remura-price-status-v1",
        "serverTime":iso_utc(now),
        "total":len(MARKETS),
        "collector":states.get("collector","disabled"),
        "collectorBatch":states.get("collector_batch"),
        "lastAttempt":states.get("last_attempt"),
        "qualityTotals":quality_totals,
        "freshnessTotals":freshness_totals,
        "markets":results
    }


def api_document(db,symbol,now=None):
    """Browser shape is exactly the existing remura-price-v1 contract."""
    data=latest(db,symbol)
    if not data:
        return None
    return {"schema":"remura-price-v1",
            "generatedAt":data.get("lastComplete",iso_utc(now or utcnow())),
            "purpose":"private-auto-feed","markets":{symbol:data}}


def iso_utc(date):
    return date.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
