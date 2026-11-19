"""Track B research-only: prospective Myfxbook incremental-value readiness.

No predictor is trained, no outcomes are read, no OOS claim is produced.
Counts only the authentic original-decision denominator visible to the
research SQLite connection, never the whole 34-market scan universe.
The original numeric receipt is consulted solely via read_linked().
Missing values are UNKNOWN, not bearish/bullish; repeated decisions
and correlated COT weeks are not independent observations.

Only synthetic ephemeral SQLite files are used in --storage-probe.
No Oracle, service, scheduler, API, paid storage or LIVE operations.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
import hashlib
import json
from pathlib import Path
import sqlite3
import tempfile

from scripts import shark_cot_asof_witness as clocks
from scripts import shark_cvd_incremental_protocol as frozen
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric

SCHEMA = "remura-retail-prospective-incremental-readiness-v1"
MAX_AUDIT_ROWS = 10000
MIN_COHORTS_PER_FOLD = 30
MIN_COT_WEEKS_PER_FOLD = 8
FOLDS = ("train", "validation", "test")
# These are a PLAN, not selected boundaries or an active statistical study.
# Freeze distinct calendar boundaries and analysis before any actual outcomes.
PRESPECIFIED_COMPARISON = {
    "baseline": "same eligible COT-price-only decisions",
    "incremental": "same decisions plus original pre-decision retail six",
    "featureHandling": "long-minus-short percentage; four optional counts/volumes",
    "missingPolicy": "UNKNOWN; no zero, no negative, no forward fill",
    "samplingUnit": "independent COT publication week; market overlap clustered",
    "splitPolicy": "chronological, COT week grouped, purge by evaluated_at, embargo",
    "foldRequirements": "30 matured decisions and 8 distinct COT weeks per fold",
    "costs": "same observed spread, slippage and fees on paired decisions",
    "testUse": "single untouched test after training and validation are locked",
    "scoreAndPnlStatus": "NOT_MEASURED",
}


def _has_table(db, name):
    return db.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",
        (name,)
    ).fetchone() is not None


def audit(db, *, as_of):
    """Read-only causal/missingness coverage, NOT a trading backtest.

    A valid receipt is local evidence, not an externally authenticated
    provider timestamp. The audit never reads mutable retail/latest.json,
    never obtains future outcomes and never declares statistical power.
    """
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("offline_research_sqlite_connection_required")
    if type(as_of) is not datetime:
        raise ValueError("explicit_asof_utc_required")
    now = clocks._clock(as_of)
    if frozen.protocol_sha256() != frozen.FROZEN_PROTOCOL_SHA256:
        raise ValueError("frozen_cvd_protocol_mismatch")
    start = clocks._parse(frozen.START)
    if now < start:
        raise ValueError("study_not_started_at_requested_asof")
    if not _has_table(db, "squalincome_history"):
        raise ValueError("original_decision_history_schema_missing")
    rows = db.execute(
        "SELECT id,symbol,observed_at FROM squalincome_history "
        "WHERE symbol IN ('EURUSD','XAUUSD') AND observed_at>=? "
        "ORDER BY id LIMIT ?",
        (clocks._iso(start), MAX_AUDIT_ROWS + 1)
    ).fetchall()
    if len(rows) > MAX_AUDIT_ROWS:
        raise ValueError("research_audit_denominator_capacity_exceeded")
    available = all(_has_table(db, t) for t in
                    (retail.TABLE, retail.LINK, numeric.TABLE))
    counts = Counter()
    distinct_receipts = set()
    seen_weeks = set()
    audited = 0
    for history_id, symbol, observed_string in rows:
        try:
            observed = clocks._parse(observed_string)
        except (TypeError, ValueError):
            counts["REJECTED_INVALID_OBSERVATION_CLOCK"] += 1
            audited += 1
            continue
        if observed > now:
            continue  # This decision does not exist AS OF the requested clock.
        audited += 1
        seen_weeks.add((observed.isocalendar().year,
                        observed.isocalendar().week))
        if not available:
            counts["UNKNOWN_NUMERIC_ARCHIVE_NOT_ENABLED"] += 1
            continue
        try:
            # The original research link must itself have existed as-of.
            link = db.execute(
                f"SELECT linked_at,retail_witness_id FROM {retail.LINK} "
                "WHERE history_id=?", (history_id,)
            ).fetchone()
            if link is not None and clocks._parse(link[0]) > now:
                counts["UNKNOWN_LINK_NOT_YET_KNOWN_ASOF"] += 1
                continue
            result = numeric.read_linked(db, history_id=history_id)
        except (ValueError, sqlite3.DatabaseError):
            counts["REJECTED_CAUSALITY_OR_INTEGRITY"] += 1
            continue
        status = result["status"]
        if status != "LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH":
            counts[status] += 1
            continue
        six = result["features"]
        # Null is missing, never a zero-flow/contrarian observation.
        if any(six[field] is None for field in numeric.FIELDS):
            counts["PARTIAL_SIX_METRICS_UNKNOWN"] += 1
        else:
            counts["COMPLETE_LOCAL_RESEARCH_CONTEXT"] += 1
        distinct_receipts.add(link[1])
    return {
        "schema": SCHEMA,
        "status": "OFFLINE_COVERAGE_ONLY_NOT_INCREMENTAL_PERFORMANCE",
        "denominator": "SQUALINCOME_ORIGINAL_DECISIONS_PILOT_ONLY",
        "pilotDecisionsAsOf": audited,
        "coverage": dict(sorted(counts.items())),
        "distinctLocalRetailReceiptsLinked": len(distinct_receipts),
        "distinctObservedUtcWeeksUpperBound": len(seen_weeks),
        "independentMarketSamplesProven": 0,
        "retailActuallyUsedByOriginalSqualincome": False,
        "originalValuesObtainedFromLaterFile": False,
        "providerClockIndependentlyAuthenticated": False,
        "providerRevisionsIndependentlyAuthenticated": False,
        "whole34MarketDenominatorCertified": False,
        "retailResearchEnabledOnLive": False,
        "retailIncrementalPredictiveValueMeasured": False,
        "outcomesRead": 0,
        "costsRead": 0,
        "purgedEmbargoedOosTestExecuted": False,
        "edgeEstablished": False,
        "newAPICalls": 0,
    }


def synthetic_storage_probe():
    """Measure exact 4500-row vault + original receipts and a full backup.

    This models the two *research* tables with the actual schema/algorithm,
    not the live DB, free OCI capacity, filesystem quota, or SQLite peak
    under concurrent writers. All paths and records are ephemeral.
    """
    with tempfile.TemporaryDirectory(prefix="remura-retail-lab-") as td:
        path = Path(td) / "private-synthetic.sqlite3"
        backup = Path(td) / "verified-backup.sqlite3"
        db = sqlite3.connect(str(path))
        try:
            db.execute("PRAGMA page_size=4096")
            db.execute("PRAGMA journal_mode=WAL")
            retail.ensure_schema(db)
            numeric.ensure_schema(db)
            start = clocks._parse(frozen.START)
            with db:
                for i in range(numeric.MAX_FEATURE_ROWS):
                    symbol = ("EURUSD", "XAUUSD")[i % 2]
                    stamp = clocks._iso(start + timedelta(minutes=i))
                    digest = hashlib.sha256(
                        ("synthetic-retail-original-" + str(i)).encode()
                    ).hexdigest()
                    rec = db.execute(
                        f"INSERT INTO {retail.TABLE}"
                        "(symbol,source_updated_at,original_read_at,"
                        "recorded_at,numeric_sha256,algorithm)"
                        " VALUES (?,?,?,?,?,?)",
                        (symbol, stamp, stamp, stamp, digest, retail.ALG)
                    ).lastrowid
                    # Deterministic mock aggregates; NOT actual Myfxbook data.
                    six = {"lPct": 62.5, "sPct": 37.5,
                           "lLots": 1200.5, "sLots": 800.25,
                           "lPos": 950, "sPos": 725}
                    numeric.append_inside_original_pair(
                        db, receipt_id=rec, symbol=symbol, entry=six,
                        original_sha=digest,
                        recorded_clock=start + timedelta(minutes=i)
                    )
            wal_path = Path(str(path) + "-wal")
            wal_peak_snapshot = wal_path.stat().st_size if wal_path.exists() else 0
            with sqlite3.connect(str(backup)) as target:
                db.backup(target)
            integrity = db.execute("PRAGMA integrity_check").fetchone()[0]
            db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            rows = db.execute(f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0]
            source_rows = db.execute(f"SELECT count(*) FROM {retail.TABLE}").fetchone()[0]
            page_count = db.execute("PRAGMA page_count").fetchone()[0]
            page_size = db.execute("PRAGMA page_size").fetchone()[0]
            with sqlite3.connect(str(backup)) as verified:
                restored_integrity = verified.execute(
                    "PRAGMA integrity_check").fetchone()[0]
                restored_rows = verified.execute(
                    f"SELECT count(*) FROM {numeric.TABLE}").fetchone()[0]
            if (rows != numeric.MAX_FEATURE_ROWS or source_rows != rows
                    or restored_rows != rows
                    or integrity != "ok" or restored_integrity != "ok"):
                raise ValueError("synthetic_storage_backup_or_row_count_invalid")
            main_bytes, backup_bytes = path.stat().st_size, backup.stat().st_size
            return {
                "schema": "retail-synthetic-storage-envelope-v1",
                "syntheticOnly": True,
                "featureRows": rows,
                "originalReceiptRows": source_rows,
                "hardFeatureRowLimit": numeric.MAX_FEATURE_ROWS,
                "pageSizeBytes": page_size,
                "pageCount": page_count,
                "mainDbBytes": main_bytes,
                "walBytesBeforeCheckpoint": wal_peak_snapshot,
                "restoredBackupBytes": backup_bytes,
                "mainPlusBackupPlusObservedWalBytes":
                    main_bytes + backup_bytes + wal_peak_snapshot,
                "backupRestoreIntegrity": "OK",
                "oracleFreeTierQuotaCertified": False,
                "maximumRuntimeWalOrDiskPeakCertified": False,
                "liveDbTotalStorageEstimated": False,
                "extraCloudServicesCreated": 0,
                "liveWrites": 0,
            }
        finally:
            db.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--storage-probe", action="store_true")
    args = parser.parse_args()
    if not args.storage_probe:
        parser.error("only --storage-probe is supported; no LIVE mode")
    print(json.dumps(synthetic_storage_probe(), sort_keys=True))
