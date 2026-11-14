"""Track B OFFLINE: pre-decision retail handoff across two SQLite stores.

The receipt shard and the Squalincome decision database are NOT one SQLite
transaction. This module deliberately uses a one-way PRE-DECISION ticket:
  1. read and check an already-persisted segment receipt, BEFORE a decision
  2. pin its exact identity in the NEW original history transaction
  3. AFTER commit, independently reconcile the unchanged shard receipt

Never choose/attach a later source at reconciliation time. If the original
history, linked COT+price+ingest evidence, or retail shard disappeared,
report UNKNOWN -- do NOT backfill, manufacture sample coverage or re-fetch
the provider. Pinning is a LOCAL assertion, not independently signed proof
of reception time or an actual Squalincome signal input. A privileged caller
could forge its own clock. This is a laboratory contract, not a production
hook, cross-DB atomicity, off-host recovery, external timestamp or trading
signal. No API, LIVE DB, VPS, collector, broker, cron or notifications.
"""
from __future__ import annotations

from datetime import datetime,timedelta
import hashlib
import json
import sqlite3

from scripts import shark_cot_asof_witness as clocking
from scripts import shark_signal_evidence as cot
from scripts import shark_price_asof_evidence as price
from scripts import shark_ingest_first_seen as ingest
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_retail_segment_readiness as layout
from scripts import shark_retail_segment_writer as writer
from scripts import shark_signal_ingest_decision_link as source

SCHEMA="remura-track-b-predecision-retail-crossdb-handoff-v1"
TABLE="research_original_retail_predecision_pins"
ALGORITHM="predecision_original_row_to_isolated_retial_shard_v1"
MAX_ROWS=15000
PIN_GRACE=timedelta(seconds=30)
SHA_KEYS=("originalSha256","numericSha256")


def _hex(value):
    return (type(value) is str and len(value)==64
            and all(c in "0123456789abcdef" for c in value))


def _ident(ticket):
    expected={"schema","symbol","segmentNumber","receiptId",
              "sourceUpdatedAt","readAt","recordedAt","preparedAt",
              "originalSha256","numericSha256"}
    if type(ticket) is not dict or set(ticket)!=expected:
        raise ValueError("untrusted_predecision_receipt_ticket")
    if (ticket["schema"]!=SCHEMA or ticket["symbol"] not in retail.PILOT
            or type(ticket["segmentNumber"]) is not int
            or not 1<=ticket["segmentNumber"]<=layout.EXPECTED_SEGMENTS
            or type(ticket["receiptId"]) is not int
            or ticket["receiptId"]<=0
            or any(not _hex(ticket[k]) for k in SHA_KEYS)):
        raise ValueError("invalid_predecision_retail_receipt_identity")
    updated=clocking._parse(ticket["sourceUpdatedAt"])
    read=clocking._parse(ticket["readAt"])
    recorded=clocking._parse(ticket["recordedAt"])
    prepared=clocking._parse(ticket["preparedAt"])
    if (not updated<=read<=recorded<=prepared
            or prepared-updated>retail.MAX_AGE
            or prepared-recorded>retail.MAX_AGE):
        raise ValueError("predecision_receipt_not_causal_or_fresh")
    return updated,read,recorded,prepared


def _from_shard(db,receipt_id,expected_symbol):
    row=db.execute(
        f"SELECT id,symbol,source_updated_at,original_read_at,recorded_at,"
        f"numeric_sha256,algorithm FROM {retail.TABLE} WHERE id=?",
        (receipt_id,)).fetchone()
    if row is None:
        raise ValueError("pinned_receipt_missing_from_shard")
    ident,symbol,updated,read,recorded,digest,alg=row
    if symbol!=expected_symbol or alg!=retail.ALG or not _hex(digest):
        raise ValueError("shard_receipt_identity_inconsistent")
    item=db.execute(
        f"SELECT symbol,original_sha256,recorded_at,"
        f"long_pct,short_pct,long_lots,short_lots,long_positions,"
        f"short_positions,features_sha256,algorithm "
        f"FROM {numeric.TABLE} WHERE receipt_id=?",(ident,)).fetchone()
    if item is None:
        raise ValueError("pinned_numeric_six_missing_from_shard")
    sym,original,when,*rest=item
    six_values=rest[:6]
    feature_digest,algorithm=rest[6:]
    if (sym!=symbol or original!=digest or when!=recorded
            or algorithm!=numeric.ALG or not _hex(feature_digest)):
        raise ValueError("pinned_numeric_source_link_mismatched")
    six=dict(zip(numeric.FIELDS,six_values))
    try:
        clean=numeric._six(six)
        computed=numeric._hash(symbol,digest,clean)
    except (TypeError,ValueError) as exc:
        raise ValueError("pinned_numeric_six_invalid") from exc
    if computed!=feature_digest:
        raise ValueError("pinned_numeric_values_digest_invalid")
    return {
        "schema":SCHEMA,"symbol":symbol,"receiptId":ident,
        "sourceUpdatedAt":updated,"readAt":read,
        "recordedAt":recorded,
        "originalSha256":digest,"numericSha256":feature_digest,
    }


def _original_proofs_still_present(db,history_id,sym,observed):
    """Read-only evidence chain check, not a new signal or provider fetch."""
    h=db.execute(
        "SELECT symbol,report_date,price_time,observed_at,cot_side "
        "FROM squalincome_history WHERE id=?",(history_id,)).fetchone()
    link=db.execute(
        f"SELECT symbol,cot_report_date,price_closed_at_utc,"
        f"observed_at_utc,linked_at_utc,original_ingest_proof_id,"
        f"merged_document_sha256,cot_source_version_digest,algorithm "
        f"FROM {source.TABLE} WHERE history_id=?",(history_id,)).fetchone()
    if h is None or link is None:
        return False
    hs,week,closed,stamp,side=h
    ls,lweek,lclosed,lobs,linked,ingest_id,doc_sha,cot_sha,alg=link
    if (hs!=sym or (hs,week,closed)!=(ls,lweek,lclosed)
            or clocking._parse(stamp)!=observed
            or clocking._parse(lobs)!=observed
            or alg!=source.ALG or not _hex(doc_sha) or not _hex(cot_sha)
            or type(ingest_id) is not int or ingest_id<=0
            or not observed<=clocking._parse(linked)
                    <=observed+source.MAX_OBS_DELAY):
        return False
    p=db.execute(
        f"SELECT observed_at,witnessed_at,source_document_sha256,"
        f"m15_closed_at,algorithm FROM {price.TABLE} "
        "WHERE symbol=? AND report_date=? AND price_time=?",
        (hs,week,closed)).fetchone()
    if p is None or p[4]!=price.ALGO or p[2]!=doc_sha:
        return False
    if (clocking._parse(p[0])!=observed
            or clocking._parse(p[3])!=clocking._parse(closed)
            or not observed<=clocking._parse(p[1])<=clocking._parse(linked)):
        return False
    c=db.execute(
        f"SELECT observed_at,linked_at,cot_side,source_version_evidence,"
        f"evidence_digest,algorithm FROM {cot.TABLE} "
        "WHERE symbol=? AND cot_week=? AND price_closed_at=?",
        (hs,week,closed)).fetchone()
    if (c is None or c[2]!=side or c[5]!=cot.ALG
            or c[4]!=cot_sha or type(c[3]) is not str
            or hashlib.sha256(c[3].encode()).hexdigest()!=cot_sha):
        return False
    if (clocking._parse(c[0])!=observed
            or not observed<=clocking._parse(c[1])<=clocking._parse(linked)):
        return False
    original_ingest=db.execute(
        f"SELECT symbol,closed_at_utc,recorded_at_utc,"
        f"merged_document_sha256,algorithm FROM {ingest.TABLE} "
        "WHERE id=?",(ingest_id,)).fetchone()
    if original_ingest is None:
        return False
    return (original_ingest[0]==hs
            and clocking._parse(original_ingest[1])==clocking._parse(closed)
            and clocking._parse(original_ingest[2])<=observed
            and original_ingest[3]==doc_sha
            and original_ingest[4]==ingest.ALGORITHM)


def _latest_asof(folder,segment_count,symbol,as_of):
    """Find the last recorded local source as of ORIGINAL observation time."""
    latest=None
    for number in range(1,segment_count+1):
        db=writer._ro(writer._path(folder,number))
        try:
            for rid,stamp in db.execute(
                f"SELECT id,recorded_at FROM {retail.TABLE} WHERE symbol=?",
                (symbol,)):
                received=clocking._parse(stamp)
                if received<=as_of:
                    candidate=(received,number,rid)
                    if latest is None or candidate>latest:
                        latest=candidate
        finally:
            db.close()
    return latest


def prepare(root,*,authorized_at,symbol,prepared_at):
    """READ ONLY lab lookup of latest already recorded receipt AS OF now.

    All existing shards are first validated under the writer's lab gate.
    A distinct later scan must supply the resulting ticket at NEW history
    insertion; this function does not and must not append history itself.
    A shard can still change between this read and that transaction;
    post-commit reconcile therefore treats changed evidence as UNKNOWN.
    """
    prepared=clocking._clock(prepared_at)
    if symbol not in retail.PILOT:
        raise ValueError("pilot_market_required")
    plan=layout.plan(authorized_at)
    if plan["status"]!="OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO":
        raise ValueError("retail_segment_calendar_not_authorized")
    # One lock spans verification + exact receipt selection. Any later
    # append requires a NEW verification, not a silent post-hoc source.
    with writer._exclusive(root) as folder:
        shards,_,_=writer._inspect(
            folder,{**plan,"_authorized_at":authorized_at},20)
        if not shards:
            raise ValueError("no_prior_persisted_segment_receipt")
        chosen=_latest_asof(folder,len(shards),symbol,prepared)
        if chosen is None:
            raise ValueError("no_asof_persisted_retail_receipt")
        _,shard,rid=chosen
        db=writer._ro(writer._path(folder,shard))
        try:
            row=_from_shard(db,rid,symbol)
        finally:
            db.close()
    ticket={
        "schema":SCHEMA,"symbol":symbol,"segmentNumber":shard,
        "receiptId":rid,"sourceUpdatedAt":row["sourceUpdatedAt"],
        "readAt":row["readAt"],"recordedAt":row["recordedAt"],
        "preparedAt":clocking._iso(prepared),
        "originalSha256":row["originalSha256"],
        "numericSha256":row["numericSha256"],
    }
    _ident(ticket)
    return ticket


def ensure_schema(db):
    """Explicit research-only migration on an unused synthetic original DB."""
    if not isinstance(db,sqlite3.Connection) or db.in_transaction:
        raise ValueError("explicit_clean_original_db_migration_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            history_id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            observed_at TEXT NOT NULL,segment_number INTEGER NOT NULL,
            receipt_id INTEGER NOT NULL,
            original_sha256 TEXT NOT NULL,numeric_sha256 TEXT NOT NULL,
            source_updated_at TEXT NOT NULL,retail_read_at TEXT NOT NULL,
            retail_recorded_at TEXT NOT NULL,prepared_at TEXT NOT NULL,
            pinned_at TEXT NOT NULL,algorithm TEXT NOT NULL
        )""")
        for op,name in (
            ("UPDATE","research_predecision_retail_pin_no_update"),
            ("DELETE","research_predecision_retail_pin_no_delete")):
            db.execute(f"""CREATE TRIGGER IF NOT EXISTS {name}
                BEFORE {op} ON {TABLE} BEGIN
                SELECT RAISE(ABORT,'append_only'); END""")


def pin_new(db,*,fresh_history_cursor,ticket,clock):
    """Pin immediately after ORIGINAL INSERT, during its write transaction.

    Caller MUST later include COT+price+ingest source proofs and commit ALL
    together. If subsequent work aborts, pin and original history roll back.
    This cannot prove that an untrusted caller genuinely executed a scan.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("new_original_write_transaction_required")
    cur=fresh_history_cursor
    if (not isinstance(cur,sqlite3.Cursor) or cur.connection is not db
            or cur.rowcount!=1 or type(cur.lastrowid) is not int
            or cur.lastrowid<=0
            or db.execute("SELECT last_insert_rowid()").fetchone()[0]!=cur.lastrowid):
        raise ValueError("fresh_original_history_insert_cursor_required")
    now=clocking._clock(clock)
    updated,read,recorded,prepared=_ident(ticket)
    hid=cur.lastrowid
    row=db.execute(
        "SELECT symbol,observed_at FROM squalincome_history WHERE id=?",
        (hid,)).fetchone()
    if row is None:
        raise ValueError("fresh_original_squalincome_row_missing")
    symbol,stamp=row
    observed=clocking._parse(stamp)
    if (symbol!=ticket["symbol"] or not prepared<=observed<=now
            or now-observed>PIN_GRACE
            or observed-prepared>PIN_GRACE
            or observed-updated>retail.MAX_AGE):
        raise ValueError("retail_ticket_not_known_before_original_observation")
    if db.execute(f"SELECT 1 FROM {TABLE} WHERE history_id=?",(hid,)).fetchone():
        raise ValueError("original_retail_ticket_cannot_be_rebound")
    db.execute(
        f"INSERT INTO {TABLE} VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (hid,symbol,stamp,ticket["segmentNumber"],ticket["receiptId"],
         ticket["originalSha256"],ticket["numericSha256"],
         ticket["sourceUpdatedAt"],ticket["readAt"],
         ticket["recordedAt"],ticket["preparedAt"],
         clocking._iso(now),ALGORITHM))
    return {
        "schema":SCHEMA,"status":"PREDECISION_LOCAL_TICKET_PINNED_IN_OPEN_ORIGINAL_TX",
        "historyId":hid,
        "originalTransactionStillOpen":db.in_transaction,
        "retailActuallyUsedBySqualincome":False,
        "crossDatabaseAtomicityProven":False,
        "liveAuthorized":False,
    }


def reconcile(core_db,root,*,history_id,authorized_at):
    """Read-only post-crash comparison with precisely PINNED shard values.

    NEVER choose latest available receipt during reconciliation.
    An absent history, source chain or shard is UNKNOWN, not a new sample.
    """
    if (not isinstance(core_db,sqlite3.Connection) or core_db.in_transaction
            or core_db.execute("PRAGMA query_only").fetchone()[0]!=1
            or type(history_id) is not int or history_id<=0):
        raise ValueError("read_only_exact_original_history_id_required")
    unknown={
        "schema":SCHEMA,"status":"UNKNOWN_ORIGINAL_OR_SHARD_PROOF_UNVERIFIABLE",
        "verifiedOriginalRetailPin":False,
        "reconstructedFromLaterRetailData":False,
        "liveAuthorized":False,
        "apiCallsAdded":0,
        "edgeEstablished":False,
    }
    pin=core_db.execute(
        f"SELECT symbol,observed_at,segment_number,receipt_id,"
        f"original_sha256,numeric_sha256,source_updated_at,retail_read_at,"
        f"retail_recorded_at,prepared_at,pinned_at,algorithm "
        f"FROM {TABLE} WHERE history_id=?",(history_id,)).fetchone()
    if pin is None:
        return unknown
    sym,observed,segment,rid,orig,digest,updated,read,recorded,prepared,pinned,alg=pin
    if alg!=ALGORITHM:
        return unknown
    try:
        if not _original_proofs_still_present(
                core_db,history_id,sym,clocking._parse(observed)):
            return unknown
    except (ValueError,TypeError,OverflowError,sqlite3.Error):
        return unknown
    ticket={
        "schema":SCHEMA,"symbol":sym,"segmentNumber":segment,
        "receiptId":rid,"sourceUpdatedAt":updated,"readAt":read,
        "recordedAt":recorded,"preparedAt":prepared,
        "originalSha256":orig,"numericSha256":digest,
    }
    try:
        _ident(ticket)
        recorded_at=clocking._parse(observed)
        prepared_at=clocking._parse(prepared)
        pinned_at=clocking._parse(pinned)
        if (not prepared_at<=recorded_at<=pinned_at
                or recorded_at-prepared_at>PIN_GRACE
                or pinned_at-recorded_at>PIN_GRACE):
            return unknown
        with writer._exclusive(root) as folder:
            plan=layout.plan(authorized_at)
            if plan["status"]!="OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO":
                return unknown
            shards,_,_=writer._inspect(
                folder,{**plan,"_authorized_at":authorized_at},20)
            if segment not in shards:
                return unknown
            # A more recent value already recorded BEFORE the original
            # observation makes the older pin UNKNOWN, not reselectable.
            latest=_latest_asof(folder,len(shards),sym,recorded_at)
            if latest!=(clocking._parse(ticket["recordedAt"]),segment,rid):
                return unknown
            shard=writer._ro(writer._path(folder,segment))
            try:
                from_file=_from_shard(shard,rid,sym)
            finally:
                shard.close()
        if any(ticket[k]!=from_file[k] for k in (
                "symbol","receiptId","sourceUpdatedAt","readAt",
                "recordedAt","originalSha256","numericSha256")):
            return unknown
    except (ValueError,sqlite3.Error,OSError):
        return unknown
    return {
        "schema":SCHEMA,"status":"LOCAL_PREDECISION_TICKET_AND_SHARD_MATCH_NOT_LIVE_GO",
        "verifiedOriginalRetailPin":True,
        "reconstructedFromLaterRetailData":False,
        "localClocksExternallyAttested":False,
        "retailActuallyUsedBySqualincome":False,
        "crossDatabaseAtomicityProven":False,
        "offHostRestoreVerified":False,
        "tradingEdgeEstablished":False,
        "liveAuthorized":False,
        "apiCallsAdded":0,
    }
