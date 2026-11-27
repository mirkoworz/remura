"""Track B OFFLINE: append-only source link between first-seen ingest and COT/price decision.

This MAY run only in a FUTURE coordinated research mode, after a brand-new
squalincome_history INSERT and shark_observation_bundle.record() on the SAME
SQLite connection and inside the SAME original observer transaction. It does
not modify/import production signals_monitor or the LIVE collector.

An earlier, append-only first-seen ingest proof must match the EXACT full
OHLC document used at this decision, its original M15 close and local
receive/ingest clocks. The already-present COT link and H1/H4 price proof
must match this exact history row. Unknown retail first-seen / CVD coverage
remain UNKNOWN, never asserted as verified or negative controls.

This proves local cross-table consistency ONLY: SQLite timestamps can be
operator-supplied, COT receipt is not independently signed by CFTC and
cTrader parent JSON-read clock is not the Spotware response time. No
realized returns, orders, notifications, broker calls or retroactive fills.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import re
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as protocol
from scripts import shark_ingest_first_seen as ingest
from scripts import shark_price_asof_evidence as price
from scripts import shark_signal_evidence as cot
from scripts import shark_market_regime_context as regime

SCHEMA = "remura-track-b-original-decision-ingest-cot-price-link-v1"
TABLE = "research_signal_ingest_source_links"
ALG = "original_same_snapshot_ingest_cot_price_v1"
MAX_LINKS = 15000
MAX_OBS_DELAY = timedelta(seconds=30)
MAX_INGEST_AGE = timedelta(minutes=3)
STEP = timedelta(minutes=15)
HASH = re.compile(r"[0-9a-f]{64}\Z")


def ensure_schema(db):
    """EXPLICIT sandbox migration; never invoked by the default LIVE path."""
    if not isinstance(db, sqlite3.Connection) or db.in_transaction:
        raise ValueError("research_migration_requires_clean_connection")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            history_id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL CHECK(symbol IN ('EURUSD','XAUUSD')),
            cot_report_date TEXT NOT NULL,
            price_closed_at_utc TEXT NOT NULL,
            observed_at_utc TEXT NOT NULL,
            linked_at_utc TEXT NOT NULL,
            original_ingest_proof_id INTEGER NOT NULL,
            merged_document_sha256 TEXT NOT NULL,
            cot_source_version_digest TEXT NOT NULL,
            algorithm TEXT NOT NULL,
            UNIQUE(symbol,cot_report_date,price_closed_at_utc)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_signal_ingest_link_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_signal_ingest_link_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def _hex(s):
    return type(s) is str and HASH.fullmatch(s) is not None


def _read(db, history_id, original_document, now):
    if (protocol.protocol_sha256() != protocol.FROZEN_PROTOCOL_SHA256
            or now < witness._parse(protocol.START)):
        raise ValueError("frozen_prospective_protocol_gate")
    history=db.execute(
        "SELECT symbol,report_date,price_time,observed_at,state,cot_side "
        "FROM squalincome_history WHERE id=?", (history_id,)
    ).fetchone()
    if history is None:
        raise ValueError("original_signal_history_absent")
    symbol,week,price_time,stamp,state,side=history
    if symbol not in ingest.PILOT or state not in ("aligned","divergent") or side not in (-1,1):
        raise ValueError("only_original_two_market_signal_pilot")
    observed=witness._parse(stamp)
    closed=witness._parse(price_time)
    if (observed < witness._parse(protocol.START)
            or not closed <= observed <= now <= observed + MAX_OBS_DELAY
            or closed.minute % 15 or closed.second or closed.microsecond
            or observed-closed > MAX_INGEST_AGE):
        raise ValueError("noncausal_new_signal_observation_clock")
    if type(original_document) is not dict:
        raise ValueError("actual_original_scan_document_required")
    digest=regime._digest(original_document)
    if not _hex(digest):
        raise ValueError("invalid_original_price_sha")

    # Existing price as-of proof is created by the SAME original Squalincome
    # observation bundle, whose price.capture validated all three M15/H1/H4
    # rollups against the original in-memory document.
    proofs=db.execute(
        f"SELECT observed_at,witnessed_at,source_document_sha256,"
        f"m15_closed_at,algorithm FROM {price.TABLE} "
        "WHERE symbol=? AND report_date=? AND price_time=?",
        (symbol,week,price_time)
    ).fetchall()
    if len(proofs)!=1:
        raise ValueError("missing_exact_original_price_asof_proof")
    p_obs,p_record,p_sha,p_closed,p_alg=proofs[0]
    if (p_alg!=price.ALGO or p_sha!=digest
            or witness._parse(p_obs)!=observed
            or witness._parse(p_closed)!=closed
            or not observed <= witness._parse(p_record) <= now):
        raise ValueError("original_price_evidence_mismatch_or_future")

    # COT is witnessed BEFORE original observation, then source values were
    # independently checked by shark_signal_evidence.capture at decision.
    c_rows=db.execute(
        f"SELECT observed_at,linked_at,cot_side,source_version_evidence,"
        f"evidence_digest,algorithm FROM {cot.TABLE} "
        "WHERE symbol=? AND cot_week=? AND price_closed_at=?",
        (symbol,week,price_time)
    ).fetchall()
    if len(c_rows)!=1:
        raise ValueError("missing_exact_original_cot_link")
    c_obs,c_link,c_side,versions,versions_sha,c_alg=c_rows[0]
    if (c_alg!=cot.ALG or c_side!=side or
            witness._parse(c_obs)!=observed or
            not observed<=witness._parse(c_link)<=now or
            not _hex(versions_sha) or type(versions) is not str or
            hashlib.sha256(versions.encode()).hexdigest()!=versions_sha):
        raise ValueError("cot_proof_or_original_decision_mismatch")
    try:
        cot_versions=json.loads(versions)
        if (type(cot_versions) is not list
                or len(cot_versions) not in (2,4)
                or any(type(x) is not dict or
                       witness._parse(x.get("witnessed"))>observed
                       for x in cot_versions)):
            raise ValueError("cot_versions_cannot_be_after_decision")
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("invalid_original_cot_version_witnesses") from exc

    # The ingress evidence is append-only and was saved in the SAME UPSERT
    # transaction as the original merged prices, NOT synthesized from
    # prices.updated_at (M15 candle OPEN) or child generatedAt (START).
    matches=db.execute(
        f"SELECT id,last_complete_open_utc,closed_at_utc,"
        f"collection_started_utc,parent_read_at_utc,recorded_at_utc,"
        f"merged_document_sha256,algorithm FROM {ingest.TABLE} "
        "WHERE symbol=? AND merged_document_sha256=? "
        "ORDER BY id DESC LIMIT 3",
        (symbol,digest)
    ).fetchall()
    eligible=[]
    for row in matches:
        ident,opened,ingest_close,started,receipt,recorded,sha,algorithm=row
        if algorithm!=ingest.ALGORITHM or sha!=digest:
            continue
        opened=witness._parse(opened)
        ingested_close=witness._parse(ingest_close)
        started=witness._parse(started)
        receipt=witness._parse(receipt)
        recorded=witness._parse(recorded)
        # EXACT same M15 source and no later child merge allowed.
        if (opened+STEP!=closed or ingested_close!=closed or
                not witness._parse(protocol.START)<=started<=receipt<=recorded<=observed
                or observed-recorded>MAX_INGEST_AGE):
            continue
        eligible.append(ident)
    if len(eligible)!=1:
        raise ValueError("missing_or_ambiguous_original_ingest_first_seen")

    # Compare against actual SQLite CURRENT snapshot, not a selectively
    # supplied earlier copy or a newly fetched broker history.
    current=db.execute("SELECT payload FROM prices WHERE symbol=?",(symbol,)).fetchone()
    if current is None:
        raise ValueError("price_source_missing_at_original_signal")
    try:
        stored=json.loads(current[0])
    except (ValueError,TypeError) as exc:
        raise ValueError("invalid_current_price_payload") from exc
    if regime._digest(stored)!=digest:
        raise ValueError("price_document_reloaded_or_changed_after_original_ingest")
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]>=MAX_LINKS:
        raise ValueError("research_source_link_capacity_reached")
    return symbol,week,price_time,stamp,digest,eligible[0],versions_sha


def capture(db, *, history_id, original_document, clock):
    """Attach ONLY during original history INSERT transaction, AFTER bundle.

    This module cannot authenticate the caller's claim that this transaction
    is the first history insertion: the calling future coordinator MUST check
    cursor.rowcount == 1 and call all witnesses before commit. No backfill.
    """
    if not isinstance(db,sqlite3.Connection) or not db.in_transaction:
        raise ValueError("same_original_history_transaction_required")
    if type(history_id) is not int or history_id<=0:
        raise ValueError("new_history_id_required")
    now=witness._clock(clock)
    symbol,week,price_closed,observed,sha,ingest_id,cot_sha=_read(
        db,history_id,original_document,now)
    if db.execute(f"SELECT 1 FROM {TABLE} WHERE history_id=?",
                  (history_id,)).fetchone():
        raise ValueError("original_observation_already_joined")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(history_id,symbol,cot_report_date,price_closed_at_utc,"
        "observed_at_utc,linked_at_utc,original_ingest_proof_id,"
        "merged_document_sha256,cot_source_version_digest,algorithm)"
        " VALUES (?,?,?,?,?,?,?,?,?,?)",
        (history_id,symbol,week,price_closed,observed,
         witness._iso(now),ingest_id,sha,cot_sha,ALG)
    )
    return {
        "schema":SCHEMA,"status":"ORIGINAL_LOCAL_COT_PRICE_INGEST_LINKED",
        "localOriginalMergedPriceHashMatched":True,
        "originalM15CloseAndDecisionClockMatched":True,
        "previousCotValueVersionDigestMatched":True,
        "retailFirstSeen": "UNKNOWN_NO_INDEPENDENT_PROOF",
        "cvdCoverage": "UNKNOWN_NO_SAME_SOURCE_FULL_SCAN",
        "trueBrokerResponseReceiptAuthenticated":False,
        "originalSourceClockIndependentlyTrusted":False,
        "statisticalEdgeEstablished":False,
        "realizedReturnsOrCostsCalculated":False,
        "ordersEnabled":False,"notificationsEnabled":False,
        "brokerCalls":0
    }


def aggregate(db):
    if not isinstance(db,sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    states=db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0]
    return {"schema":SCHEMA,"locallyJoined":states,
            "locallyJoinedNotExternallyAuthenticated":True,
            "retailFirstSeenVerified":False,"cvdFullScanVerified":False,
            "actualOOSOrCostsMeasured":False,"statisticalEdgeEstablished":False,
            "liveEnabled":False,"brokerCalls":0}
