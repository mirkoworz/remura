"""Track B: zero-network, PRIVATE SQLite research sample census (aggregate only).

No broker data, SSH, remote host, credentials or external SDK. It NEVER writes
to the operational REMURA database and never logs individual OHLC, events,
broker symbols, account IDs or private paths. To use on real data, the operator
must run this tool against an already-accessible local SQLite snapshot AFTER
coordinating with the live release process; GitHub CI uses synthetic fixtures.

The report counts *point-in-time potentially eligible observational outcomes*.
It does not establish that COT revisions, historical H1, broker quotes, trades
or CVD detection timestamps were immutably attested at each observation.
"""
from __future__ import annotations

from collections import Counter
from contextlib import closing
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sqlite3
from urllib.parse import quote

from scripts import shark_cot_paired_baseline as baseline
from scripts import shark_data_readiness as readiness

SCHEMA = "remura-shark-research-census-v1"
MAX_ROWS = 50000
HORIZONS = baseline.HORIZONS
PILOT = baseline.PILOT


def _count(db, query, parameters=()):
    value = db.execute(query, parameters).fetchone()[0]
    if type(value) is not int or value < 0 or value > MAX_ROWS:
        raise ValueError("bounded_research_counts_only")
    return value


def audit_connection(db, *, as_of):
    """Return only aggregate counts, with evidence gaps kept explicit."""
    if not isinstance(db, sqlite3.Connection):
        raise ValueError("sqlite_connection_required")
    now = baseline._utc(as_of)
    present = baseline._table_names(db)
    tables = {
        key: key in present for key in
        ("prices", "cot_first_seen", "squalincome_history",
         "squalincome_validation_cohorts", "squalincome_validation_outcomes")
    }
    for table in ("squalincome_history",
                  "squalincome_validation_cohorts",
                  "squalincome_validation_outcomes"):
        if tables[table]:
            _count(db, "SELECT count(*) FROM " + table)
    price_audit = readiness.audit_connection(db)
    cases, excluded, received, missing = baseline._verified_cases(db, now)
    if received > MAX_ROWS:
        raise ValueError("too_many_raw_outcomes")
    by_symbol = {s: [] for s in PILOT}
    for record in cases:
        by_symbol[record["symbol"]].append(record)
    markets = {}
    for sym in PILOT:
        history = price_audit["markets"][sym]
        if tables["squalincome_validation_cohorts"]:
            cohorts = _count(db,
                "SELECT count(*) FROM squalincome_validation_cohorts "
                "WHERE symbol=? AND stage='observation'", (sym,))
        else:
            cohorts = 0
        rows = by_symbol[sym]
        horizons = []
        for h in HORIZONS:
            eligible = [c for c in rows if c["horizon"] == h]
            weeks = len({c["week"] for c in eligible})
            if tables["squalincome_validation_outcomes"] and tables["squalincome_validation_cohorts"]:
                persisted = _count(db,
                    "SELECT count(*) FROM squalincome_validation_outcomes o "
                    "JOIN squalincome_validation_cohorts c "
                    "ON c.symbol=o.symbol AND c.report_date=o.report_date "
                    "AND c.stage=o.stage "
                    "WHERE c.stage='observation' AND c.symbol=? "
                    "AND o.horizon_hours=?", (sym, h))
            else:
                persisted = 0
            descriptive = len(eligible) >= 30 and weeks >= 8
            horizons.append({
                "hours": h,
                "recordedOutcomeRows": persisted,
                "pointInTimeEligible": len(eligible),
                "cotWeeksEligible": weeks,
                "sampleGate": "DESCRIPTIVE_ONLY" if descriptive else "INSUFFICIENT",
                "netPnLValidated": False,
            })
        markets[sym] = {
            "archivedM15": history["archivedM15"],
            "authenticFirstObservations": history["authenticFirstObservations"],
            "initialCohortsPersisted": cohorts,
            "contextCohortsPossiblyUsable": history["priceContextOnly"],
            "contextExclusionCounts": history["cohortReasons"],
            "historicalOutcomes": horizons,
            "realtimeCvdRecordings": None,  # no LIVE recorder yet
        }
    return {
        "schema": SCHEMA, "status": "PRIVATE_READ_ONLY_RESEARCH",
        "tablesAvailable": tables,
        "markets": markets,
        "outcomeRowsExamined": received,
        "outcomeLineageExclusions": dict(sorted(excluded.items())),
        "missingValidationTables": missing,
        "cvdHistoryAvailable": False,
        "historicalCandleVersionsAttested": False,
        "cotValueVersionsAttested": False,
        "brokerQuotesAndSpreadMeasured": False,
        "historicalAsOfH1SnapshotsAttested": False,
        "actualTradingEdgeEstablished": False,
        "dataInterpretation": "observational_correlated_not_independent_oos",
        "recommendation": (
            "VERIFY_ORIGINAL_DATA_AND_COLLECT_MORE_REAL_EVENTS"
            if all(row["sampleGate"] == "INSUFFICIENT"
                   for m in markets.values() for row in m["historicalOutcomes"])
            else "DESCRIPTIVE_RESEARCH_ONLY_NO_TRADING_CLAIM"
        ),
        "ordersEnabled": False, "notificationsEnabled": False,
        "brokerCalls": 0,
    }


def audit_path(db_path, *, as_of):
    """SQLite URI read-only, no create, attach or schema mutation."""
    if not isinstance(db_path, (str, Path)):
        raise ValueError("invalid_path_type")
    path = Path(db_path).expanduser().resolve(strict=True)
    if not path.is_file():
        raise ValueError("not_a_file")
    uri = "file:" + quote(str(path), safe="/") + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=3)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")  # one point-in-time read transaction
        return audit_connection(db, as_of=as_of)


def main():
    """No private path in CLI arguments or printed error messages."""
    try:
        path = os.environ.get("REMURA_RESEARCH_DB_PATH", "")
        now = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        report = audit_path(path, as_of=now)
        print(json.dumps(report, ensure_ascii=True, sort_keys=True,
                         separators=(",", ":")))
        return 0
    except Exception:
        # Fail closed, including corrupt DB, missing file, and permission errors.
        print("SHARK_RESEARCH_CENSUS=NON_COMPLETATO")
        print("MOTIVO=ARCHIVIO_O_CONNESSIONE_NON_VALIDI")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
