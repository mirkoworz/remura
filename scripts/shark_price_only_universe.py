"""REMURA Track B prospective PRICE-ONLY universe (no COT pre-selection).

Not integrated with LIVE. Future caller must invoke for EVERY monitored
symbol after its existing price read/quality/price_view(), BEFORE any COT
filter/classification, in the ordinary scan/ingest cadence; NO new cTrader
requests, additional polling, or hidden signals.

This is an observational census of what the scanner ACTUALLY saw, not an
assertion that 15-minute entry opportunities were continuously monitored.
Records include no OHLC, broker mapping, account data, or COT fields. In
particular, PRICE_ONLY is not an order, nor an aggressor-flow measurement.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import math
import json
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_asof_evidence as prices

SCHEMA = "remura-price-only-universe-v1"
TABLE = "research_price_only_universe"
ALGORITHM = "remura-v162-price-view-v1"
MAX_EVENTS = 50000
MAX_DELAY = timedelta(seconds=30)
ALLOWED_QUALITY = frozenset(
    ("verified","partial","invalid","insufficient","missing"))
ALLOWED_FRESHNESS = frozenset(("recent","weekend","stale","missing"))
DIRECTIONS = frozenset((-1,0,1))
STATES = ("PRICE_CONTEXT_READY","PRICE_NO_TREND",
          "PRICE_QUALITY_BLOCKED","PRICE_NUMERIC_AMBIGUOUS")
EMA_RELATIVE_EPS = 1e-12  # numerical noise, NOT optimized trading threshold


def ensure_schema(db):
    """Manual future-release schema creation: NEVER mutate Oracle v1.62."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            symbol TEXT NOT NULL,
            observed_slot TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            witnessed_at TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN
                ('PRICE_CONTEXT_READY','PRICE_NO_TREND','PRICE_QUALITY_BLOCKED',
                 'PRICE_NUMERIC_AMBIGUOUS')),
            quality_integrity TEXT NOT NULL,
            quality_freshness TEXT NOT NULL,
            m15_close_at TEXT,
            price_side INTEGER NOT NULL CHECK(price_side IN (-1,0,1)),
            price_state TEXT,
            h1_side INTEGER NOT NULL CHECK(h1_side IN (-1,0,1)),
            h4_side INTEGER NOT NULL CHECK(h4_side IN (-1,0,1)),
            m15_side INTEGER NOT NULL CHECK(m15_side IN (-1,0,1)),
            original_source_sha256 TEXT,
            last16_tick_volume_complete INTEGER NOT NULL
                CHECK(last16_tick_volume_complete IN (0,1)),
            algorithm TEXT NOT NULL,
            PRIMARY KEY(symbol, observed_slot)
        )""")
        for kind in ("UPDATE","DELETE"):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS
                research_price_only_no_{kind.lower()}
                BEFORE {kind} ON {TABLE}
                BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def _document_digest(db,symbol,document):
    """Same in-memory document as live scanner, never a later overwrite."""
    if document is None:
        exists = db.execute("SELECT 1 FROM prices WHERE symbol=?",
                            (symbol,)).fetchone()
        if exists:
            raise ValueError("missing_original_document_but_source_exists")
        return None
    if not isinstance(document,dict):
        raise ValueError("scan_document_not_dict")
    blob = db.execute("SELECT payload FROM prices WHERE symbol=?",
                      (symbol,)).fetchone()
    if not blob or not isinstance(blob[0],str) or len(blob[0])>4_000_000:
        raise ValueError("missing_or_oversized_source")
    try:
        saved = json.loads(blob[0])
        left = json.dumps(document,sort_keys=True,ensure_ascii=True,
                          separators=(",",":"))
        right = json.dumps(saved,sort_keys=True,ensure_ascii=True,
                           separators=(",",":"))
    except (TypeError,ValueError) as e:
        raise ValueError("noncanonical_price_source") from e
    if left!=right:
        raise ValueError("price_document_race")
    return hashlib.sha256(left.encode()).hexdigest()


def _ema(values,length):
    if len(values)<length:
        raise ValueError("not_enough_closed_bars_for_ema")
    value=sum(values[:length])/length
    mult=2/(length+1)
    for cl in values[length:]:
        value=cl*mult+value*(1-mult)
    return value


def _ema_direction_not_roundoff(doc,side):
    """Protect research denominators from spurious IEEE754 EMA ordering.

    A tiny EMA ordering in an EXACTLY FLAT market is not a directional
    observation. This ~1e-12 relative numerical tolerance is NOT an
    empirically optimized profitability threshold; returns remain unproven.
    """
    for frame in ("H1","H4"):
        closes=[row["c"] for row in doc["timeframes"][frame]]
        a,b=_ema(closes,20),_ema(closes,50)
        cl=closes[-1]
        scale=max(abs(cl),abs(a),abs(b))
        gap=EMA_RELATIVE_EPS*scale
        if not (math.isfinite(scale) and math.isfinite(gap) and gap>0):
            return False
        if side==1:
            if not (cl-a>gap and a-b>gap):
                return False
        elif side==-1:
            if not (a-cl>gap and b-a>gap):
                return False
        else:
            return False
    return True


def prepare(db, *, symbol, scan_at, observed_document,
            quality, price_result, price_reason, clock=None):
    """Write ONE record per market / observed 15-min UTC scan slot.

    Caller MUST use existing scan_at and the same document/quality/price_view
    it used for scanning. No COT argument, no reading COT tables, no outcomes.
    Instrument candidates are collected independently of current COT status.

    A real future backend should use the same DB transaction as its scan
    changes. Injected clock exists exclusively for synthetic tests.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("scan_transaction_required")
    if symbol not in prices_monitored():
        raise ValueError("symbol_not_monitored")
    observed=witness._parse(scan_at)
    now=witness._clock(clock)
    if not observed<=now<=observed+MAX_DELAY:
        raise ValueError("scan_not_happening_now")
    if not isinstance(quality,dict):
        raise ValueError("original_price_quality_missing")
    integrity=quality.get("integrity")
    freshness=quality.get("freshness")
    ready=quality.get("ready")
    if (integrity not in ALLOWED_QUALITY or freshness not in ALLOWED_FRESHNESS
            or type(ready) is not bool):
        raise ValueError("invalid_original_quality")
    if type(price_reason) is not str or price_reason not in (
            "price_present","price_no_direction","trend_disagreement",
            "prices_stale","prices_missing","candles_insufficient",
            "price_error","ohlc_mismatch","market_closed"):
        raise ValueError("price_only_reason_not_allowlisted")
    # Accepted price candidates already require the stricter _source()
    # attestation: same SQLite snapshot, canonical source identity, mapping,
    # closed M15/H1/H4, rollups and SHA-256. Do NOT re-fetch and canonicalize
    # the entire OHLC document a second time in _document_digest().
    # For rejected/missing price cases, _document_digest() remains mandatory
    # so every denominator row is independently bound to its original source.
    source_sha=None
    price_source_attested=False
    price_side=h1=h4=m15=0
    price_state=None
    last_close=None
    complete=False
    if ready and integrity=="verified" and freshness=="recent":
        if price_result is None:
            if price_reason in ("price_no_direction","trend_disagreement"):
                state="PRICE_NO_TREND"
            else:
                # Even with M15 recent and aggregate quality verified, LIVE
                # price_view can reject H1 by its own tighter clock guard.
                state="PRICE_QUALITY_BLOCKED"
            # Both are denominator entries; neither is a trading signal.
        else:
            if price_reason!="price_present":
                raise ValueError("price_reason_must_match_ready_candidate")
            if not isinstance(price_result,dict):
                raise ValueError("price_signal_not_a_dict")
            price_side=price_result.get("side")
            h1=price_result.get("h1_side")
            h4=price_result.get("h4_side")
            m15=price_result.get("m15_side")
            price_state=price_result.get("state")
            last_close=price_result.get("last_m15")
            if (type(price_side) is not int or price_side not in (-1,1)
                    or type(h1) is not int or h1!=price_side
                    or type(h4) is not int or h4!=price_side
                    or type(m15) is not int or m15 not in DIRECTIONS
                    or price_state not in ("watch","partial","confirmed")
                    or (price_state in ("partial","confirmed")
                        and m15!=price_side)):
                raise ValueError("invalid_price_only_classification")
            closed=witness._parse(last_close)
            if closed>observed:
                raise ValueError("future_price_bar")
            try:
                proof=prices._source(
                    db,symbol,observed,closed,observed_document)
            except ValueError as exc:
                # Preserve original source-race failure semantics for the
                # shared legacy/compact research preparation contract.
                if str(exc)=="price_document_changed_since_scan":
                    raise ValueError("price_document_race") from exc
                raise
            source_sha=proof["sha"]
            price_source_attested=True
            complete=proof["volume16"]
            state=("PRICE_CONTEXT_READY"
                   if _ema_direction_not_roundoff(observed_document,price_side)
                   else "PRICE_NUMERIC_AMBIGUOUS")
    else:
        if price_result is not None or price_reason=="price_present":
            raise ValueError("price_signal_from_stale_or_missing_quality")
        state="PRICE_QUALITY_BLOCKED"
    if not price_source_attested:
        source_sha=_document_digest(db,symbol,observed_document)
    bucket=int(observed.timestamp())//900*900
    slot=witness._iso(datetime.fromtimestamp(bucket,tz=timezone.utc))
    # One deterministic 16-field row: the legacy per-market writer and
    # future compact scan-batch writer MUST share this exact validation.
    row=(symbol,slot,witness._iso(observed),witness._iso(now),state,
         integrity,freshness,witness._iso(witness._parse(last_close)) if last_close else None,
         price_side,price_state,h1,h4,m15,source_sha,int(complete),ALGORITHM)
    status={"schema":SCHEMA,"status":state,"newRows":1,
            "priceQualifiedWithoutCot":state=="PRICE_CONTEXT_READY",
            "existingPriceCadenceOnly":True,
            "last16TickVolumeComplete":complete,
            "originalPriceDirectionReproducedIndependently":False,
            "emaSeparationAboveNumericalTolerance":(
                state=="PRICE_CONTEXT_READY"),
            "independentCollectionTimeKnown":False,
            "noCotDataUsed":True,
            "edge":"NOT_ESTABLISHED","newBrokerCalls":0,
            "alertsEnabled":False,"ordersEnabled":False}
    return row,status


def capture(db, *, symbol, scan_at, observed_document,
            quality, price_result, price_reason, clock=None):
    """Legacy research writer; unchanged semantics, same shared preparation."""
    row,result=prepare(
        db,symbol=symbol,scan_at=scan_at,observed_document=observed_document,
        quality=quality,price_result=price_result,price_reason=price_reason,
        clock=clock)
    if db.execute(
        f"SELECT 1 FROM {TABLE} WHERE symbol=? AND observed_slot=?",
        (symbol,row[1])).fetchone():
        return {"schema":SCHEMA,"status":"DUPLICATE_SCAN_SLOT",
                "newRows":0,"newBrokerCalls":0,
                "edge":"NOT_ESTABLISHED","alertsEnabled":False}
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_EVENTS:
        raise ValueError("price_only_capacity_reached")
    db.execute(f"INSERT INTO {TABLE} VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",row)
    return result


def prices_monitored():
    """Freeze exactly the 34 markets from the existing Squalincome catalog."""
    from scripts.shark_cot_asof_witness import CATALOG
    return CATALOG


def capture_optional(db,**kwargs):
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("scan_transaction_required")
    try:
        return capture(db,**kwargs)
    except ValueError as exc:
        # Capacity exhaustion is not generic N/D; future operators must see
        # that sampling STOPPED before treating its denominator as complete.
        status=("PRICE_UNIVERSE_CAPACITY_REACHED"
                if str(exc)=="price_only_capacity_reached"
                else "PRICE_UNIVERSE_NOT_RECORDED")
        return {"schema":SCHEMA,"status":status,
                "newRows":0,"noCotDataUsed":True,"edge":"NOT_ESTABLISHED",
                "newBrokerCalls":0,"alertsEnabled":False}


def summary(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    rows=db.execute(
        f"SELECT state,count(*),count(DISTINCT symbol) FROM {TABLE} "
        "GROUP BY state").fetchall()
    total=sum(x[1] for x in rows)
    # Current private_server.squalincome_loop is scheduled every 15 minutes.
    # Not a real-time ETA: weekends, outages and targeted scans may vary.
    # A silent 50k-row cap could otherwise invalidate the denominator.
    remaining=max(0,MAX_EVENTS-total)
    full_market_count=len(prices_monitored())
    return {"schema":SCHEMA,
            "totalScans":total,
            "byState":{state:count for state,count,_ in rows},
            "maxConfiguredRows":MAX_EVENTS,
            "remainingRows":remaining,
            "fullUniverseMarkets":full_market_count,
            "theoreticalDaysAtEvery15MinFullScan":round(
                remaining/(full_market_count*96),2),
            "capacityExhausted":remaining==0,
            "tradingObservationsValidated":0,
            "conditionalOnCot":False,
            "retrospectiveHistoryReconstructed":False,
            "priceOnlyIndependentProfitabilityVerified":False,
            "edge":"NOT_ESTABLISHED","newBrokerCalls":0}
