"""Track B — FUTURE-ONLY COT value-presence attestation prototype.

This module is not called/imported by production REMURA. Integrating it requires
a coordinated, explicitly reviewed future release (schema backup/restore,
timing, concurrency tests, banner/version). No historic first_seen is altered.

Rationale: REMURA v1.62 cot_first_seen is intentionally missing for reports
that existed when first-seen recording began. We cannot backdate the original
capture, but CAN attest that values are present NOW for observations occurring
AFTER an actual attestation. Storing a digest also reveals subsequent revisions.

Pure SQLite, no broker/CFTC request, no secrets, and no prices/account data.
The digest is evidence of a LOCAL value snapshot, not a CFTC signature, an
independent trusted timestamp, or immutable audit of an historic decision.
"""
from __future__ import annotations

from collections import Counter
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import sqlite3

from scripts import shark_universe_lineage as universe

SCHEMA = "remura-cot-prospective-attestation-v1"
TABLE = "research_cot_asof_attestations"
UTC = timezone.utc
MAX_REPORT_AGE_DAYS = 22
MAX_SOURCE_ROWS = 200
MAX_EVIDENCE_ROWS = 15000
DATASET_CODES = {
    "tff": frozenset((*universe.FX_CODES.values(), "13874A",
                      "209742", "124603", "098662")),
    "disagg": frozenset(("088691", "084691", "067651")),
}
CATALOG = tuple(sorted({
    *universe.DIRECT.keys(),
    *(left + right
      for left in (*universe.FX_CODES, "USD")
      for right in (*universe.FX_CODES, "USD")
      if left != right
      and (left == "USD" or right == "USD"
           or left in universe.FX_CODES and right in universe.FX_CODES))
}))


def _clock(clock=None):
    when = datetime.now(UTC) if clock is None else clock
    if (not isinstance(when, datetime) or when.tzinfo is None
            or when.utcoffset() != timedelta(0)):
        raise ValueError("utc_clock_required")
    return when.astimezone(UTC)


def _parse(value):
    if not isinstance(value, str) or len(value) > 48:
        raise ValueError("bad_datetime")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("bad_datetime") from exc
    if t.tzinfo is None or t.utcoffset() != timedelta(0):
        raise ValueError("utc_required")
    return t.astimezone(UTC)


def _iso(clock):
    return clock.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(row):
    """Fingerprint the ACTUAL six COT values, without persisting them twice."""
    if len(row) != 6:
        raise ValueError("wrong_cot_value_shape")
    fields = []
    for idx, v in enumerate(row):
        if type(v) not in (int, float) or not math.isfinite(v):
            raise ValueError("non_finite_cot_value")
        if not (0 < v <= 1e11 if idx == 0 else 0 <= v <= 1e11):
            raise ValueError("cot_value_out_of_bounds")
        fields.append(format(v, ".17g"))
    return hashlib.sha256(
        json.dumps(fields, separators=(",", ":"), ensure_ascii=True).encode()
    ).hexdigest()


def ensure_schema(db):
    """Explicit future-release opt-in. NEVER call against current LIVE."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE} (
            dataset TEXT NOT NULL CHECK(dataset IN ('tff', 'disagg')),
            code TEXT NOT NULL,
            report_date TEXT NOT NULL,
            value_digest TEXT NOT NULL,
            witnessed_at TEXT NOT NULL,
            evidence_kind TEXT NOT NULL CHECK(evidence_kind='observed_local_values'),
            PRIMARY KEY(dataset, code, report_date, value_digest)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_cot_asof_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT, 'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_cot_asof_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT, 'append_only'); END""")


def _source(db, now):
    """Read all matching, recent, presently persisted COT values without network."""
    tables = {name for (name,) in db.execute(
        "SELECT name FROM sqlite_master WHERE type='table'")}
    if "cot_reports" not in tables:
        raise ValueError("cot_source_missing")
    cutoff = (now.date() - timedelta(days=MAX_REPORT_AGE_DAYS)).isoformat()
    rows = db.execute(
        "SELECT dataset,code,report_date,oi,first_long,first_short,"
        "second_long,second_short FROM cot_reports WHERE report_date>=?",
        (cutoff,)).fetchall()
    if len(rows) > MAX_SOURCE_ROWS:
        raise ValueError("source_rows_over_limit")
    result={}
    for dataset,code,week,*values in rows:
        if dataset not in DATASET_CODES or code not in DATASET_CODES[dataset]:
            continue
        try:
            report_date = date.fromisoformat(week)
            if (report_date.isoformat()!=week or
                    report_date>now.date() or
                    now.date()-report_date>timedelta(days=MAX_REPORT_AGE_DAYS)):
                raise ValueError("bad_report_date")
            digest = _digest(values)
        except (TypeError,ValueError,OverflowError) as exc:
            raise ValueError("invalid_source_cot_values") from exc
        key=(dataset,code,week)
        if key in result:
            raise ValueError("duplicate_source_report")
        result[key]=digest
    return result


def witness(db, *, clock=None):
    """Record only evidence of what is present NOW, never inferred historic time.

    Caller must run exactly when COT values are observed; there is no request
    or ingest inside this method. Future integration should use the COT ingest
    transaction or immediately follow its successful commit.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now = _clock(clock)
    with db:
        before = db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
        if before>MAX_EVIDENCE_ROWS:
            raise ValueError("archive_capacity_exceeded")
        rows=_source(db, now)
        written=0
        for (dataset,code,week),digest in rows.items():
            existing=db.execute(
                f"SELECT 1 FROM {TABLE} WHERE dataset=? AND code=? "
                "AND report_date=? AND value_digest=?",
                (dataset,code,week,digest)).fetchone()
            if existing:
                continue
            if before+written>=MAX_EVIDENCE_ROWS:
                raise ValueError("archive_capacity_exceeded")
            cursor=db.execute(
                f"INSERT INTO {TABLE} "
                "(dataset,code,report_date,value_digest,witnessed_at,evidence_kind) "
                "VALUES (?,?,?,?,?,'observed_local_values')",
                (dataset,code,week,digest,_iso(now)))
            written += cursor.rowcount
    return {"schema":SCHEMA,"status":"FUTURE_ONLY_RESEARCH",
            "sourceValuesPresent":len(rows),"newWitnessRows":written,
            "estimatedTotalRows":before+written,
            "historicalFirstSeenModified":False,
            "newBrokerCalls":0,"tradingEdge":"NOT_ESTABLISHED"}


def readiness(db, *, as_of):
    """Descriptive eligibility of COT data NOW; not a historical signal audit.

    We require a witness of the SAME currently persisted values for the
    recent report and previous report for each leg. This rejects any values
    revised in COT cache but not yet re-witnessed at or before as_of.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now=_parse(as_of)
    rows=_source(db,now)
    proofs={}
    try:
        for ds,code,week,digest,stamp in db.execute(
                f"SELECT dataset,code,report_date,value_digest,witnessed_at "
                f"FROM {TABLE}"):
            t=_parse(stamp)
            if t>now:
                continue
            key=(ds,code,week,digest)
            proofs[key]=min(proofs.get(key,t),t)
    except sqlite3.OperationalError as exc:
        raise ValueError("witness_table_unavailable") from exc
    reasons=Counter()
    ready=0
    for symbol in CATALOG:
        spec=universe.contracts(symbol)
        if spec is None:
            continue
        _,legs=spec
        leg_weeks=[]
        for ds,code in legs:
            dates = [date.fromisoformat(week) for (kind,leg,week) in rows
                     if kind==ds and leg==code]
            leg_weeks.append(set(dates))
        common=set.intersection(*leg_weeks) if leg_weeks else set()
        if not common:
            reasons["missing_common_report_week"]+=1
            continue
        week=max(common)
        previous = [d for d in common if 6<=(week-d).days<=10]
        if not previous:
            reasons["no_two_consecutive_weeks"]+=1
            continue
        prior=max(previous)
        valid=True
        for ds,code in legs:
            for report in (week,prior):
                key=(ds,code,report.isoformat())
                digest=rows.get(key)
                if digest is None or (ds,code,report.isoformat(),digest) not in proofs:
                    reasons["source_values_not_yet_witnessed"]+=1
                    valid=False
                    break
            if not valid:
                break
        if valid:
            ready+=1
    return {
        "schema":SCHEMA,"status":"PROSPECTIVE_SOURCE_ONLY",
        "mappedMarketsReviewed":len(CATALOG),
        "marketsWithTwoWeeksAttested":ready,
        "marketsBlocked":len(CATALOG)-ready,
        "blockerCounts":dict(sorted(reasons.items())),
        "historicalEventsRetroactivelyQualified":False,
        "cotSourceValueVersionsAttestedLocally":True,
        "originalSignalValueDigestRecorded":False,
        "historicalIndependentOutOfSample":False,
        "edge":"NOT_ESTABLISHED","newBrokerCalls":0,
        "ordersEnabled":False,"notificationsEnabled":False,
    }
