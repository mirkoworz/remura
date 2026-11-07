"""Track C <-> frozen Track B ORIGINAL integration, OFFLINE ONLY.

This is a rehearsal adapter, not a recorder or production wiring.
The separate Track B checkout (exact pinned SHA in existing CI) supplies
original source/decision FIRST-SEEN modules and its own synthetic test fixtures.
Neither their sources nor scientific protocols are copied or merged here.

Accept ONLY a single SQLite :memory: DB with an explicitly prepared research
schema and caller-supplied original synthetic documents/clocks. Never read a
file, provider, token, database path, network or environment. No backfill,
orders, notifications, external datasets, performance/profit claims or LIVE.
"""
from __future__ import annotations

from datetime import datetime
import sqlite3

MODE = "OFFLINE_SYNTHETIC_ORIGINAL_B_PINNED_ONLY"
PINNED_B_SHA = "35b06da71da8cad75cc573ec8cde252f72d5a339"
EXPECTED_CVD_SHA = "09d833dafdd426254bc8fedccc367e41fa451ac8f2e6c99a9dac27f7387e2905"
EXPECTED_RETAIL_SHA = "6c4413a9851233e0785cb86eb30a03a22e8fa0a20efd4385c22638cba2ba4f6e"


def _memory_only(db):
    if type(db) is not sqlite3.Connection:
        raise ValueError("explicit_sqlite_in_memory_connection_required")
    databases = db.execute("PRAGMA database_list").fetchall()
    if len(databases) != 1 or databases[0][1] != "main" or databases[0][2]:
        raise ValueError("never_use_disk_or_attached_database")
    if db.in_transaction:
        raise ValueError("preexisting_transaction_forbidden")


def rehearsal(db, *, original_snapshot, file_read_at, receipt_clock,
              original_price_document, insert_history, decision_clock,
              mode=None):
    """Rehearse actual B first-seen -> numeric -> atomic original decision.

    Retail capture is an earlier, separate transaction, as in the real
    collector. The decision's history+COT+price+retail link is one transaction
    under B's ORIGINAL coordinator. No retrospective attachment.

    This adapter cannot authenticate its synthetic caller or source clocks,
    and may ONLY run on an isolated in-memory database. The full method is
    deliberately unusable with the LIVE SQLite file.
    """
    if mode != MODE:
        raise ValueError("offline_only_explicit_mode_required")
    _memory_only(db)
    if not callable(insert_history) or type(original_snapshot) is not dict:
        raise ValueError("explicit_original_synthetic_documents_required")
    if type(original_price_document) is not dict:
        raise ValueError("explicit_original_synthetic_price_required")
    if any(type(t) is not datetime for t in
           (file_read_at, receipt_clock, decision_clock)):
        raise ValueError("explicit_utc_datetime_clocks_required")

    # No shadow copies of any scientific algorithm. Require the ORIGINAL
    # research modules to be importable from the separately checked out B SHA.
    try:
        from scripts import shark_cvd_incremental_protocol as cvd
        from scripts import shark_retail_preregistered_protocol as study
        from scripts import shark_retail_first_seen as retail
        from scripts import shark_retail_numeric_features as numeric
        from scripts import shark_original_decision_atomic_gate as atomic
    except ImportError as exc:
        raise ValueError("original_track_b_modules_unavailable") from exc

    if (cvd.FROZEN_PROTOCOL_SHA256 != EXPECTED_CVD_SHA or
            cvd.protocol_sha256() != EXPECTED_CVD_SHA or
            study.FROZEN_RULES_SHA256 != EXPECTED_RETAIL_SHA or
            study.fingerprint() != EXPECTED_RETAIL_SHA):
        raise ValueError("frozen_original_track_b_protocol_drift")
    if (retail.PILOT != frozenset(("EURUSD", "XAUUSD")) or
            retail.MAX_ROWS != 15000 or numeric.MAX_FEATURE_ROWS != 4500):
        raise ValueError("original_track_b_contract_changed")

    # Require prior, explicit schema setup. NEVER auto-migrate the DB.
    retail.require_schema(db)
    numeric.require_schema(db)
    # Retail arrival must precede the decision and is atomic for both
    # markets. This calls ORIGINAL B capture_pair, not the Track C mock.
    first = retail.capture_pair(
        db, original_snapshot=original_snapshot,
        file_read_at=file_read_at, clock=receipt_clock,
        research_numeric_features=True,
    )
    if (first.get("status") != "BOTH_LOCAL_RETAIL_SOURCES_WITNESSED"
            or first.get("pilotCount") != 2
            or first.get("anonymousNumericResearchCaptured") is not True):
        raise ValueError("original_b_pair_capture_unverifiable")

    inserted = []
    def one_new_row(connection):
        cursor = insert_history(connection)
        if isinstance(cursor, sqlite3.Cursor):
            inserted.append(cursor.lastrowid)
        return cursor

    # This is the ORIGINAL B coordinator: inserts an actual new synthetic
    # Squalincome history event with original COT-price-ingest attestations,
    # resolves retail receipt as-of INSIDE the same decision transaction.
    decision = atomic.record_new(
        db, insert_history=one_new_row,
        original_document=original_price_document, clock=decision_clock,
        research_retail_inbox=True,
    )
    if (decision.get("status") !=
            "LOCAL_NEW_OBSERVATION_AND_THREE_PROOFS_ATOMIC" or
            decision.get("retailFirstSeen") !=
            "PINNED_LOCAL_RECEIPT_NOT_SIGNAL_INPUT" or
            decision.get("retailSelectedInsideOriginalDecision") is not True or
            len(inserted) != 1 or type(inserted[0]) is not int):
        raise ValueError("original_b_decision_handoff_unverifiable")

    # Important: read_linked comes from B and verifies the original same
    # receipt's six numeric values, SHA and scan time. Never return values to
    # CI/logs or reinterpret them as a signal.
    read = numeric.read_linked(db, history_id=inserted[0])
    if (read.get("status") !=
            "LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH" or
            read.get("retailInputToOriginalSignal") is not False or
            read.get("realEdgeEstablished") is not False or
            read.get("cvdCoverage") != "UNKNOWN"):
        raise ValueError("original_b_numeric_link_unverifiable")

    return {
        "state": "SYNTHETIC_PINNED_ORIGINAL_B_CHAIN_VERIFIED_NOT_LIVE",
        "retailReceipts": db.execute(
            f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0],
        "numericFeatures": db.execute(
            f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0],
        "newOriginalDecision": True,
        "originalRetailValuesReturned": False,
        "retailNotUsedByOriginalSignal": True,
        "cvdCoverage": "UNKNOWN",
        "providerTimestampsAuthenticated": False,
        "realOutcomesRecorded": False,
        "statisticalEdgeEstablished": False,
        "liveEnabled": False,
        "brokerCalls": 0,
        "ordersEnabled": False,
        "notificationsEnabled": False,
    }
