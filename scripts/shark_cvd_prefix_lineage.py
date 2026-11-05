"""REMURA Track B: prospective, bounded UTC M15-session prefix proofs.

A CVD event may be detected from an EARLIER price document. When later
Squalincome observation has appended new bars, entire-document SHA cannot
match. Instead compare a keyed proof of the *identical causal prefix* from
UTC session midnight through the last M15 candle closed when CVD was detected.
This is a separate evidence tier, never called exact full-source equivalence.

Only immutable proof metadata is saved: private HMAC(prefix SHA) in the CVD
database, SHA(prefix) at the original Squalincome observation. Neither is
retroactively manufactured from today's mutable prices.

The original detector rerun and full-document HMAC remain mandatory for
private CVD binding. M15 prefixes must be complete from midnight, contiguous
with valid tick volume, broker/source-identical, capped at 96 bars. Other
timeframes remain subject to their own independent source checks. A matching
M15 prefix does NOT prove the full OHLC/H1/H4 documents are identical, that
real aggressor flow was measured or that predictive trading edge exists.

OFFLINE research only; no server import, new API, secret storage or LIVE DB.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import json
import sqlite3

from scripts import cvd_divergence as detector
from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_asof_evidence as price

PRIVATE_TABLE = "research_cvd_m15_prefix_proofs"
MAIN_TABLE = "research_squalincome_m15_prefix_proofs"
VERSION = "remura-m15-session-prefix-lineage-v1"
DOMAIN = b"remura-cvd-session-prefix-v1|"
STEP = timedelta(minutes=15)
MAX_CANDLES = 96
MAX_CUTOFFS = 7
MAX_MAIN_ROWS = 15000
PILOT = frozenset(("EURUSD","XAUUSD"))
TRIGGERS = {
    PRIVATE_TABLE: ("research_cvd_prefix_no_update",
                    "research_cvd_prefix_no_delete"),
    MAIN_TABLE: ("research_signal_prefix_no_update",
                 "research_signal_prefix_no_delete"),
}


def _protected(db,table):
    exists=db.execute("SELECT 1 FROM sqlite_master WHERE type='table' "
                      "AND name=?", (table,)).fetchone()
    if not exists:
        return False
    have={x[0] for x in db.execute(
        "SELECT name FROM sqlite_master WHERE type='trigger' "
        "AND tbl_name=?", (table,))}
    if not set(TRIGGERS[table]).issubset(have):
        raise ValueError("prefix_immutable_triggers_missing")
    return True


def _private_schema(db):
    db.execute(f"""CREATE TABLE IF NOT EXISTS {PRIVATE_TABLE} (
        event_key TEXT PRIMARY KEY,
        m15_closed_at TEXT NOT NULL,
        prefix_hmac TEXT NOT NULL,
        bound_at TEXT NOT NULL,
        schema_version TEXT NOT NULL CHECK(schema_version='{VERSION}'),
        FOREIGN KEY(event_key) REFERENCES research_cvd_observations(key)
    )""")
    for op,name in zip(("UPDATE","DELETE"),TRIGGERS[PRIVATE_TABLE]):
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
            BEFORE {op} ON {PRIVATE_TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_cvd_prefix_proof'); END""")


def _main_schema(db):
    db.execute(f"""CREATE TABLE IF NOT EXISTS {MAIN_TABLE} (
        symbol TEXT NOT NULL, report_date TEXT NOT NULL,
        price_time TEXT NOT NULL, observed_at TEXT NOT NULL,
        m15_closed_at TEXT NOT NULL, prefix_sha256 TEXT NOT NULL,
        recorded_at TEXT NOT NULL,
        schema_version TEXT NOT NULL CHECK(schema_version='{VERSION}'),
        PRIMARY KEY(symbol,report_date,price_time,m15_closed_at)
    )""")
    for op,name in zip(("UPDATE","DELETE"),TRIGGERS[MAIN_TABLE]):
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
            BEFORE {op} ON {MAIN_TABLE}
            BEGIN SELECT RAISE(ABORT,'immutable_signal_prefix_proof'); END""")


def _sha(doc, cutoff):
    """SHA of the precise M15 UTC-session prefix known in ORIGINAL document.

    Truncate by known CLOSED candle timestamp, not by a later cutoff or
    candle-open guessed from another market. Includes broker mapping.
    """
    if (not isinstance(doc,dict) or doc.get("symbol") not in PILOT
            or doc.get("provider")!="ctrader"
            or not isinstance(doc.get("providerSymbol"),str)
            or not doc["providerSymbol"].strip()
            or doc.get("timezone")!="UTC"
            or doc.get("sourceTimeframe")!="M15"
            or not isinstance(doc.get("timeframes"),dict)):
        raise ValueError("prefix_source_or_market_unverified")
    latest=witness._parse(doc.get("lastComplete"))+STEP
    end=witness._parse(cutoff)
    if (end>latest or end.minute%15 or end.second or end.microsecond
            or end.hour==0 and end.minute==0):
        raise ValueError("prefix_cutoff_invalid")
    rows=price._bars(doc["timeframes"].get("M15"),900,4320)
    if rows[-1][0]+STEP!=latest:
        raise ValueError("prefix_last_closed_mismatch")
    session_start=end.replace(hour=0,minute=0,second=0,microsecond=0)
    picked=[(t,bar) for t,bar in rows if session_start<=t and t+STEP<=end]
    count=int((end-session_start).total_seconds()//900)
    if (len(picked)!=count or not 1<=count<=MAX_CANDLES
            or picked[0][0]!=session_start
            or picked[-1][0]+STEP!=end):
        raise ValueError("prefix_session_incomplete")
    normalized=[]
    for i,(at,row) in enumerate(picked):
        if at!=session_start+i*STEP or type(row.get("v")) is not int:
            raise ValueError("prefix_session_gap_or_tick_missing")
        normalized.append([
            witness._iso(at),
            *(row[k] for k in ("o","h","l","c","v")),
        ])
    raw=json.dumps({
        "algorithm":detector.VERSION,"symbol":doc["symbol"],
        "provider":"ctrader","providerSymbol":doc["providerSymbol"],
        "sessionUtc":session_start.date().isoformat(),
        "endClosedAt":witness._iso(end),
        "m15":normalized,
    },sort_keys=True,separators=(",",":"),ensure_ascii=True)
    return hashlib.sha256(raw.encode()).hexdigest()


def _mac(secret,sha):
    if not isinstance(secret,bytes) or len(secret)<16:
        raise ValueError("stable_private_hmac_secret_required")
    if not isinstance(sha,str) or len(sha)!=64 or any(
            ch not in "0123456789abcdef" for ch in sha):
        raise ValueError("invalid_prefix_sha")
    return hmac.new(secret,DOMAIN+sha.encode(),hashlib.sha256).hexdigest()


def bind_private(db, *, event_key, original_doc, detected_at, secret):
    """Add to the SAME ongoing insert transaction as the NEW CVD event.

    Caller has ALREADY rerun detector and verified entire event, so the
    prefix here cannot be used to bless an event on its own.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("new_cvd_event_transaction_required")
    detected=witness._clock(detected_at)
    end=witness._parse(original_doc["lastComplete"])+STEP
    if end>detected:
        raise ValueError("private_prefix_future_candle")
    digest=_sha(original_doc,witness._iso(end))
    _private_schema(db)
    if not _protected(db,PRIVATE_TABLE):
        raise ValueError("private_prefix_proof_unavailable")
    if db.execute(f"SELECT 1 FROM {PRIVATE_TABLE} WHERE event_key=?",
                  (event_key,)).fetchone():
        raise ValueError("private_prefix_already_bound")
    db.execute(
        f"INSERT INTO {PRIVATE_TABLE} "
        "(event_key,m15_closed_at,prefix_hmac,bound_at,schema_version) "
        "VALUES (?,?,?,?,?)",
        (event_key,witness._iso(end),_mac(secret,digest),
         witness._iso(detected),VERSION))


def capture_main(db, *, history_id, original_doc, clock=None):
    """Write prefixes only inside the ORIGINAL signal+source transaction.

    Must follow genuine price.capture and cot.capture for the SAME new
    history ID. Never call on historical/replayed signals. Does not look
    into private CVD DB: emits up to 7 bounded candidate cutoffs so a later
    offline auditor can compare without involving a second writer.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("original_signal_transaction_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("original_signal_history_id_required")
    # The original history insert was verified by observation_bundle.record
    # BEFORE the two proof INSERTs. Those inserts change last_insert_rowid,
    # so require the matching original row+both proofs instead of incorrectly
    # expecting last_insert_rowid to still point at history_id.
    now=witness._clock(clock)
    row=db.execute(
        "SELECT symbol,report_date,price_time,observed_at "
        "FROM squalincome_history WHERE id=?",(history_id,)).fetchone()
    if not row:
        raise ValueError("original_signal_row_missing")
    sym,week,closed,observed_at=row
    if sym not in PILOT:
        return {"status":"NON_PILOT_NO_PREFIX","prefixCount":0}
    from scripts import shark_signal_evidence as cot
    from scripts import shark_price_asof_evidence as price_proof
    if not db.execute(
            f"SELECT 1 FROM {cot.TABLE} "
            "WHERE symbol=? AND cot_week=? AND price_closed_at=? "
            "AND observed_at=?",(sym,week,closed,observed_at)).fetchone():
        raise ValueError("cot_proof_missing_before_prefix")
    proof=db.execute(
        f"SELECT source_document_sha256,observed_at,witnessed_at "
        f"FROM {price_proof.TABLE} WHERE symbol=? AND report_date=? "
        "AND price_time=?",(sym,week,closed)).fetchone()
    from scripts import shark_cvd_source_lineage as full
    if (not proof or proof[1]!=observed_at
            or proof[0]!=full._document_sha(original_doc)
            or not witness._parse(observed_at)<=witness._parse(
                proof[2])<=now<=witness._parse(observed_at)+timedelta(seconds=30)
            or witness._parse(closed)!=witness._parse(
                original_doc["lastComplete"])+STEP):
        raise ValueError("original_price_source_proof_mismatch")
    end=witness._parse(closed)
    start_day=end.replace(hour=0,minute=0,second=0,microsecond=0)
    candidate=[]
    for i in range(MAX_CUTOFFS):
        cutoff=end-i*STEP
        if cutoff<=start_day:
            break
        candidate.append((witness._iso(cutoff),_sha(original_doc,
                                                 witness._iso(cutoff))))
    if not candidate:
        raise ValueError("empty_m15_prefix_window")
    _main_schema(db)
    if not _protected(db,MAIN_TABLE):
        raise ValueError("main_prefix_proof_unavailable")
    if db.execute(f"SELECT count(*) FROM {MAIN_TABLE}").fetchone()[0]+len(
            candidate)>MAX_MAIN_ROWS:
        raise ValueError("main_prefix_archive_capacity")
    db.executemany(
        f"INSERT INTO {MAIN_TABLE} "
        "(symbol,report_date,price_time,observed_at,m15_closed_at,"
        "prefix_sha256,recorded_at,schema_version) VALUES (?,?,?,?,?,?,?,?)",
        [(sym,week,closed,observed_at,cutoff,digest,
          witness._iso(now),VERSION) for cutoff,digest in candidate])
    return {"status":"FUTURE_ORIGINAL_M15_PREFIXES_RECORDED",
            "prefixCount":len(candidate),"brokerCalls":0,
            "tradingEdgeEstablished":False}


def verified_main_prefixes(db, *, pairs, as_of):
    """Return bounded PRIVATE internal digest map for pre-verified COT pairs.

    Never emitted in an HTTP response or serialized into public summaries.
    Pair identity is supplied by the exact original-observation COT+OHLC
    auditor, NOT an unverified symbol/date lookup. No source data fetched.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now=witness._parse(as_of)
    if not _protected(db,MAIN_TABLE):
        return None
    accepted={(s,w,c,o) for s,w,c,o,_,_ in pairs}
    rows=db.execute(
        f"SELECT symbol,report_date,price_time,observed_at,"
        f"m15_closed_at,prefix_sha256,recorded_at,schema_version "
        f"FROM {MAIN_TABLE} ORDER BY observed_at,symbol,m15_closed_at "
        "LIMIT ?",(MAX_MAIN_ROWS+1,)).fetchall()
    if len(rows)>MAX_MAIN_ROWS:
        raise ValueError("main_prefix_archive_unbounded")
    result={}
    for sym,week,closed,observed,cutoff,sha,recorded,version in rows:
        key=(sym,week,closed,observed)
        if key not in accepted:
            continue
        event_clock=witness._parse(observed)
        sealed=witness._parse(recorded)
        cutoff_clock=witness._parse(cutoff)
        last=witness._parse(closed)
        if (version!=VERSION or not isinstance(sha,str)
                or len(sha)!=64
                or any(ch not in "0123456789abcdef" for ch in sha)
                or not event_clock<=sealed<=event_clock+timedelta(seconds=30)
                or cutoff_clock>last
                or not 0<= (last-cutoff_clock).total_seconds()<=90*60
                or cutoff_clock.minute%15 or cutoff_clock.second
                or cutoff_clock.microsecond):
            raise ValueError("main_prefix_provenance_or_clock_invalid")
        # A row only becomes visible as-of when written; no future
        # main proof can be used to re-qualify an earlier report.
        if sealed>now:
            continue
        index=(*key,cutoff)
        if index in result:
            raise ValueError("duplicate_original_prefix_proof")
        result[index]=sha
    return result


def verified_private_prefixes(db, *, events, as_of):
    """Return event_key -> (cutoff, HMAC) for ORIGINAL new private events.

    A proof not accompanied by the original full-document HMAC is rejected;
    neither table may be supplied retroactively or revised.
    """
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now=witness._parse(as_of)
    if not _protected(db,PRIVATE_TABLE):
        return None
    from scripts import shark_cvd_source_lineage as full
    if not full._has_protected_schema(db):
        raise ValueError("private_full_source_proof_required")
    full_rows=db.execute(
        f"SELECT event_key,document_hmac,bound_at,algorithm "
        f"FROM {full.TABLE}").fetchall()
    full_keys={}
    for key,digest,at,algorithm in full_rows:
        if (algorithm!=full.ALG or not isinstance(digest,str)
                or len(digest)!=64 or any(
                    ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError("private_full_document_binding_corrupt")
        full_keys[key]=at
    keys={row[0]:row for row in events}
    rows=db.execute(
        f"SELECT event_key,m15_closed_at,prefix_hmac,bound_at,schema_version "
        f"FROM {PRIVATE_TABLE} ORDER BY event_key LIMIT ?",
        (len(keys)+1,)).fetchall()
    # The table is bounded by the original CVD MAX_EVENTS upper limit,
    # including entries outside this audit's as-of window.
    if len(rows)>len(keys):
        # Old events outside the current window may legitimately exist:
        # caller must supply full population or use an independent max cap.
        rows=db.execute(
            f"SELECT event_key,m15_closed_at,prefix_hmac,bound_at,schema_version "
            f"FROM {PRIVATE_TABLE} ORDER BY event_key LIMIT 4097").fetchall()
        if len(rows)>4096:
            raise ValueError("private_prefix_archive_unbounded")
    result={}
    for key,closed,mac,bound,version in rows:
        original=keys.get(key)
        if original is None:
            continue
        detected=witness._parse(original[4])
        confirmed=witness._parse(original[3])
        cutoff=witness._parse(closed)
        bound_at=witness._parse(bound)
        if (version!=VERSION or not isinstance(mac,str)
                or len(mac)!=64
                or any(ch not in "0123456789abcdef" for ch in mac)
                or bound_at!=detected
                or full_keys.get(key)!=bound
                or not confirmed<=cutoff<=detected
                or detected-cutoff>timedelta(minutes=90)
                or cutoff.minute%15 or cutoff.second or cutoff.microsecond):
            raise ValueError("private_prefix_binding_not_from_event")
        if bound_at>now:
            continue
        result[key]=(closed,mac)
    return result
