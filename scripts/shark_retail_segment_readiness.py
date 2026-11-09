"""Track B OFFLINE: 28-week retail FIRST-SEEN partition rehearsal.

A hypothetical 14 x 14-day UTC layout follows the EXISTING frozen
12/8/8-week protocol without changing its fingerprint. It uses the current
unchanged per-SQLite caps: 4500 numeric rows, 15000 first-seen receipts.
A read-only auditor checks 14 *independent* synthetic SQLite shards, their
paired receipt/feature integrity and monotone source times across rollover.

NOT a sharded writer, original Squalincome source-of-truth, recovery plan,
cross-DB atomic transaction or live enablement. No Oracle, API, trade,
manual backup, provider authentication, scheduler or changes to LIVE code.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import math
import sqlite3

from scripts import shark_retail_preregistered_protocol as protocol
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric

SCHEMA="remura-track-b-retail-14day-segment-readiness-v1"
DAYS=14
EXPECTED_SEGMENTS=14
MARKETS=frozenset(("EURUSD","XAUUSD"))
UTC=timezone.utc


def _time(value):
    if type(value) is not str or len(value)>45:
        raise ValueError("explicit_bounded_utc_receipt_time_required")
    try:
        dt=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_original_utc_receipt_clock") from exc
    if dt.tzinfo is None or dt.utcoffset()!=timedelta(0):
        raise ValueError("non_utc_or_unaware_original_receipt_clock")
    return dt.astimezone(UTC)


def _iso(value):
    return value.isoformat().replace("+00:00","Z")


def plan(authorized_at=None,*,scenario_cycle_minutes=20):
    """Plan, not authorization: exactly 14 consecutive two-week intervals."""
    if (type(scenario_cycle_minutes) is not int
            or not 1<=scenario_cycle_minutes<=120):
        raise ValueError("bounded_positive_integer_scenario_cycle_required")
    cal=protocol.frozen_calendar(authorized_at)
    if cal["status"]=="BLOCKED_NO_AUTHORIZED_RETAIL_START":
        return {
            "schema":SCHEMA,"status":"BLOCKED_NO_AUTHORIZED_RETAIL_START",
            "segments":[],"liveAuthorized":False,
            "retailFirstSeenActivated":False,"newApiCalls":0
        }
    if cal["protocolSha256"]!=protocol.FROZEN_RULES_SHA256:
        raise ValueError("frozen_retail_calendar_mismatch")
    start=_time(cal["trainStartUtc"])
    train=_time(cal["validationStartUtc"])
    val=_time(cal["testStartUtc"])
    end=_time(cal["testEndUtc"])
    if (end-start!=timedelta(days=196)
            or train-start!=timedelta(weeks=12)
            or val-train!=timedelta(weeks=8)):
        raise ValueError("frozen_retail_folds_changed")
    expected=2*math.ceil(DAYS*24*60/scenario_cycle_minutes)
    hard=min(retail.MAX_ROWS,numeric.MAX_FEATURE_ROWS)
    fits=expected<=hard
    segments=[]
    for i in range(EXPECTED_SEGMENTS):
        begin=start+timedelta(days=DAYS*i)
        finish=begin+timedelta(days=DAYS)
        fold="train" if i<6 else "validation" if i<10 else "test"
        segments.append({
            "number":i+1,"fold":fold,"startUtc":_iso(begin),
            "endExclusiveUtc":_iso(finish),
            "scenarioTwoMarketRows":expected,
            "firstSeenHardRowLimit":retail.MAX_ROWS,
            "numericHardRowLimit":numeric.MAX_FEATURE_ROWS,
            "numericHeadroomRows":numeric.MAX_FEATURE_ROWS-expected,
        })
    if _time(segments[-1]["endExclusiveUtc"])!=end:
        raise ValueError("retail_partition_not_full_28_weeks")
    return {
        "schema":SCHEMA,
        "status":("OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO"
                  if fits else "NO_GO_SEGMENT_SCENARIO_EXCEEDS_HARD_CAP"),
        "frozenProtocolSha256":protocol.FROZEN_RULES_SHA256,
        "startRule":"HYPOTHETICAL_FROZEN_CALENDAR_NOT_AUTHORIZATION",
        "segments":segments,
        "scenarioCollectorMinutes":scenario_cycle_minutes,
        "scenarioAllSegmentsRows":EXPECTED_SEGMENTS*expected,
        "segmentsNeeded":EXPECTED_SEGMENTS,
        "coversFrozen196Days":True,
        "oneDatabasePerSegmentRequiredButNotImplemented":True,
        "crossSegmentGlobalLastSeenProofMissing":True,
        "crossDatabaseSqualincomeAtomicLinkMissing":True,
        "realSqliteStorageBytesUnknown":True,
        "offHostRestoreVerified":False,
        "automaticRolloverEnabled":False,
        "retailFirstSeenActivated":False,
        "liveAuthorized":False,
        "costOrEdgeProven":False,
        "newApiCalls":0,
    }


def audit_shards(authorized_at,shards,*,scenario_cycle_minutes=20):
    """READ-ONLY integrity proof on 14 existing test segment databases.

    Cross-segment monotonicity is checked on provided rows, not authenticated
    by a source ledger or external clock. Empty periods are NOT counted as
    covered market observations. All problems fail closed.
    """
    layout=plan(authorized_at,scenario_cycle_minutes=scenario_cycle_minutes)
    if layout["status"]!="OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO":
        raise ValueError("partition_layout_not_capacity_safe")
    if type(shards) not in (tuple,list) or len(shards)!=EXPECTED_SEGMENTS:
        raise ValueError("fourteen_explicit_readonly_shards_required")
    # Complete preflight before processing the first receipt.
    for db in shards:
        if (not isinstance(db,sqlite3.Connection)
                or db.in_transaction or
                db.execute("PRAGMA query_only").fetchone()[0]!=1):
            raise ValueError("readonly_clean_shard_required")
        retail.require_schema(db)
        numeric.require_schema(db)
    last={symbol:None for symbol in MARKETS}
    total_receipts=0
    total_numeric=0
    populated=0
    for slot,db in zip(layout["segments"],shards):
        start=_time(slot["startUtc"])
        end=_time(slot["endExclusiveUtc"])
        rows=db.execute(
            f"SELECT id,symbol,source_updated_at,original_read_at,"
            f"recorded_at,numeric_sha256,algorithm FROM {retail.TABLE}"
            " ORDER BY id").fetchall()
        features=db.execute(
            f"SELECT receipt_id,symbol,original_sha256,recorded_at,"
            f"long_pct,short_pct,long_lots,short_lots,"
            f"long_positions,short_positions,features_sha256,algorithm"
            f" FROM {numeric.TABLE}").fetchall()
        if (len(rows)>retail.MAX_ROWS or
                len(features)>numeric.MAX_FEATURE_ROWS
                or len(rows)!=len(features)):
            raise ValueError("partition_receipt_or_numeric_capacity_broken")
        if db.execute(f"SELECT count(*) FROM {retail.LINK}").fetchone()[0]:
            raise ValueError("cross_database_decision_link_not_certified")
        by_id={row[0]:row for row in features}
        if len(by_id)!=len(features):
            raise ValueError("duplicate_numeric_feature_receipt_key")
        batches={}
        for ident,symbol,source_clock,read_clock,recorded_clock,sha,alg in rows:
            if (type(ident) is not int or ident<=0 or
                    symbol not in MARKETS or alg!=retail.ALG or
                    type(sha) is not str or len(sha)!=64):
                raise ValueError("invalid_segment_original_receipt")
            updated=_time(source_clock)
            read=_time(read_clock)
            recorded=_time(recorded_clock)
            if (not start<=recorded<end or not updated<=read<=recorded
                    or recorded-read>retail.WRITE_GRACE
                    or read-updated>retail.MAX_AGE
                    or last[symbol] is not None and updated<=last[symbol]):
                raise ValueError("noncausal_or_cross_segment_backdated_receipt")
            last[symbol]=updated
            batches.setdefault(recorded_clock,[]).append(symbol)
            feature=by_id.get(ident)
            if (feature is None or feature[1]!=symbol or feature[2]!=sha
                    or _time(feature[3])!=recorded
                    or feature[11]!=numeric.ALG):
                raise ValueError("numeric_row_not_bound_to_original_first_seen")
            six=dict(zip(numeric.FIELDS,feature[4:10]))
            try:
                clean=numeric._six(six)
                digest=numeric._hash(symbol,sha,clean)
            except (TypeError,ValueError) as exc:
                raise ValueError("malformed_original_numeric_six") from exc
            if feature[10]!=digest:
                raise ValueError("numeric_sha256_not_bound_to_original_values")
        if any(len(symbols)!=2 or set(symbols)!=MARKETS
               for symbols in batches.values()):
            raise ValueError("partial_pair_or_duplicate_original_retail_batch")
        total_receipts+=len(rows)
        total_numeric+=len(features)
        populated+=int(bool(rows))
    return {
        "schema":SCHEMA,
        "status":"OFFLINE_SHARD_SCHEMA_AND_BOUNDARIES_VERIFIED_NOT_LIVE_GO",
        "shardsInspected":EXPECTED_SEGMENTS,
        "populatedShardCount":populated,
        "locallyRevalidatedRetailReceipts":total_receipts,
        "locallyRevalidatedNumericRows":total_numeric,
        "allOriginalBatchesPaired":True,
        "crossSegmentSourceTimestampsIncreasing":True,
        "complete28WeekEnrollmentProven":False,
        "actualSourceClockAuthenticated":False,
        "crossDatabaseAtomicSignalLinkProven":False,
        "offHostRecoverabilityVerified":False,
        "automaticRolloverEnabled":False,
        "liveAuthorized":False,
        "edgeEstablished":False,
        "newApiCalls":0,
        "sourceWrites":0,
    }
