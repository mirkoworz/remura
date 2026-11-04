"""REMURA Track B: prospective, NO-NETWORK, per-observation OHLC provenance.

OFFLINE ONLY. Not imported by production. Future integration must call this
immediately after the genuine Squalincome history INSERT, using the SAME SQLite
connection, inside the SAME transaction, only if history INSERT rowcount==1.
No new cTrader GET, signals, alerts, orders, external APIs, or broker names.

REMURA v1.62 prices.updated_at and market_document.lastComplete both denote
the M15 candle OPEN, NOT the ingest/collection time. This module explicitly
does NOT label either as collectedAt. witnessed_at is actual recorder time.
It can attest what OHLC source/rollups were present locally at observed_at,
not an independent exchange quote, CFTC flow, or verified fill.
"""
from __future__ import annotations

from datetime import datetime, timedelta
import hashlib
import json
import math
import sqlite3

from scripts import shark_cot_asof_witness as witness

SCHEMA = "remura-shark-price-asof-v1"
TABLE = "research_squalincome_price_evidence"
FRAMES = {"M15": 900, "H1": 3600, "H4": 14400}
STALE_MINUTES = {"M15": 180, "H1": 120, "H4": 300}
MIN_BARS = 55
MAX_BARS = {"M15": 4320, "H1": 900, "H4": 280}
MAX_LATENCY_SECONDS = 30
MAX_EVENTS = 15000
ALGO = "price_source_and_rollup_v162_prospective_v1"


def ensure_schema(db):
    """One-time opt-in on a FUTURE coordinated release, never on LIVE v1.62."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            symbol TEXT NOT NULL, report_date TEXT NOT NULL,
            price_time TEXT NOT NULL, observed_at TEXT NOT NULL,
            witnessed_at TEXT NOT NULL,
            source_document_sha256 TEXT NOT NULL,
            m15_closed_at TEXT NOT NULL, h1_closed_at TEXT NOT NULL,
            h4_closed_at TEXT NOT NULL,
            last16_tick_volume_complete INTEGER NOT NULL CHECK(last16_tick_volume_complete IN (0,1)),
            algorithm TEXT NOT NULL,
            PRIMARY KEY(symbol,report_date,price_time)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_price_asof_no_update
            BEFORE UPDATE ON {TABLE} BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_price_asof_no_delete
            BEFORE DELETE ON {TABLE} BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def _bars(rows, duration, limit):
    if not isinstance(rows, list) or not MIN_BARS <= len(rows) <= limit:
        raise ValueError("insufficient_or_unbounded_bars")
    result=[]
    last=None
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("bad_candle")
        started=witness._parse(row.get("t"))
        if int(started.timestamp())%duration or (last is not None and started<=last):
            raise ValueError("noncontiguous_order_or_time_alignment")
        ohlc=tuple(row.get(x) for x in ("o","h","l","c"))
        if (any(type(v) not in (int,float) or not math.isfinite(v) or v<=0
                for v in ohlc) or ohlc[1]<max(ohlc[0],ohlc[3])
                or ohlc[2]>min(ohlc[0],ohlc[3]) or ohlc[1]<ohlc[2]):
            raise ValueError("invalid_ohlc")
        v=row.get("v")
        if v is not None and (type(v) is not int or not 0<=v<=9007199254740991):
            raise ValueError("invalid_tick_volume")
        result.append((started,row))
        last=started
    return result


def _rollups_valid(m15, rows, n):
    lookup={at:bar for at,bar in m15}
    for start, bar in rows[-30:]:
        inputs=[lookup.get(start+timedelta(minutes=15*i)) for i in range(n)]
        if any(x is None for x in inputs):
            raise ValueError("missing_m15_rollup_input")
        observed=(bar["o"],bar["h"],bar["l"],bar["c"])
        expected=(inputs[0]["o"],max(x["h"] for x in inputs),
                  min(x["l"] for x in inputs),inputs[-1]["c"])
        if any(not math.isclose(a,b,abs_tol=1e-9,rel_tol=1e-9)
               for a,b in zip(observed,expected)):
            raise ValueError("ohlc_rollup_mismatch")
        v=sum(x["v"] for x in inputs) if all("v" in x for x in inputs) else None
        if bar.get("v") != v:
            raise ValueError("tick_volume_rollup_mismatch")


def _source(db,symbol,at,expected_close):
    row=db.execute(
        "SELECT source,broker_symbol,updated_at,payload FROM prices WHERE symbol=?",
        (symbol,)).fetchone()
    if row is None:
        raise ValueError("price_document_missing")
    source,broker,updated,raw=row
    if (source!="ctrader" or not isinstance(broker,str)
            or not broker.strip() or len(broker)>100
            or not isinstance(raw,str) or len(raw)>4_000_000):
        raise ValueError("unverified_price_mapping_or_payload")
    try:
        doc=json.loads(raw)
    except (TypeError,ValueError) as exc:
        raise ValueError("bad_price_document") from exc
    if (not isinstance(doc,dict) or doc.get("symbol")!=symbol
            or doc.get("provider")!="ctrader"
            or doc.get("providerSymbol")!=broker
            or doc.get("timezone")!="UTC"
            or doc.get("sourceTimeframe")!="M15"
            or not isinstance(doc.get("timeframes"),dict)):
        raise ValueError("source_mapping_mismatch")
    frames={}
    for frame,seconds in FRAMES.items():
        frames[frame]=_bars(
            doc["timeframes"].get(frame),seconds,MAX_BARS[frame])
    m15=frames["M15"]
    latest_start=m15[-1][0]
    # Both fields are CANDLE OPEN timestamps, not actual ingestion times.
    if (witness._parse(updated)!=latest_start
            or witness._parse(doc.get("lastComplete"))!=latest_start):
        raise ValueError("last_complete_open_mismatch")
    latest_close={}
    for frame,seconds in FRAMES.items():
        closed=frames[frame][-1][0]+timedelta(seconds=seconds)
        age=(at-closed).total_seconds()/60
        if not 0<=age<=STALE_MINUTES[frame]:
            raise ValueError("stale_future_or_unclosed_"+frame.lower())
        latest_close[frame]=closed
    if latest_close["M15"]!=expected_close:
        raise ValueError("different_m15_at_original_observation")
    _rollups_valid(m15,[*frames["H1"]],4)
    _rollups_valid(m15,[*frames["H4"]],16)
    recent=m15[-16:]
    last16=all("v" in bar and bar["v"]>0 for _,bar in recent) and all(
        (recent[i][0]-recent[i-1][0]).total_seconds()==900
        for i in range(1,len(recent)))
    return {
        "sha":hashlib.sha256(raw.encode()).hexdigest(),
        "close":latest_close,"volume16":last16,
    }


def capture(db,*,history_id,clock=None):
    """Record ONLY a fresh live observation's price-source and quality context.

    No open/close price values or broker symbol are saved. Call inside same
    SQLite transaction immediately after INSERT INTO squalincome_history.
    Caller MUST verify INSERT rowcount==1 (INSERT OR IGNORE may insert zero).
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("history_insert_transaction_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("history_row_id_required")
    now=witness._clock(clock)
    row=db.execute(
        "SELECT symbol,report_date,price_time,observed_at,state,"
        "price_state,price_side,h1_side,h4_side,m15_side "
        "FROM squalincome_history WHERE id=?", (history_id,)).fetchone()
    if row is None:
        raise ValueError("original_observation_missing")
    sym,report,price,stamp,state,pstate,side,h1,h4,m15=row
    observed=witness._parse(stamp)
    closed=witness._parse(price)
    if (not observed<=now<=observed+timedelta(seconds=MAX_LATENCY_SECONDS)
            or not isinstance(sym,str) or not 3<=len(sym)<=10
            or state not in ("aligned","divergent")
            or pstate not in ("watch","partial","confirmed")
            or type(side) is not int or side not in (-1,1)
            or type(h1) is not int or h1!=side
            or type(h4) is not int or h4!=side
            or type(m15) is not int or m15 not in (-1,0,1)
            or (pstate!="watch" and m15!=side)
            or report is None):
        raise ValueError("invalid_original_signal_or_time")
    doc=_source(db,sym,observed,closed)
    if db.execute(
        f"SELECT 1 FROM {TABLE} WHERE symbol=? AND report_date=? "
        "AND price_time=?", (sym,report,price)).fetchone():
        raise ValueError("price_evidence_already_recorded")
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_EVENTS:
        raise ValueError("price_evidence_capacity_reached")
    db.execute(
        f"INSERT INTO {TABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?)",
        (sym,report,price,stamp,witness._iso(now),doc["sha"],
         *(witness._iso(doc["close"][frame]) for frame in FRAMES),
         int(doc["volume16"]),ALGO))
    return {
        "schema":SCHEMA,"status":"PRICE_ASOF_SOURCE_VERIFIED",
        "m15H1H4FreshAtOriginalObservation":True,
        "h1H4RollupsValidatedAgainstM15":True,
        "sourceMappingObservedLocally":True,
        "candleCollectionTimeIndependentlyKnown":False,
        "sourceBrokerMappingHistoricallyVersioned":False,
        "originalPriceDirectionIndependentlyReproduced":False,
        "last16TickVolumeComplete":bool(doc["volume16"]),
        "realAggressorFlowMeasured":False,
        "edge":"NOT_ESTABLISHED","brokerCalls":0,
        "ordersEnabled":False,"alertsEnabled":False,
    }


def capture_optional(db,*,history_id,clock=None):
    """On missing/stale proof retain the actual observation but mark N/D.

    Only known source/clock/quality ValueError are translated to N/D;
    unexpected sqlite3 database errors propagate for rollback.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("history_insert_transaction_required")
    try:
        return capture(db,history_id=history_id,clock=clock)
    except ValueError:
        return {
            "schema":SCHEMA,"status":"PRICE_PROVENANCE_NOT_VERIFIABLE",
            "m15H1H4FreshAtOriginalObservation":False,
            "candleCollectionTimeIndependentlyKnown":False,
            "edge":"NOT_ESTABLISHED","brokerCalls":0,
            "ordersEnabled":False,"alertsEnabled":False,
        }


def aggregate(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    total=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    with_tick=db.execute(
        f"SELECT count(*) FROM {TABLE} WHERE last16_tick_volume_complete=1"
    ).fetchone()[0]
    return {"schema":SCHEMA,"recordedEvidence":total,
            "observationsWithLast16TickVolume":with_tick,
            "independentPriceCollectedAt":False,
            "validatedTradingEdge":False,"brokerCalls":0}
