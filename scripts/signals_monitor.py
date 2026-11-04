#!/usr/bin/env python3
"""REMURA private Squalincome observer (v1.37).

Read-only analysis of verified cTrader OHLC and locally stored official CFTC
futures. A SQLite baseline is required before any transition can be recorded.
No browser, Google, retail, trades, API tokens, webhooks or notifications.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import sqlite3
from contextlib import contextmanager

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
HISTORY_KEEP_DAYS=30
HISTORY_MAX_PER_SYMBOL=720
HISTORY_API_PER_SYMBOL=12


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
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_last_scan(
        id INTEGER PRIMARY KEY CHECK(id=1),
        scanned_at TEXT NOT NULL, summary TEXT NOT NULL)""")
    # Append-only samples of accepted REAL observations (no fabricated OHLC).
    # Existing v1.36 baselines are NOT deleted, replaced, or backdated.
    db.execute("""CREATE TABLE IF NOT EXISTS squalincome_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,
        state TEXT NOT NULL CHECK(state IN ('aligned','divergent')),
        cot_side INTEGER NOT NULL CHECK(cot_side IN (-1,1)),
        price_side INTEGER NOT NULL CHECK(price_side IN (-1,1)),
        h4_side INTEGER CHECK(h4_side IN (-1,0,1) OR h4_side IS NULL),
        h1_side INTEGER CHECK(h1_side IN (-1,0,1) OR h1_side IS NULL),
        m15_side INTEGER CHECK(m15_side IN (-1,0,1) OR m15_side IS NULL),
        price_state TEXT NOT NULL CHECK(price_state IN ('watch','partial','confirmed')),
        report_date TEXT NOT NULL,
        price_time TEXT NOT NULL,
        observed_at TEXT NOT NULL,
        cot_weekly REAL,
        cot_sustained INTEGER,
        origin TEXT NOT NULL CHECK(origin IN ('baseline','update','first_after_upgrade')),
        event_type TEXT,
        UNIQUE(symbol,report_date,price_time))""")
    db.execute("CREATE INDEX IF NOT EXISTS idx_squal_history_symbol"
               " ON squalincome_history(symbol,id DESC)")
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


def price_view(doc, now, *, quality=None):
    if not isinstance(doc,dict):return None
    quality=audit_market(doc,now) if quality is None else quality
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
    return {"side":side,"state":state,"last_m15":m15["close_time"],
            "h4_side":h4["side"],"h1_side":h1["side"],"m15_side":m15["side"]}


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


def cot_exclusion(series, symbol, now):
    """Allowlisted reason: no raw CFTC rows in HTTP diagnostics."""
    if len(series)<2:
        return "cot_missing"
    try:
        first,previous=series[-1],series[-2]
        age=(now.date()-dt.date.fromisoformat(first[0])).days
        span=(dt.date.fromisoformat(first[0])-dt.date.fromisoformat(previous[0])).days
        if age<0 or age>14:
            return "cot_stale"
        if not 6<=span<=10:
            return "cot_nonconsecutive"
    except (ValueError,TypeError,IndexError):
        return "cot_missing"
    # A valid but opposed TFF institutional group is not a missing report.
    if not (symbol in OTHER and OTHER[symbol][0]=="disagg"):
        spec,other=series[-1][2]-series[-2][2],series[-1][1]-series[-2][1]
        if abs(spec)>MIN_COT_DELTA and other*spec<0 and abs(other)>MIN_COT_DELTA:
            return "cot_group_conflict"
    # A valid report without enough directional change is NOT missing data.
    return "cot_no_direction"


def safe_frame_diagnostics(doc, now):
    """Export only UTC close timestamps, counts and ages; never OHLC or tokens."""
    result={}
    timeframes=doc.get("timeframes") if isinstance(doc,dict) else None
    for name,seconds in DURATIONS.items():
        entry={"lastClosedAt":None,"ageMinutes":None,"bars":0}
        try:
            rows=timeframes.get(name) if isinstance(timeframes,dict) else None
            if isinstance(rows,list):
                entry["bars"]=len(rows)
                if rows:
                    opened=parse_time(rows[-1]["t"])
                    closed=opened+dt.timedelta(seconds=seconds)
                    age=(now-closed).total_seconds()/60
                    if math.isfinite(age) and abs(age)<10_000_000:
                        entry["lastClosedAt"]=closed.isoformat()
                        entry["ageMinutes"]=round(age)
        except (ValueError,TypeError,KeyError,OverflowError,AttributeError,OSError):
            pass
        result[name]=entry
    return result


def price_exclusion(doc, now, *, quality=None):
    """Report the reason a price was rejected without exporting private bars."""
    if doc is None:
        return "prices_missing"
    quality=audit_market(doc,now) if quality is None else quality
    if quality["h1"]["mismatched"] or quality["h4"]["mismatched"]:
        return "ohlc_mismatch"
    if quality["integrity"]=="invalid":
        return "price_error"
    if quality["freshness"]=="weekend":
        return "market_closed"
    if quality["freshness"] in ("stale","missing"):
        return "prices_stale"
    if quality["integrity"] in ("missing","insufficient","partial") or not quality["ready"]:
        return "candles_insufficient"
    if quality["integrity"]!="verified":
        return "price_error"
    try:
        frames={}
        for key,seconds in DURATIONS.items():
            rows=doc["timeframes"][key]
            if len(rows)<MIN_FRAMES:
                return "candles_insufficient"
            frame=frame_direction(rows,seconds,now)
            if frame is None:
                return "prices_stale"
            frames[key]=frame
        h4,h1=frames["H4"],frames["H1"]
        if h4["side"] and h1["side"] and h4["side"]!=h1["side"]:
            return "trend_disagreement"
        return "price_no_direction"
    except (KeyError,TypeError,ValueError,IndexError,OverflowError):
        return "price_error"


def scan_once(db_path,now=None,*,targets=None):
    """Preserve the exact deployed and pinned legacy entrypoint/signature."""
    return _scan_once(db_path,now,targets=targets)


def scan_once_with_h1_frames(db_path,now=None,*,targets=None):
    """Opt-in internal targeted scan: one atomic H1 metadata capture."""
    if targets is None:
        raise ValueError("H1 paired capture requires targeted scan")
    return _scan_once(db_path,now,targets=targets,capture_frames=True)


def scan_once_with_price_only_research(db_path, now=None, *, targets=None):
    """FUTURE-ONLY explicit opt-in; never called by LIVE v1.62.

    No import, table or extra SQL on the default scan_once code path.
    App integration would require an audited feature flag set to OFF by default.
    The import fallback is necessary because private_server runs from scripts/.
    """
    import sys
    from pathlib import Path
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts import shark_price_only_universe as research
    return _scan_once(db_path, now, targets=targets,
                      price_only_research=research)


def scan_once_with_compact_price_only_research(db_path, now=None, *, targets=None):
    """Future-only, explicit compact research mode; LIVE default unchanged.

    Complete 34-market scan becomes ONE SHA-verified zlib SQLite record,
    distinct from targeted scans. No legacy per-symbol research table.
    """
    import sys
    from pathlib import Path
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)
    from scripts import shark_price_only_universe as preparer
    from scripts import shark_price_only_compact as compact
    return _scan_once(db_path, now, targets=targets,
                      compact_research=compact, compact_preparer=preparer)


def _scan_once(db_path,now=None,*,targets=None,capture_frames=False,
               price_only_research=None,compact_research=None,
               compact_preparer=None):
    """Observe all markets on periodic scans, or a small verified fresh batch.

    Targeted scans update existing observation/history/event tables, but NEVER
    overwrite the 34-market diagnostics summary. They use the SAME freshness
    gates, COT validation, event transition and SQLite deduplication as a full
    scan; no relaxed thresholds, fake observations, or notifications.
    """
    now=now or utcnow()
    all_symbols=monitored_symbols()
    if targets is None:
        symbols=all_symbols
    else:
        if (not isinstance(targets,(tuple,list,set,frozenset)) or
            not 1<=len(targets)<=5 or
            any(type(symbol) is not str or symbol not in all_symbols for symbol in targets)):
            raise ValueError("Invalid Squalincome fresh-batch symbols")
        symbols=tuple(sorted(set(targets)))
    # Safe to run even when the upstream collector is not ready: no invented report.
    db=connect(db_path)
    if compact_research is not None:
        # Bound SQLite contention even during CREATE TABLE IF NOT EXISTS:
        # the original monitor/schema entrypoint must remain unchanged.
        db.execute("PRAGMA busy_timeout=5000")
    ensure_tables(db)
    from cot_monitor import ensure_table as ensure_cot_table
    ensure_cot_table(db)
    if price_only_research is not None:
        # Schema + new writes are enabled ONLY by the explicit research entry
        # point. No migration, import or new request on legacy scan_once.
        price_only_research.ensure_schema(db)
    if compact_research is not None:
        if price_only_research is not None or compact_preparer is None:
            raise ValueError("exclusive_research_store_required")
        compact_research.ensure_schema(db)
    examined=baselines=events=updates=0
    exclusions={}
    frames_by_symbol={}
    price_quality_by_symbol={}
    research_totals={}
    compact_rows=[]
    scan_savepoint_counter=0

    @contextmanager
    def scan_write():
        """Preserve legacy commits; compact mode keeps the outer transaction.

        Per-symbol SAVEPOINT prevents an error inside a symbol's multi-write
        sequence from leaking partial changes into the final atomic commit.
        """
        nonlocal scan_savepoint_counter
        if compact_research is None:
            with db:
                yield
            return
        scan_savepoint_counter+=1
        name=f"remura_scan_{scan_savepoint_counter}"
        db.execute(f"SAVEPOINT {name}")
        try:
            yield
        except BaseException:
            db.execute(f"ROLLBACK TO SAVEPOINT {name}")
            db.execute(f"RELEASE SAVEPOINT {name}")
            raise
        else:
            db.execute(f"RELEASE SAVEPOINT {name}")

    def read_original_price(symbol):
        # Exactly the original v1.62 price operations, with no broker GETs.
        document=latest(db,symbol)
        frames_by_symbol[symbol]=safe_frame_diagnostics(document,now)
        # Same immutable loaded document and scan UTC as frame metadata.
        # Values are allowlisted; never store broker IDs, OHLC or secrets.
        quality=audit_market(document,now)
        price_quality_by_symbol[symbol]={
            "integrity":quality.get("integrity"),
            "freshness":quality.get("freshness"),
            "ready":quality.get("ready"),
            "checkedAt":now.isoformat()
        }
        price=price_view(document,now,quality=quality) if document else None
        return document,quality,price

    try:
        if compact_research is not None:
            # Acquire a SQLite write reservation before the first price/COT
            # observation. Roll back *all* original Squalincome changes if
            # the compact block fails to seal, if SQLite is busy, or if a
            # worker terminates before COMMIT. No historical backfill.
            db.execute("BEGIN IMMEDIATE")
        for symbol in symbols:
            compact_row=None
            try:
                if compact_research is not None:
                    # All price data are calculated BEFORE COT. The exact
                    # shared price-only validation is reused, but there are
                    # NO per-market research SQL writes or separate DBs.
                    document,quality,price=read_original_price(symbol)
                    reason=("price_present" if price is not None else
                            price_exclusion(document,now,quality=quality))
                    compact_row,_=compact_preparer.prepare(
                            db,symbol=symbol,scan_at=now.isoformat(),
                            observed_document=document,quality=quality,
                            price_result=price,price_reason=reason)
                if price_only_research is not None:
                    # The PRICE-ONLY denominator is captured BEFORE ANY
                    # per-symbol COT access. An absent/broken COT must never
                    # preselect the population of price candidates.
                    document,quality,price=read_original_price(symbol)
                    reason=("price_present" if price is not None else
                            price_exclusion(document,now,quality=quality))
                    with db:
                        db.execute("BEGIN")
                        research_result=price_only_research.capture_optional(
                            db,symbol=symbol,scan_at=now.isoformat(),
                            observed_document=document,quality=quality,
                            price_result=price,price_reason=reason)
                    result_status=research_result["status"]
                    research_totals[result_status]=research_totals.get(
                        result_status,0)+1
                series=cot_series(db,symbol)
                cot=cot_view(series,symbol,now)
                if price_only_research is None and compact_research is None:
                    document,quality,price=read_original_price(symbol)
                current=classify(cot,price)
                if current is None:
                    reasons=[]
                    if cot is None:
                        reasons.append(cot_exclusion(series,symbol,now))
                    if price is None:
                        reasons.append(price_exclusion(document,now,quality=quality))
                    exclusions[symbol]=reasons or ["no_qualifying_setup"]
                    continue
                examined+=1
                row=db.execute("SELECT state,side,report_date,price_time,price_state,observed_at "
                               "FROM squalincome_observations WHERE symbol=?",(symbol,)).fetchone()
                prior=dict(zip(("state","side","report_date","price_time","price_state","observed_at"),row)) if row else None
                if prior and (current["report_date"]<prior["report_date"] or
                              current["price_time"]<prior["price_time"]):
                    continue
                if prior and (current["report_date"]==prior["report_date"] and
                              current["price_time"]==prior["price_time"]):
                    continue  # No new source data, even if the classification algorithm changed.
                if prior:
                    try:
                        previous_observed=dt.datetime.fromisoformat(prior["observed_at"])
                        elapsed=now-previous_observed
                        if not dt.timedelta(0)<=elapsed<=dt.timedelta(days=14):
                            prior=None  # Long outages require a new baseline, never a stale alert.
                    except (ValueError,TypeError):
                        prior=None
                change=transition(prior,current)
                stamp=now.isoformat()
                with scan_write():
                    if change:
                        cur=db.execute("INSERT OR IGNORE INTO squalincome_events"
                           "(symbol,event_type,side,report_date,price_time,observed_at,detail) VALUES(?,?,?,?,?,?,?)",
                           (symbol,change,current["side"],current["report_date"],current["price_time"],stamp,
                            "COT futures e struttura OHLC verificata; osservazione, non ordine o previsione."))
                        if cur.rowcount:events+=1
                    if prior is None:baselines+=1
                    else:updates+=1
                    history_found=db.execute(
                        "SELECT 1 FROM squalincome_history WHERE symbol=? LIMIT 1",
                        (symbol,)).fetchone() is not None
                    origin=("baseline" if prior is None and not history_found else
                            "first_after_upgrade" if not history_found else "update")
                    # An existing reference may be valid even if no v1.37
                    # timeline exists yet. Never invent older data for it.
                    db.execute("INSERT OR IGNORE INTO squalincome_history"
                        "(symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
                        "price_state,report_date,price_time,observed_at,cot_weekly,"
                        "cot_sustained,origin,event_type) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (symbol,current["state"],current["side"],price["side"],
                         price.get("h4_side"),price.get("h1_side"),price.get("m15_side"),
                         current["price_state"],current["report_date"],current["price_time"],
                         stamp,cot.get("weekly"),int(bool(cot.get("sustained"))),
                         origin,change))
                    db.execute("DELETE FROM squalincome_history WHERE symbol=? AND id NOT IN"
                        " (SELECT id FROM squalincome_history WHERE symbol=?"
                        " ORDER BY id DESC LIMIT ?)",
                        (symbol,symbol,HISTORY_MAX_PER_SYMBOL))
                    db.execute("INSERT INTO squalincome_observations"
                        "(symbol,state,side,report_date,price_time,price_state,observed_at)"
                        " VALUES(?,?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
                        "state=excluded.state,side=excluded.side,report_date=excluded.report_date,"
                        "price_time=excluded.price_time,price_state=excluded.price_state,"
                        "observed_at=excluded.observed_at",
                        (symbol,current["state"],current["side"],current["report_date"],current["price_time"],
                         current["price_state"],stamp))
            except sqlite3.Error:
                # A broken research evidence table is an operational database
                # failure, NOT an innocent N/D. Never mask it when opt-in.
                if price_only_research is not None or compact_research is not None:
                    raise
                exclusions[symbol]=["scan_error"]
                continue
            except (ValueError,TypeError,KeyError,OverflowError):
                # Never expose provider exceptions, prices or credentials.
                exclusions[symbol]=["scan_error"]
                continue
            finally:
                if compact_research is not None:
                    # Even when price processing or COT fails for a symbol,
                    # preserve a marked UNKNOWN cell in the full denominator.
                    # Missing means observation failed NOW, never a backfill.
                    if compact_row is None:
                        compact_row=compact_research.missing_row(
                            symbol=symbol,scan_at=now.isoformat())
                    compact_rows.append(compact_row)
        # Keep counters internally consistent even if a single market errors.
        examined=len(symbols)-len(exclusions)
        counts={}
        for reasons in exclusions.values():
            for reason in reasons:
                counts[reason]=counts.get(reason,0)+1
        data_gaps={"cot_missing","cot_stale","cot_nonconsecutive",
                   "prices_missing","prices_stale","market_closed",
                   "candles_insufficient","timeframe_disagreement",
                   "ohlc_mismatch","trend_disagreement","price_error","scan_error"}
        outcome=("events_detected" if events else
                 "no_significant_event" if examined else
                 "data_insufficient" if any(r in data_gaps for r in counts) else
                 "no_qualifying_setup")
        summary={"lastScanAt":now.isoformat(),"trackedMarkets":len(symbols),
                 "analyzed":examined,"excluded":len(exclusions),
                 "exclusionReasons":counts,
                 "exclusions":[{"symbol":symbol,"reasons":reasons}
                               for symbol,reasons in sorted(exclusions.items())],
                 "markets":[{"symbol":symbol,
                             "timeframes":frames_by_symbol.get(symbol,safe_frame_diagnostics(None,now)),
                             "priceQuality":price_quality_by_symbol.get(symbol),
                             "analyzed":symbol not in exclusions}
                            for symbol in symbols],
                 "newBaselines":baselines,"updatedObservations":updates,
                 "newEvents":events,"outcome":outcome}
        with scan_write():
            db.execute("DELETE FROM squalincome_events WHERE observed_at < ?",
                ((now-dt.timedelta(days=EVENT_KEEP_DAYS)).isoformat(),))
            db.execute("DELETE FROM squalincome_history WHERE observed_at < ?",
                ((now-dt.timedelta(days=HISTORY_KEEP_DAYS)).isoformat(),))
            # This summary is a full 34-market snapshot. Fresh-batch scans
            # must not replace it with partial counters or fake 0-stale totals.
            if targets is None:
                db.execute("INSERT INTO squalincome_last_scan(id,scanned_at,summary)"
                    " VALUES(1,?,?) ON CONFLICT(id) DO UPDATE SET"
                    " scanned_at=excluded.scanned_at,summary=excluded.summary",
                    (now.isoformat(),json.dumps(summary,sort_keys=True)))
        result={"examined":examined,"baselines":baselines,"newEvents":events}
        if compact_research is not None:
            if len(compact_rows)!=len(symbols):
                raise ValueError("incomplete_price_only_compact_scan")
            # Within the very same BEGIN IMMEDIATE transaction as all prior
            # Squalincome writes. The next db.commit() is the only commit.
            compressed=compact_research.seal(
                db,compact_rows,full=(targets is None))
            result["priceOnlyResearch"]={
                "marketsAttempted":len(symbols),
                "batchStatus":compressed["status"],
                "storedMarkets":compressed["storedMarkets"],
                "eligiblePriceCandidates":compressed.get("eligiblePriceCandidates",0),
                "unknownObservations":compressed.get("unverifiableMarketObservations",0),
                "fullMarketDenominator":targets is None,
                "cotFilterAppliedToResearch":False,
                "extraBrokerRequests":0,
                "ordersEnabled":False,
                "alertsEnabled":False,
            }
        if price_only_research is not None:
            # Only aggregate allowlisted statuses; no quotes or account names.
            result["priceOnlyResearch"]={
                "marketsAttempted":len(symbols),
                "byState":dict(sorted(research_totals.items())),
                "cotFilterAppliedToResearch":False,
                "extraBrokerRequests":0,
                "ordersEnabled":False,
                "alertsEnabled":False,
            }
        if capture_frames and targets is not None:
            # Internal opt-in: expose only the H1 frame metadata that this
            # very same scan read, at the very same UTC instant. Never export
            # broker payloads or read the price database a second time.
            result["h1Frames"]={
                symbol:{"H1":frames_by_symbol.get(symbol,{}).get("H1")}
                for symbol in symbols}
        if compact_research is not None:
            db.commit()
        return result
    except BaseException:
        if compact_research is not None:
            db.rollback()
        raise
    finally:db.close()


def status(db_path,enabled=False,now=None):
    now=now or utcnow()
    db=connect(db_path)
    try:
        ensure_tables(db)
        baseline=db.execute("SELECT count(*) FROM squalincome_observations").fetchone()[0]
        total_events=db.execute("SELECT count(*) FROM squalincome_events").fetchone()[0]
        saved=db.execute("SELECT summary FROM squalincome_last_scan WHERE id=1").fetchone()
        diagnostics=None
        if saved:
            try:
                candidate=json.loads(saved[0])
                if isinstance(candidate,dict) and candidate.get("lastScanAt"):
                    diagnostics=candidate
            except (TypeError,ValueError):
                pass
        observations=db.execute(
            "SELECT symbol,state,report_date,price_time,price_state,observed_at "
            "FROM squalincome_observations ORDER BY symbol LIMIT 40").fetchall()
        history_total=db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0]
        history=[]
        for symbol in monitored_symbols():
            sampled=db.execute(
                "SELECT state,cot_side,price_side,h4_side,h1_side,m15_side,"
                "price_state,report_date,price_time,observed_at,cot_weekly,"
                "cot_sustained,origin,event_type FROM squalincome_history"
                " WHERE symbol=? ORDER BY id DESC LIMIT ?",
                (symbol,HISTORY_API_PER_SYMBOL)).fetchall()
            for record in reversed(sampled):
                entry=dict(zip(("state","cotSide","priceSide","h4Side","h1Side","m15Side",
                      "priceState","reportDate","priceTime","observedAt","cotWeekly",
                      "cotSustained","origin","eventType"),record))
                history.append({"symbol":symbol,**entry})
        events=db.execute("SELECT symbol,event_type,side,report_date,price_time,observed_at,detail "
            "FROM squalincome_events ORDER BY id DESC LIMIT 20").fetchall()
        return {"schema":"remura-squalincome-monitor-v1","enabled":bool(enabled),
                "mode":"observation_only","notificationsEnabled":False,
                "trackedMarkets":len(monitored_symbols()),"baselines":baseline,
                "eventsTotal":total_events,"diagnostics":diagnostics,
                "historyTotal":history_total,"history":history,
                "observations":[dict(zip(("symbol","state","reportDate","priceTime",
                                         "priceState","observedAt"),record))
                                for record in observations if record[0] in monitored_symbols()],
                "lastEvents":[dict(zip(("symbol","eventType","side","reportDate","priceTime","observedAt","detail"),r))
                              for r in events],
                "serverTime":now.isoformat()}
    finally:db.close()
