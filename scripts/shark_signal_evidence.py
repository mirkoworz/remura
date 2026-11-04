"""REMURA Track B: prospective link between genuine Squalincome and COT versions.

OFFLINE PROTOTYPE ONLY; never imported by LIVE. Enable only after coordinated
release with Track A, SQLite backup/restore/rollback and private cost audit.

Integration contract: with db: ... INSERT real squalincome_history row ...
capture(db, history_id=cursor.lastrowid), in THAT SAME transaction BEFORE commit.
The COT source, prior witness and new linkage are therefore one coherent SQLite
snapshot. A previously inserted row or post-facto historical scan fails closed.
No network, no broker calls, no order/notification, no raw OHLC or broker IDs.

The witness and original COT source are LOCAL observations. This is evidence
of what REMURA's database contained, NOT independent CFTC release proof,
original H1 quality, executed order volume or statistically proven edge.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_universe_lineage as universe

SCHEMA = "remura-signal-cot-link-v1"
TABLE = "research_squalincome_cot_links"
ALG = "squalincome-v162-cot-context-prospective"
UTC = timezone.utc
MAX_OBSERVATION_DELAY = timedelta(seconds=30)
MAX_CLOSE_DELAY = timedelta(hours=3)
MAX_COT_AGE_DAYS = 14
MAX_LINKS = 15000
MIN_COT_MOVE = 0.45


def ensure_schema(db):
    """Opt-in future release only. Never run this migration on current LIVE."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            symbol TEXT NOT NULL,
            cot_week TEXT NOT NULL,
            price_closed_at TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            linked_at TEXT NOT NULL,
            cot_side INTEGER NOT NULL CHECK(cot_side IN (-1,1)),
            price_state TEXT NOT NULL CHECK(price_state IN ('watch','partial','confirmed')),
            source_version_evidence TEXT NOT NULL,
            evidence_digest TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            PRIMARY KEY(symbol,cot_week,price_closed_at)
        )""")
        for kind in ("UPDATE", "DELETE"):
            db.execute(
                f"CREATE TRIGGER IF NOT EXISTS research_squalincome_links_no_{kind.lower()} "
                f"BEFORE {kind} ON {TABLE} "
                "BEGIN SELECT RAISE(ABORT, 'append_only'); END")


def _report(db, ds, code, report_week):
    row = db.execute(
        "SELECT oi,first_long,first_short,second_long,second_short "
        "FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
        (ds,code,report_week)).fetchone()
    if row is None:
        raise ValueError("cot_source_week_missing")
    digest = witness._digest(row)  # independently validates finite CFTC figures
    oi, first_long, first_short, second_long, second_short = row
    return digest, (100*(first_long-first_short)/oi,
                    100*(second_long-second_short)/oi)


def _proof(db, ds, code, report_week, digest, observed):
    """A LOCAL digest must have been recorded BEFORE the genuine signal."""
    matches = db.execute(
        f"SELECT witnessed_at FROM {witness.TABLE} "
        "WHERE dataset=? AND code=? AND report_date=? AND value_digest=?",
        (ds, code, report_week, digest)).fetchall()
    if len(matches) != 1:
        raise ValueError("matching_cot_witness_missing")
    instant = witness._parse(matches[0][0])
    if instant > observed:
        raise ValueError("cot_value_witness_is_future")
    return instant


def _legs(db, symbol, cot_week, observed):
    mapping = universe.contracts(symbol)
    if symbol not in witness.CATALOG or mapping is None:
        raise ValueError("unmapped_market")
    _, legs = mapping
    current = date.fromisoformat(cot_week)
    if current.isoformat() != cot_week or not 0 <= (observed.date()-current).days <= MAX_COT_AGE_DAYS:
        raise ValueError("cot_report_not_recent")
    # Precisely select the newest common prior date, not a later backfill.
    allowed_prior = [
        (current-timedelta(days=d)).isoformat() for d in range(6,11)
    ]
    valid_priors = []
    for previous in allowed_prior:
        if all(db.execute(
                "SELECT 1 FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
                (ds,code,previous)).fetchone() for ds,code in legs):
            valid_priors.append(previous)
    if not valid_priors:
        raise ValueError("cot_prior_week_not_present")
    previous = max(valid_priors)
    # Scan latest common week: the live COT view uses the *newest* compatible
    # common report, not a conveniently selected older report.
    src = witness._source(db, observed)
    common_dates = None
    for ds,code in legs:
        dates = {week for (d,c,week) in src if (d,c)==(ds,code)}
        common_dates = dates if common_dates is None else common_dates & dates
    if not common_dates or max(common_dates) != cot_week:
        raise ValueError("cot_signal_week_not_latest_common")
    report = {}
    for ds,code in legs:
        report[(ds,code)] = {}
        for week in (previous,cot_week):
            digest,positions = _report(db, ds, code, week)
            stamped = _proof(db,ds,code,week,digest,observed)
            report[(ds,code)][week] = positions
            report[(ds,code)][(week,"proof")] = {
                "dataset":ds, "code":code, "week":week,
                "digest":digest, "witnessed":witness._iso(stamped)
            }
    return legs, previous, report


def _live_side(symbol, legs, week, previous, report):
    """Reproduce the v1.62 cot_view weekly side, not infer from outcome PnL."""
    def composite(day):
        first=second=0.0
        for ds,code in legs:
            a,b=report[(ds,code)][day]
            sign=-1 if symbol not in universe.DIRECT and symbol[3:] != "USD" and (
                len(legs)==1 or code==universe.FX_CODES.get(symbol[3:])) else 1
            first+=sign*a
            second+=sign*b
        return first, second
    olda,oldb=composite(previous)
    newa,newb=composite(week)
    disagg = symbol in universe.DIRECT and universe.DIRECT[symbol][0] == "disagg"
    spec_delta=(newa-olda) if disagg else (newb-oldb)
    other_delta=(newb-oldb) if disagg else (newa-olda)
    side=1 if spec_delta>MIN_COT_MOVE else -1 if spec_delta < -MIN_COT_MOVE else 0
    opposed=not disagg and bool(side) and (
        other_delta>MIN_COT_MOVE if side<0 else other_delta < -MIN_COT_MOVE
    )
    if not side or opposed:
        raise ValueError("live_cot_direction_conflict")
    return side,round(spec_delta,4)


def capture(db, *, history_id, clock=None):
    """Link a JUST-INSERTED authentic observation inside the caller transaction.

    The production caller MUST take clock from the system clock after the
    accepted Squalincome insert and call before COMMIT, never in a replay.
    The injectable clock exists solely for synthetic unit tests.
    """
    if (not isinstance(db,sqlite3.Connection) or not db.in_transaction):
        raise ValueError("live_observation_transaction_required")
    if type(history_id) is not int or history_id <= 0:
        raise ValueError("original_history_id_required")
    now = witness._clock(clock)
    row = db.execute(
        "SELECT symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin "
        "FROM squalincome_history WHERE id=?", (history_id,)).fetchone()
    if row is None:
        raise ValueError("authentic_history_row_absent")
    (symbol,state,side,price_side,h4,h1,m15,price_state,
     cot_week,closed_at,observed_at,weekly,origin) = row
    observed = witness._parse(observed_at)
    closed = witness._parse(closed_at)
    if (not observed <= now <= observed+MAX_OBSERVATION_DELAY
            or not closed <= observed or observed-closed > MAX_CLOSE_DELAY
            or closed.second or closed.microsecond
            or closed.minute % 15  # expected M15 CLOSE boundary UTC
            or origin not in ("baseline","first_after_upgrade","update")
            or state not in ("aligned","divergent")
            or type(side) is not int or side not in (-1,1)
            or type(price_side) is not int or price_side not in (-1,1)
            or state != ("aligned" if side==price_side else "divergent")
            or any(type(x) is not int or x not in (-1,1) for x in (h1,h4))
            or type(m15) is not int or m15 not in (-1,0,1)
            or h1!=h4 or h1!=price_side
            or (price_state in ("partial","confirmed") and m15 != price_side)
            or price_state not in ("watch","partial","confirmed")
            or type(weekly) not in (float,int) or not math.isfinite(weekly)):
        raise ValueError("signal_observation_not_new_or_invalid")
    legs, previous, reports = _legs(db,symbol,cot_week,observed)
    actual_side,actual_delta = _live_side(symbol,legs,cot_week,previous,reports)
    if actual_side != side or not math.isclose(float(weekly),actual_delta,abs_tol=.00011):
        raise ValueError("original_signal_does_not_match_present_cot")
    versions = []
    for ds,code in legs:
        for week in (previous,cot_week):
            versions.append(reports[(ds,code)][(week,"proof")])
    versions.sort(key=lambda x:(x["dataset"],x["code"],x["week"]))
    evidence_json=json.dumps(versions,sort_keys=True,separators=(",",":"))
    if len(evidence_json)>1700 or len(versions) not in (2,4):
        raise ValueError("unbounded_evidence")
    evidence_digest=hashlib.sha256(evidence_json.encode()).hexdigest()
    # A duplicate is a logical error: the live unique history row must be
    # inserted once, and no future event may replace its original evidence.
    # Production integration MUST check history INSERT rowcount == 1 and only
    # then call this function before committing the transaction.
    if db.execute(
            f"SELECT 1 FROM {TABLE} WHERE symbol=? AND cot_week=? "
            "AND price_closed_at=?", (symbol,cot_week,closed_at)).fetchone():
        raise ValueError("observation_evidence_already_recorded")
    total=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    if total>=MAX_LINKS:
        raise ValueError("evidence_capacity_exceeded")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(symbol,cot_week,price_closed_at,observed_at,linked_at,"
        "cot_side,price_state,source_version_evidence,evidence_digest,algorithm) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (symbol,cot_week,closed_at,observed_at,witness._iso(now),
         side,price_state,evidence_json,evidence_digest,ALG))
    return {
        "schema":SCHEMA,"status":"FUTURE_OBSERVATION_CERTIFIED_LOCALLY",
        "cotReportsVersionedForSignal":len(versions),
        "originalObservationTimestampPreserved":True,
        "originalSignalValuesMatched":True,
        "historicalH1QualityIndependentlyAttested":False,
        "realAggressorVolumeKnown":False,
        "tradingEdge":"NOT_ESTABLISHED",
        "brokerCalls":0,"notificationsEnabled":False,"ordersEnabled":False,
    }


def capture_optional(db, *, history_id, clock=None):
    """For a coordinated future opt-in: keep original monitoring operational.

    Missing/late/revised COT evidence returns N/D and records NO evidence,
    rather than rolling back an authentic Squalincome observation. The caller
    must still check its INSERT rowcount==1 before calling. Unexpected SQLite
    errors MUST propagate so operational DB failures cannot be concealed.
    """
    if not isinstance(db, sqlite3.Connection) or not db.in_transaction:
        raise ValueError("caller_transaction_required")
    try:
        return capture(db, history_id=history_id, clock=clock)
    except ValueError:
        return {
            "schema": SCHEMA, "status": "COT_PROVENANCE_NOT_VERIFIABLE",
            "cotReportsVersionedForSignal": 0,
            "originalSignalValuesMatched": False,
            "tradingEdge": "NOT_ESTABLISHED",
            "brokerCalls": 0, "notificationsEnabled": False,
            "ordersEnabled": False,
        }


def summarize(db):
    """Only aggregate counters; never print private event clock or broker."""
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    by_market=db.execute(
        f"SELECT symbol,count(*) FROM {TABLE} GROUP BY symbol").fetchall()
    return {"schema":SCHEMA,"total":sum(n for _,n in by_market),
            "marketsWithEvidence":len(by_market),
            "realTradingEdgeEstablished":False,"brokerCalls":0,
            "notificationsEnabled":False}
