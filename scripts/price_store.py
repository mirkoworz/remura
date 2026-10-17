#!/usr/bin/env python3
"""Private REMURA OHLC storage. No web framework or third-party requirements.

SQLite stores only market candles and operational state, never account credentials.
The database is a local PRIVATE file. Each update is atomic.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from pathlib import Path
import sqlite3

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
