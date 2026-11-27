"""Track C2c-d: synthetic cross-process as-of audit of ORIGINAL B evidence.

NO live recorder, data fetch, CFTC signature, cloud connection, trading,
prediction, file creation, migrations or alerts. This is a READ-ONLY check
of TWO distinct synthetic SQLite stores:
- C: explicitly named temporary COT HTTP ledger written by C's rehearsal.
- B: single in-memory DB with B's original cTrader FIRST-SEEN, COT,
  two-market Myfxbook numeric FIRST-SEEN, and new Squalincome decisions.

Verifies COT source digests and receipt clocks match the ORIGINAL B
value witnesses, plus B's original price/retail decision proofs. Cross-DB
timestamps are self-reported and the commits are NOT cross-DB atomic.
A passing check is NEVER authentic prospective market evidence.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

MODE = "OFFLINE_SYNTHETIC_TWO_MARKET_SOURCE_JOIN_ONLY"
SCHEMA = "remura-track-c-cross-process-original-b-asof-v1"
PILOT = {"EURUSD": ("tff", "099741"), "XAUUSD": ("disagg", "088691")}
MAX_HTTP_TO_B_WITNESS = timedelta(minutes=2)


def _stores(cot_db, science_db):
    if type(cot_db) is not sqlite3.Connection or type(science_db) is not sqlite3.Connection:
        raise ValueError("explicit_synthetic_sqlite_connections_required")
    for db in (cot_db, science_db):
        if db.in_transaction:
            raise ValueError("read_only_clean_transaction_required")
        if db.execute("PRAGMA query_only").fetchone()[0] != 1:
            raise ValueError("read_only_connection_required")
    left = cot_db.execute("PRAGMA database_list").fetchall()
    right = science_db.execute("PRAGMA database_list").fetchall()
    if len(left) != 1 or len(right) != 1 or right[0][2]:
        raise ValueError("science_must_be_single_in_memory_database")
    if left[0][1] != "main" or right[0][1] != "main" or not left[0][2]:
        raise ValueError("no_attached_or_ambiguous_sqlite_databases")
    from scripts import track_c_cot_atomic_b_witness as bridge
    source_file = Path(left[0][2]).resolve()
    root = Path(tempfile.gettempdir()).resolve()
    if source_file.name != bridge.FILE_NAME or not source_file.is_relative_to(root):
        raise ValueError("only_original_synthetic_cot_temp_file_allowed")


def audit(cot_db, science_db, *, original_history_ids, mode=None):
    """Audit two original B decisions against COT post-response metadata.

    The actual COT cache exists in both *independent* stores only because
    the fixtures placed equivalent original values there. This function
    checks content/clock correspondence rather than inventing cross-DB ACID.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_cross_process_mode_required")
    _stores(cot_db, science_db)

    from scripts import shark_cot_asof_witness as witness
    from scripts import shark_retail_numeric_features as numeric
    from scripts import shark_ingest_first_seen as ingest
    from scripts import shark_signal_ingest_decision_link as source_link
    from scripts import shark_signal_evidence as signal
    from scripts import shark_retail_preregistered_protocol as retail_protocol
    from scripts import shark_cvd_incremental_protocol as cvd
    from scripts import track_c_cot_atomic_b_witness as bridge

    if (cvd.protocol_sha256() != cvd.FROZEN_PROTOCOL_SHA256
            or cvd.FROZEN_PROTOCOL_SHA256 !=
            "09d833dafdd426254bc8fedccc367e41fa451ac8f2e6c99a9dac27f7387e2905"
            or retail_protocol.fingerprint() != retail_protocol.FROZEN_RULES_SHA256
            or retail_protocol.FROZEN_RULES_SHA256 !=
            "6c4413a9851233e0785cb86eb30a03a22e8fa0a20efd4385c22638cba2ba4f6e"):
        raise ValueError("pinned_B_protocol_drift")
    if (type(original_history_ids) is not dict
            or set(original_history_ids) != set(PILOT)
            or any(type(i) is not int or i <= 0 for i in original_history_ids.values())
            or len(set(original_history_ids.values())) != 2):
        raise ValueError("exact_two_new_original_pilot_decisions_required")

    # The COT side's HTTP ledger was explicitly migrated by a lab test.
    for table in (bridge.TABLE, witness.TABLE, "cot_reports"):
        row = cot_db.execute(
            "SELECT type FROM sqlite_master WHERE name=?", (table,)
        ).fetchone()
        if row is None or row[0] != "table":
            raise ValueError("original_cot_ledger_schema_missing")
    receipts = cot_db.execute(
        f"SELECT dataset,request_started_at,response_received_at,"
        f"witnessed_at,normalized_row_count,normalized_sha256 FROM {bridge.TABLE}"
    ).fetchall()
    if len(receipts) != 2 or {r[0] for r in receipts} != {"tff", "disagg"}:
        raise ValueError("both_exact_original_http_receipts_required")

    source_clocks = {}
    for ds, started, received, recorded, n, sha in receipts:
        a, b, c = map(witness._parse, (started, received, recorded))
        if (not a <= b <= c or a < witness._parse(cvd.START)
                or c - b > bridge.MAX_INGEST_AFTER_HTTP
                or b - a > bridge.MAX_RESPONSE_SPAN):
            raise ValueError("noncausal_original_cot_http_clock")
        rows = cot_db.execute(
            "SELECT dataset,code,report_date,oi,first_long,first_short,"
            "second_long,second_short FROM cot_reports WHERE dataset=? "
            "ORDER BY code,report_date", (ds,)
        ).fetchall()
        if len(rows) != n or not rows or n > witness.MAX_SOURCE_ROWS:
            raise ValueError("cot_http_receipt_row_count_mismatch")
        hashes = []
        for kind, code, week, *values in rows:
            digest = witness._digest(tuple(values))
            hashes.append((kind, code, week, digest))
            proof = cot_db.execute(
                f"SELECT witnessed_at FROM {witness.TABLE} WHERE "
                "dataset=? AND code=? AND report_date=? AND value_digest=?",
                (kind, code, week, digest)
            ).fetchall()
            if len(proof) != 1 or witness._parse(proof[0][0]) != c:
                raise ValueError("cot_source_and_http_witness_mismatch")
        expected = hashlib.sha256(
            json.dumps(sorted(hashes), separators=(",", ":"),
                       ensure_ascii=True, allow_nan=False).encode("ascii")
        ).hexdigest()
        if sha != expected:
            raise ValueError("cot_http_original_sha_mismatch")
        source_clocks[ds] = (b, c)

    seen = 0
    for symbol, (ds, code) in PILOT.items():
        history_id = original_history_ids[symbol]
        row = science_db.execute(
            "SELECT symbol,report_date,observed_at,price_time FROM "
            "squalincome_history WHERE id=?", (history_id,)
        ).fetchone()
        if row is None or row[0] != symbol:
            raise ValueError("original_history_id_or_symbol_mismatch")
        _, current, observed_str, closed_str = row
        observed = witness._parse(observed_str)
        closed = witness._parse(closed_str)
        received, cot_recorded = source_clocks[ds]
        if not (received <= cot_recorded <= observed
                and closed <= observed and observed-closed <= timedelta(minutes=3)):
            raise ValueError("original_cot_source_was_not_available_asof")

        # First read the exact prior and current B COT versions; require
        # the identical COT source rows and digests from C's receipt store.
        dates = science_db.execute(
            "SELECT report_date FROM cot_reports WHERE dataset=? AND code=? "
            "ORDER BY report_date", (ds, code)
        ).fetchall()
        weeks = [w[0] for w in dates]
        if (len(weeks) != 2 or weeks[-1] != current
                or (witness._parse(current+"T00:00:00Z") -
                    witness._parse(weeks[0]+"T00:00:00Z")).days != 7):
            raise ValueError("original_pilot_cot_week_mismatch")
        for week in weeks:
            parts = science_db.execute(
                "SELECT oi,first_long,first_short,second_long,second_short "
                "FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
                (ds, code, week)
            ).fetchone()
            source = cot_db.execute(
                "SELECT oi,first_long,first_short,second_long,second_short "
                "FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
                (ds, code, week)
            ).fetchone()
            if parts is None or source is None or parts != source:
                raise ValueError("cross_process_original_cot_values_differ")
            digest = witness._digest(parts)
            b_proof = science_db.execute(
                f"SELECT witnessed_at FROM {witness.TABLE} WHERE "
                "dataset=? AND code=? AND report_date=? AND value_digest=?",
                (ds, code, week, digest)
            ).fetchall()
            if len(b_proof) != 1:
                raise ValueError("original_b_cot_witness_does_not_match")
            btime = witness._parse(b_proof[0][0])
            if not (cot_recorded <= btime <= observed
                    and btime - cot_recorded <= MAX_HTTP_TO_B_WITNESS):
                raise ValueError("cross_process_cot_reached_science_too_late")

        # ORIGINAL B validates decision-local COT+price+ingest attestation
        # and exact six Myfxbook metrics pinned at first-seen. Values are
        # deliberately discarded, never exposed through C or CI metadata.
        linked = science_db.execute(
            f"SELECT original_ingest_proof_id FROM {source_link.TABLE} "
            "WHERE history_id=?", (history_id,)
        ).fetchall()
        if len(linked) != 1 or type(linked[0][0]) is not int:
            raise ValueError("original_b_cot_price_ingest_link_missing")
        cot_link = science_db.execute(
            f"SELECT source_version_evidence FROM {signal.TABLE} WHERE "
            "symbol=? AND cot_week=? AND price_closed_at=?",
            (symbol, current, closed_str)
        ).fetchall()
        if len(cot_link) != 1:
            raise ValueError("original_b_decision_cot_source_link_missing")
        versions = json.loads(cot_link[0][0])
        for week in weeks:
            digest = witness._digest(science_db.execute(
                "SELECT oi,first_long,first_short,second_long,second_short "
                "FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",
                (ds, code, week)
            ).fetchone())
            if not any(entry.get("dataset") == ds
                       and entry.get("code") == code
                       and entry.get("week") == week
                       and entry.get("digest") == digest
                       and witness._parse(entry["witnessed"]) <= observed
                       for entry in versions):
                raise ValueError("original_decision_missing_cot_version")

        from price_store import latest
        document = latest(science_db, symbol)
        if document is None:
            raise ValueError("original_merged_cTrader_document_missing")
        verified = ingest.verify_scan(
            science_db, symbol=symbol, current_document=document,
            scan_at=observed,
        )
        if verified.get("status") != "LOCAL_SAME_MERGED_DOCUMENT_MATCHED":
            raise ValueError("original_b_cTrader_first_seen_unverifiable")
        retail = numeric.read_linked(science_db, history_id=history_id)
        if (retail.get("status") !=
                "LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH"
                or retail.get("retailInputToOriginalSignal") is not False
                or retail.get("cvdCoverage") != "UNKNOWN"
                or retail.get("realEdgeEstablished") is not False):
            raise ValueError("retail_original_provenance_unverifiable")
        seen += 1

    return {
        "schema": SCHEMA,
        "status": "SYNTHETIC_TWO_MARKET_COT_PRICE_RETAIL_DECISION_CHAIN_ONLY",
        "researchMarketsValidated": seen,
        "localHttpDatasetReceipts": len(receipts),
        "originalBDecisionLinksValidated": seen,
        "distinctDbTransactions": True,
        "crossDatabaseAtomicityProven": False,
        "localClockProviderSigned": False,
        "sourceWasActualRetailSignalInput": False,
        "cvd": "UNKNOWN",
        "actualMarketData": False,
        "actualOOSOutcomes": False,
        "realEdgeEstablished": False,
        "liveEnabled": False,
        "additionalApiCalls": 0,
        "notificationsEnabled": False,
        "ordersEnabled": False,
    }
