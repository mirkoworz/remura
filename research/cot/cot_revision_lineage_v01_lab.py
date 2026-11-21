# REMURA Shark Science · COT revision lineage v0.1 LAB — 21/11/2026 Europe/Rome
"""Safe *candidate* for CFTC revisions, entirely offline and in-memory.

The existing Oracle collector is NOT edited by this candidate. A historical
COT row can be overwritten by ON CONFLICT DO UPDATE, while cot_first_seen
still describes the original row; using revised values at that original time
would create lookahead bias. This append-only side ledger isolates versions.

No migration, provider fetch, live SQLite, snapshot reconstruction or orders.
No external timestamp attestation: captured_at is a LOCAL CLOCK CLAIM only.
Legacy reports with no recorded version remain UNKNOWN for past decisions.
"""
from __future__ import annotations
from datetime import datetime, timezone, date
from hashlib import sha256
import json
import math
import re
import sqlite3

SCHEMA = "remura.cot.revision_lineage.v01.lab"
ALLOWED = {
    "tff": frozenset(("099741", "096742", "097741", "232741", "090741",
                      "092741", "112741", "13874A", "209742", "124603", "098662")),
    "disagg": frozenset(("088691", "084691", "067651")),
}
STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
MAX_BATCH = 3000
MAX_VERSIONS_PER_KEY = 12

class RevisionError(ValueError):
    pass

def parsed_stamp(text):
    if not isinstance(text, str) or not STAMP.fullmatch(text):
        raise RevisionError("utc_stamp_invalid")
    try:
        val = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise RevisionError("utc_stamp_invalid") from exc
    if val.strftime("%Y-%m-%dT%H:%M:%SZ") != text:
        raise RevisionError("utc_stamp_invalid")
    return val

def identify(dataset, code, report_date):
    if not (type(dataset) is str and dataset in ALLOWED and
            type(code) is str and code in ALLOWED[dataset] and
            type(report_date) is str and
            re.fullmatch(r"\d{4}-\d\d-\d\d", report_date)):
        raise RevisionError("unmapped_cftc_key")
    try:
        dt = date.fromisoformat(report_date)
    except ValueError as exc:
        raise RevisionError("report_date_invalid") from exc
    return dt

def normalized_rows(rows, at):
    if type(rows) is not dict or not 1 <= len(rows) <= MAX_BATCH:
        raise RevisionError("missing_or_oversized_batch")
    clean=[]
    for key, values in rows.items():
        if type(key) is not tuple or len(key)!=3:
            raise RevisionError("row_identity_invalid")
        dataset, code, report_date=key
        if identify(dataset,code,report_date) > at.date():
            raise RevisionError("future_report_date")
        if type(values) is not tuple or len(values)!=5 or any(
            type(v) not in (int,float) or not math.isfinite(v) or v<0 or v>1e11
            for v in values
        ):
            raise RevisionError("invalid_futures_positions")
        oi=values[0]
        if oi<=0 or any(x>oi*2 for x in values[1:]):
            raise RevisionError("invalid_open_interest")
        payload=[dataset,code,report_date,[float(v) for v in values]]
        digest=sha256(json.dumps(payload,separators=(",",":"),allow_nan=False)
                     .encode("ascii")).hexdigest()
        clean.append((dataset,code,report_date,digest))
    return sorted(clean)

class OfflineRevisionLedger:
    """Deliberately impossible to open a file or an operational database."""
    def __init__(self, *, synthetic=False):
        if synthetic is not True:
            raise RevisionError("offline_synthetic_opt_in_required")
        self._db=sqlite3.connect(":memory:")
        self._db.executescript("""
          CREATE TABLE captured_versions(
            dataset TEXT NOT NULL, code TEXT NOT NULL, report_date TEXT NOT NULL,
            version INTEGER NOT NULL, captured_at TEXT NOT NULL,
            content_sha256 TEXT NOT NULL,
            PRIMARY KEY(dataset,code,report_date,version),
            UNIQUE(dataset,code,report_date,content_sha256,captured_at)
          );
          CREATE INDEX version_asof_idx ON captured_versions(
            dataset,code,report_date,captured_at);
          CREATE TRIGGER versions_no_update BEFORE UPDATE ON captured_versions
            BEGIN SELECT RAISE(ABORT,'immutable_version'); END;
          CREATE TRIGGER versions_no_delete BEFORE DELETE ON captured_versions
            BEGIN SELECT RAISE(ABORT,'immutable_version'); END;
        """)
    def close(self):
        self._db.close()
    def capture(self, rows, *, at_utc):
        at=parsed_stamp(at_utc)
        valid=normalized_rows(rows,at)
        fresh=revisions=unchanged=0
        # All checks and inserts in a single local SQLite transaction.
        with self._db:
            for dataset,code,report,digest in valid:
                previous=self._db.execute("""
                    SELECT version,captured_at,content_sha256
                    FROM captured_versions WHERE dataset=? AND code=? AND report_date=?
                    ORDER BY version DESC LIMIT 1
                """,(dataset,code,report)).fetchone()
                if previous is None:
                    version=1
                    fresh+=1
                elif previous[2]==digest:
                    unchanged+=1
                    continue
                else:
                    if previous[1]>=at_utc:
                        raise RevisionError("revision_clock_not_strictly_later")
                    version=previous[0]+1
                    if version>MAX_VERSIONS_PER_KEY:
                        raise RevisionError("version_budget_exhausted")
                    revisions+=1
                self._db.execute("""
                    INSERT INTO captured_versions(dataset,code,report_date,version,
                        captured_at,content_sha256) VALUES(?,?,?,?,?,?)
                """,(dataset,code,report,version,at_utc,digest))
        return {
            "schema":SCHEMA,"status":"LOCAL_VERSION_LOG_ONLY",
            "fresh_versions":fresh,"revisions":revisions,"unchanged":unchanged,
            "external_clock_verified":False,"official_cftc_publication_verified":False,
            "revised_values_retroactively_promoted":False,
            "oracle_or_cloudflare_calls":0,"live_deploy_allowed":False
        }
    def as_of(self, *, dataset, code, report_date, decision_utc):
        decision=parsed_stamp(decision_utc)
        if identify(dataset,code,report_date)>decision.date():
            raise RevisionError("decision_before_report_reference")
        row=self._db.execute("""
          SELECT version,captured_at,content_sha256 FROM captured_versions
          WHERE dataset=? AND code=? AND report_date=? AND captured_at<=?
          ORDER BY version DESC LIMIT 1
        """,(dataset,code,report_date,decision_utc)).fetchone()
        return {
            "schema":SCHEMA,
            "status":"LOCAL_VERSION_AVAILABLE_UNATTESTED" if row else "UNKNOWN_NO_VERSION_AT_DECISION",
            "version":row[0] if row else None,
            "captured_at":row[1] if row else None,
            "content_sha256":row[2] if row else None,
            "external_first_seen_verified":False,
            "report_publication_verified":False,
            "cross_product_mapping_verified":False,
            "prospective_holdout_admission":False,
            "institutional_edge_established":False,
            "oracle_or_cloudflare_calls":0
        }
