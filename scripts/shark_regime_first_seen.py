"""REMURA Track B: OFFLINE ONLY prospective first-seen price-regime witness.

Future coordinated integration MAY invoke capture immediately after a genuine
new Squalincome history INSERT and same-transaction original price evidence,
using the SAME in-memory price document and actual source receipt clock.
Never execute this module on LIVE until reviewed/backup-restore/rollback and
version/date release gate. This file is NOT imported by production.

This is a local source-consistency check; untrusted clocks/document SHA do
not independently authenticate cTrader, price collection, COT, or outcomes.
No retrospective regime backfill, broker GET, trade, signal, order, alert,
file access, cloud service or autonomous scheduling.
"""
from __future__ import annotations

from datetime import timedelta
import sqlite3

from scripts import shark_cot_asof_witness as witness
from scripts import shark_price_asof_evidence as price
from scripts import shark_market_regime_context as regime
from scripts import shark_cvd_incremental_protocol as study

SCHEMA = "remura-shark-regime-first-seen-local-v1"
TABLE = "research_squalincome_regime_first_seen"
MAX_ROWS = price.MAX_EVENTS
MAX_CAPTURE_LATENCY = timedelta(seconds=30)
ALGORITHM = "original_closed_m15_efficiency_33bars_offline_v1"


def ensure_schema(db):
    """EXPLICIT future opt-in schema, never a production migration."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    with db:
        db.execute(f"""CREATE TABLE IF NOT EXISTS {TABLE}(
            history_id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            report_date TEXT NOT NULL,
            price_time TEXT NOT NULL,
            observed_at TEXT NOT NULL,
            recorded_at TEXT NOT NULL,
            source_received_at TEXT NOT NULL,
            source_document_sha256 TEXT NOT NULL,
            m15_closed_at TEXT NOT NULL,
            state TEXT NOT NULL CHECK(state IN
                ('DIRECTIONAL_UP','DIRECTIONAL_DOWN','LATERAL','MIXED')),
            efficiency_ratio REAL NOT NULL
                CHECK(efficiency_ratio >= 0 AND efficiency_ratio <= 1),
            algorithm TEXT NOT NULL,
            UNIQUE(symbol,report_date,price_time)
        )""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_regime_first_no_update
            BEFORE UPDATE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")
        db.execute(f"""CREATE TRIGGER IF NOT EXISTS research_regime_first_no_delete
            BEFORE DELETE ON {TABLE}
            BEGIN SELECT RAISE(ABORT,'append_only'); END""")


def capture(db, *, history_id, observed_document, source_received_at,
            clock):
    """Write only from a REAL newly inserted observation in SAME SQLite tx.

    Future coordinator must check original history INSERT rowcount=1, create
    the original price.asof evidence in the same transaction FIRST, then call
    this method BEFORE COMMIT. Provide an actual runtime clock (not a candle
    open masquerading as collection time) and original in-memory document.

    A record already in SQLite or a later replacement document cannot be
    given a new regime after the original decision; a missing local price
    proof fails closed. Timestamp/SHA authenticity is not independent.
    """
    if not isinstance(db, sqlite3.Connection) or not db.in_transaction:
        raise ValueError("same_original_observation_transaction_required")
    if type(history_id) is not int or history_id <= 0:
        raise ValueError("new_history_id_required")
    now = witness._clock(clock)
    if (study.protocol_sha256() != study.FROZEN_PROTOCOL_SHA256
            or now < witness._parse(study.START)):
        raise ValueError("frozen_protocol_or_prospective_start_invalid")
    row = db.execute(
        "SELECT symbol,report_date,price_time,observed_at "
        "FROM squalincome_history WHERE id=?", (history_id,)
    ).fetchone()
    if row is None:
        raise ValueError("original_history_row_missing")
    symbol, report, price_closed, observed_stamp = row
    observed = witness._parse(observed_stamp)
    if (observed < witness._parse(study.START)
            or not observed <= now <= observed + MAX_CAPTURE_LATENCY):
        raise ValueError("observation_not_recorded_at_original_decision")
    if db.execute(f"SELECT 1 FROM {TABLE} WHERE history_id=?",
                  (history_id,)).fetchone():
        raise ValueError("regime_evidence_cannot_be_rebound_or_backfilled")
    evidence = db.execute(
        f"SELECT observed_at,witnessed_at,source_document_sha256,"
        f"m15_closed_at,algorithm FROM {price.TABLE} "
        "WHERE symbol=? AND report_date=? AND price_time=?",
        (symbol, report, price_closed)
    ).fetchone()
    if evidence is None:
        raise ValueError("matching_original_price_evidence_missing")
    price_observed, price_witnessed, original_sha, price_last_closed, algo = evidence
    if (witness._parse(price_observed) != observed
            or algo != price.ALGO
            or not observed <= witness._parse(price_witnessed) <= now
            or witness._parse(price_last_closed) != witness._parse(price_closed)):
        raise ValueError("price_evidence_different_original_decision")
    if db.execute(f"SELECT count(*) FROM {TABLE}").fetchone()[0] >= MAX_ROWS:
        raise ValueError("regime_first_seen_capacity_reached")
    if (type(observed_document) is not dict
            or original_sha != regime._digest(observed_document)):
        raise ValueError("price_evidence_original_document_sha_mismatch")
    receipt = witness._parse(source_received_at)
    label = regime.classify({
        "symbol": symbol,
        "observedAtUtc": observed_stamp,
        # Recorded-on-decision stamp comes from the original observation,
        # NOT from a subsequent scan and NOT a claimed trusted clock.
        "firstRecordedAtUtc": observed_stamp,
        "sourceReceivedAtUtc": witness._iso(receipt),
        "originalDocumentSha256": original_sha,
        "document": observed_document,
    }, as_of=witness._iso(now))
    if label["state"] not in regime.STATES:
        raise ValueError("unclassified_regime_never_persisted")
    db.execute(
        f"INSERT INTO {TABLE} "
        "(history_id,symbol,report_date,price_time,observed_at,"
        "recorded_at,source_received_at,source_document_sha256,"
        "m15_closed_at,state,efficiency_ratio,algorithm) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (history_id, symbol, report, price_closed, observed_stamp,
         witness._iso(now), witness._iso(receipt), original_sha,
         price_last_closed, label["state"], label["efficiencyRatio"],
         ALGORITHM)
    )
    return {
        "schema": SCHEMA,
        "status": "LOCALLY_WITNESSED_REGIME_RESEARCH_ONLY",
        "originalPriceEvidenceMatched": True,
        "locallyRegisteredAfterOriginalHistoryInsert": True,
        "regime": label["state"],
        "sourceReceiptIndependentlyAuthenticated": False,
        "unforgeableClockAttested": False,
        "unmodifiedOriginalCftcDataAuthenticated": False,
        "priceReturnsOrTradingOutcomesCalculated": False,
        "statisticalEdgeEstablished": False,
        "ordersEnabled": False,
        "notificationsEnabled": False,
        "brokerCalls": 0,
    }


def aggregate(db):
    """Aggregate only. Never expose OHLC, source hashes, timestamps, IDs."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    rows = db.execute(
        f"SELECT state,count(*) FROM {TABLE} GROUP BY state"
    ).fetchall()
    by_state = dict(rows)
    return {
        "schema": SCHEMA,
        "locallyRecorded": sum(by_state.values()),
        "byRegime": {s: by_state.get(s,0) for s in regime.STATES},
        "maxConfiguredRows": MAX_ROWS,
        "liveRecorderWired": False,
        "externallyTrustedProvenance": False,
        "retrospectiveBackfillAllowed": False,
        "outcomesOrCostedReturnsPresent": False,
        "edge": "NOT_ESTABLISHED",
        "brokerCalls": 0,
    }
