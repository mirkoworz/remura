"""Track C C2c: OFFLINE post-response COT handoff to ORIGINAL Track B.

Research rehearsal, NOT an HTTP collector or live recorder. A future parent
must sample a real UTC clock immediately AFTER each original CFTC response.
The old production cot_first_seen samples now BEFORE download; it must NOT
be mistaken for independently proved receipt time.

All source material and clocks here are caller-supplied SYNTHETIC fixtures.
Never requests any URL, reads files, creates/migrates databases, modifies LIVE,
or backfills historical timestamps. Reuses the exact pinned B normalizer and
append-only local COT witness; no duplicate institutional algorithm.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import sqlite3

MODE = "OFFLINE_SYNTHETIC_POST_RESPONSE_ONLY"
SCHEMA = "remura-track-c-cot-post-response-contract-v1"
PILOT = {"tff": "099741", "disagg": "088691"}
SOURCE_ORDER = ("tff", "disagg")
MAX_HTTP_SPAN = timedelta(seconds=60)
MAX_WRITE_DELAY = timedelta(seconds=30)
MAX_DECISION_DELAY = timedelta(minutes=3)
MIN_START = datetime(2026, 11, 9, tzinfo=timezone.utc)


def _utc(value):
    if (type(value) is not datetime or value.tzinfo is None
            or value.utcoffset() != timedelta(0)):
        raise ValueError("explicit_utc_runtime_clock_required")
    return value.astimezone(timezone.utc)


def _memory(db):
    if type(db) is not sqlite3.Connection or db.in_transaction:
        raise ValueError("clean_in_memory_connection_required")
    places = db.execute("PRAGMA database_list").fetchall()
    if len(places) != 1 or places[0][1] != "main" or places[0][2]:
        raise ValueError("live_or_attached_sqlite_forbidden")


def _schemas(db, witness):
    tables = {name: typ for name, typ in db.execute(
        "SELECT name,type FROM sqlite_master WHERE name IN (?,?,?,?,?)",
        ("cot_reports", witness.TABLE, "research_cot_asof_no_update",
         "research_cot_asof_no_delete", "cot_first_seen"))}
    if (tables.get("cot_reports") != "table"
            or tables.get(witness.TABLE) != "table"
            or tables.get("research_cot_asof_no_update") != "trigger"
            or tables.get("research_cot_asof_no_delete") != "trigger"):
        raise ValueError("explicit_pinned_b_research_schema_required")


def rehearse(db, *, arrivals, write_at, decision_at, mode=None):
    """Validate original mocked responses then witness ACTUAL B COT values.

    Two independent requests, two consecutive published-report dates per
    contract. All timestamps are local clock claims, NOT provider signatures.
    No cot_first_seen insert: legacy first_seen is not corrected/backfilled.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_synthetic_mode_required")
    _memory(db)
    from scripts import shark_cot_asof_witness as witness
    from scripts import cot_monitor as cot
    from scripts import shark_cvd_incremental_protocol as frozen
    if frozen.protocol_sha256() != frozen.FROZEN_PROTOCOL_SHA256:
        raise ValueError("original_track_b_protocol_changed")
    _schemas(db, witness)
    if type(arrivals) is not list or len(arrivals) != 2:
        raise ValueError("exact_two_original_cot_responses_required")
    persisted = _utc(write_at)
    decision = _utc(decision_at)
    if not MIN_START <= persisted <= decision <= persisted + MAX_DECISION_DELAY:
        raise ValueError("noncausal_persistence_decision_clock")
    new = {}
    previous_receive = None
    report_dates = None
    for i, item in enumerate(arrivals):
        if type(item) is not dict or set(item) != {
                "dataset", "request_started_at", "response_received_at", "records"}:
            raise ValueError("original_response_envelope_required")
        dataset = SOURCE_ORDER[i]
        if item["dataset"] != dataset:
            raise ValueError("unexpected_cot_dataset_order")
        started = _utc(item["request_started_at"])
        received = _utc(item["response_received_at"])
        if (started < MIN_START or not started <= received <= persisted
                or received - started > MAX_HTTP_SPAN
                or persisted - received > MAX_WRITE_DELAY
                or previous_receive is not None and started < previous_receive):
            raise ValueError("not_proven_post_response_receive_clock")
        previous_receive = received
        expected = PILOT[dataset]
        if (expected not in cot.DATASETS[dataset]["codes"]
                or expected not in witness.DATASET_CODES[dataset]):
            raise ValueError("original_cot_mapping_drift")
        # Reuse B original CFTC validation, NOT a copied parser.
        normalized = cot.normalize(dataset, item["records"], now=received)
        if (len(normalized) != 2 or
                any(kind != dataset or code != expected
                    for kind, code, _ in normalized)):
            raise ValueError("exact_pilot_contract_two_weeks_required")
        dates = sorted(key[2] for key in normalized)
        if (date.fromisoformat(dates[1]) - date.fromisoformat(dates[0])
                != timedelta(days=7)
                or (received.date()-date.fromisoformat(dates[0])).days > 22
                or (received.date()-date.fromisoformat(dates[1])).days < 0):
            raise ValueError("not_two_recent_consecutive_report_weeks")
        if report_dates is not None and dates != report_dates:
            raise ValueError("pilot_cot_weeks_not_aligned")
        report_dates = dates
        new.update(normalized)
    # No historical replay or edits: require all keys genuinely absent.
    existing = set(db.execute(
        "SELECT dataset,code,report_date FROM cot_reports").fetchall())
    if existing.intersection(new):
        raise ValueError("existing_cot_not_new_original_response")
    old_first_seen = None
    if db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='cot_first_seen'"
    ).fetchone():
        old_first_seen = db.execute(
            "SELECT count(*) FROM cot_first_seen").fetchone()[0]
    db.execute("BEGIN IMMEDIATE")
    try:
        db.executemany(
            "INSERT INTO cot_reports (dataset,code,report_date,oi,first_long,"
            "first_short,second_long,second_short) VALUES (?,?,?,?,?,?,?,?)",
            [(kind, code, report, *values)
             for (kind,code,report),values in new.items()],
        )
        # ORIGINAL Track B local witness. It closes/commits the outer SQLite
        # transaction; nothing else writes after this call.
        result = witness.witness(db, clock=persisted)
        if (result["newWitnessRows"] != 4
                or result["sourceValuesPresent"] != 4):
            raise ValueError("original_b_cot_witness_mismatch")
        db.commit()
    except BaseException:
        db.rollback()
        raise
    if old_first_seen is not None:
        after = db.execute("SELECT count(*) FROM cot_first_seen").fetchone()[0]
        if after != old_first_seen:
            raise ValueError("legacy_first_seen_unexpectedly_modified")
    return {
        "schema": SCHEMA,
        "state": "SYNTHETIC_ORIGINAL_B_COT_WITNESSED_AFTER_RECEIPT_NOT_LIVE",
        "pilotContracts": 2,
        "researchValueWitnesses": result["newWitnessRows"],
        "legacyFirstSeenBackfilled": False,
        "realProviderReceiptAuthenticated": False,
        "realMarketObservations": False,
        "newExternalAPICalls": 0,
        "liveCollectorWired": False,
        "tradingEdgeEstablished": False,
        "ordersEnabled": False,
        "notificationsEnabled": False,
    }
