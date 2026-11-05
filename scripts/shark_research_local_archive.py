"""REMURA Track B: OFFLINE, non-destructive local causal-evidence archive.

Exports the REQUIRED prospective COT/price/CVD evidence graph, including
Squalincome original history, into one ZIP, with typed JSONL records, source
CREATE TABLE / CREATE TRIGGER SQL, per-entry SHA256 and an overall bundle
hash. Two SQLite READ snapshots are independent, NOT one atomic join.

Hard guards: source connections must be PRAGMA query_only=ON; both complete
research schemas must exist; bounds on rows/uncompressed bytes; no overwrite;
atomic link of a 0600 local file; source rows never deleted, never backfilled.
An archive is NOT an OCI backup/restore certification, trading-data archive,
HMAC key, external attestation, an archival rotation or OOS dataset. It does
NOT include raw OHLC outcome paths, source price_store, COT mutable source or
the separate full-34 price-only batches. Never upload to GitHub/CI artifacts.
No network, broker, cloud, scheduler, production code imports or CLI.
"""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile

SCHEMA="remura-private-causal-evidence-export-v2"
LEGACY_SCHEMA="remura-private-causal-evidence-export-v1"
SCAN_TABLE="research_cvd_scan_attempts"
MAX_SCAN_ATTEMPTS=10000
MAIN_TABLES=(
    "squalincome_history",
    "research_cot_asof_attestations",
    "research_squalincome_cot_links",
    "research_squalincome_price_evidence",
    "research_squalincome_m15_prefix_proofs",
)
LEGACY_PRIVATE_TABLES=(
    "research_cvd_observations",
    "research_cvd_price_bindings",
    "research_cvd_m15_prefix_proofs",
)
PRIVATE_TABLES=(*LEGACY_PRIVATE_TABLES,SCAN_TABLE)
ALLOW={"main":MAIN_TABLES,"private":PRIVATE_TABLES}
MAX_TOTAL_ROWS=120000
MAX_TOTAL_BYTES=40_000_000
MAX_ARCHIVE_BYTES=25_000_000
ENTRY_PREFIX="evidence"
MANIFEST="manifest.json"


def _json(data):
    return (json.dumps(data,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False)+"\n").encode("ascii")


def _encode(value):
    if isinstance(value,bytes):
        return {"kind":"blob-base64","data":base64.b64encode(value).decode("ascii")}
    if value is None or type(value) in (str,int,float):
        return value
    raise ValueError("unsupported_sqlite_archive_cell")


def _checks(db, tables):
    if (not isinstance(db,sqlite3.Connection)
            or db.execute("PRAGMA query_only").fetchone()[0]!=1):
        raise ValueError("readonly_sqlite_connection_required")
    if db.execute("PRAGMA database_list").fetchone() is None:
        raise ValueError("missing_database")
    for table in tables:
        present=db.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
            (table,)).fetchone()
        if not present or not present[0]:
            raise ValueError("causal_provenance_table_missing:"+table)
        # Require historical append-only proof tables to retain their
        # immutability triggers, not only their row contents. History itself
        # is a legacy source table and is not immutable.
        if table.startswith("research_"):
            triggers=db.execute(
                "SELECT name,sql FROM sqlite_master WHERE type='trigger' "
                "AND tbl_name=?",(table,)).fetchall()
            if len(triggers)<2 or any(not x[1] for x in triggers):
                raise ValueError("causal_provenance_triggers_missing:"+table)
            if table==SCAN_TABLE:
                expected={"research_cvd_scan_no_update",
                          "research_cvd_scan_no_delete"}
                if not expected.issubset({name for name,_ in triggers}):
                    raise ValueError("cvd_scan_archive_immutability_missing")
                columns=tuple(c[1] for c in db.execute(
                    f"PRAGMA table_info({SCAN_TABLE})"))
                if columns!=("symbol","closed_at","attempted_at","state",
                            "source_hmac","session_prefix_hmac",
                            "new_confirmations","reason","schema_version"):
                    raise ValueError("cvd_scan_archive_v2_schema_required")
                versions=db.execute(
                    f"SELECT DISTINCT schema_version FROM {SCAN_TABLE} LIMIT 2").fetchall()
                if any(v[0]!="remura-track-b-cvd-scan-attempt-coverage-v2"
                       for v in versions):
                    raise ValueError("cvd_scan_archive_v2_rows_required")
                if db.execute(f"SELECT count(*) FROM {SCAN_TABLE}").fetchone()[0]>MAX_SCAN_ATTEMPTS:
                    raise ValueError("cvd_scan_archive_capacity_corrupt")


def _table_meta(db,table):
    source=db.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name=?",
        (table,)).fetchone()[0]
    cols=db.execute(f"PRAGMA table_info({table})").fetchall()
    if not cols or any(not isinstance(x[1],str) for x in cols):
        raise ValueError("unreadable_source_column_structure")
    triggers=[dict(name=x[0],sql=x[1]) for x in db.execute(
        "SELECT name,sql FROM sqlite_master WHERE type='trigger' "
        "AND tbl_name=? ORDER BY name",(table,))]
    return {
        "table":table,"columns":[c[1] for c in cols],
        "createTableSql":source,"triggers":triggers
    }


def _stable_order(db,table):
    """Sort by PRIMARY KEY: compatible with immutable WITHOUT ROWID tables."""
    cols=db.execute(f"PRAGMA table_info({table})").fetchall()
    keys=[c[1] for c in sorted(cols,key=lambda c:c[5]) if c[5]>0]
    return ",".join('"' + c.replace('"','""') + '"' for c in keys) if keys else "rowid"


def export_bundle(db_main,db_private,target, *,
                  max_rows=MAX_TOTAL_ROWS,max_bytes=MAX_TOTAL_BYTES):
    """Write a COMPLETE local-only, size-bounded, no-overwrite evidence pack.

    Source READ transactions are bounded and never committed; no source
    mutation, deletion or VACUUM. Caller must authorize both database reads
    and choose a private LOCAL destination outside the GitHub working tree.
    """
    if (type(max_rows) is not int or not 1<=max_rows<=MAX_TOTAL_ROWS
            or type(max_bytes) is not int
            or not 1024<=max_bytes<=MAX_TOTAL_BYTES):
        raise ValueError("archive_bounds_invalid")
    dest=Path(target)
    if dest.suffix!=".zip" or not dest.parent.is_dir():
        raise ValueError("local_archive_zip_destination_required")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("archive_must_not_overwrite")
    _checks(db_main,MAIN_TABLES)
    _checks(db_private,PRIVATE_TABLES)
    # Never claim that these are one global cross-database snapshot.
    own_main=not db_main.in_transaction
    own_private=not db_private.in_transaction
    if own_main:
        db_main.execute("BEGIN")
    if own_private:
        db_private.execute("BEGIN")
    tmp=None
    try:
        # Establish both read snapshots before any archive data are read.
        db_main.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        db_private.execute("SELECT name FROM sqlite_master LIMIT 1").fetchone()
        fd,path=tempfile.mkstemp(prefix=".remura-evidence-",suffix=".tmp",
                                 dir=str(dest.parent))
        tmp=Path(path)
        os.fchmod(fd,0o600)
        manifest={
            "schema":SCHEMA,
            "scope":"LOCAL_CAUSAL_PROVENANCE_ONLY",
            "snapshotSemantics":"INDEPENDENT_SQLITE_READ_SNAPSHOTS",
            "includesRawOHLCOrOutcomePaths":False,
            "includesPriceOnlyFull34Cohorts":False,
            "privateHmacSecretIncluded":False,
            "scanAttemptCoverageIncluded":True,
            "scanAttemptHmacCanBeRecomputedWithoutPrivateKey":False,
            "sourceDataDeleted":False,
            "freesSqliteCapacity":False,
            "completeOCIBackupOrRestore":False,
            "externallySignedOrNotarized":False,
            "tradingEdgeEstablished":False,
            "main":{},"private":{}
        }
        total_rows=0
        total_bytes=0
        try:
            with os.fdopen(fd,"wb") as stream:
                with zipfile.ZipFile(
                    stream,"w",compression=zipfile.ZIP_DEFLATED,
                    compresslevel=6,allowZip64=False
                ) as archive:
                    for scope,db in (("main",db_main),("private",db_private)):
                        for table in ALLOW[scope]:
                            meta=_table_meta(db,table)
                            entry=f"{ENTRY_PREFIX}/{scope}/{table}.jsonl"
                            digest=hashlib.sha256()
                            n=0
                            entry_bytes=0
                            with archive.open(entry,"w") as dest_data:
                                for row in db.execute(f"SELECT * FROM {table} ORDER BY {_stable_order(db,table)}"):
                                    packed=_json({"values":[_encode(v) for v in row]})
                                    n+=1
                                    total_rows+=1
                                    total_bytes+=len(packed)
                                    entry_bytes+=len(packed)
                                    if total_rows>max_rows or total_bytes>max_bytes:
                                        raise ValueError("archive_resource_limit_exceeded")
                                    dest_data.write(packed)
                                    digest.update(packed)
                            meta.update({
                                "entry":entry,"sha256":digest.hexdigest(),
                                "rows":n,"uncompressedBytes":entry_bytes})
                            manifest[scope][table]=meta
                    archive.writestr(MANIFEST,_json(manifest))
                stream.flush()
                os.fsync(stream.fileno())
            if tmp.stat().st_size>MAX_ARCHIVE_BYTES:
                raise ValueError("compressed_archive_exceeds_25mb_limit")
            # Verify BEFORE publishing. os.link is no-clobber; an unexpected
            # concurrent archive with same name is never replaced.
            report=verify_bundle(tmp)
            if report["rows"]!=total_rows:
                raise ValueError("export_verification_row_count_mismatch")
            os.link(tmp,dest)
            os.unlink(tmp)
            tmp=None
            return {
                **report,
                "archiveFileBytes":dest.stat().st_size,
                "sourceDatabaseModified":False,
                "sourceRowsDeleted":0,
                "readyForAutomaticPrune":False,
            }
        except BaseException:
            raise
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
        if own_private:
            db_private.rollback()
        if own_main:
            db_main.rollback()


def verify_bundle(path):
    """Verify exact schema, row counts, typed JSON, manifest and SHA hashes.

    No source DB or HMAC secret is needed. Returns only aggregate metadata.
    A valid checksum proves archive *integrity against accidental damage*,
    not a trustworthy external timestamp/signature or a complete backup.
    """
    target=Path(path)
    if not target.is_file() or target.stat().st_size>MAX_ARCHIVE_BYTES:
        raise ValueError("archive_missing_or_oversized")
    hashes={}
    total_rows=0
    try:
        with zipfile.ZipFile(target,"r") as z:
            # Inspect a bounded manifest before determining the exact table list.
            # Old v1 packs are verifiable but have NO CVD scan attempts.
            if MANIFEST not in z.namelist() or z.getinfo(MANIFEST).file_size>150000:
                raise ValueError("archive_manifest_missing_or_unbounded")
            raw=z.read(MANIFEST)
            if len(raw)>150000 or not raw.endswith(b"\n"):
                raise ValueError("archive_manifest_unbounded")
            doc=json.loads(raw)
            version=doc.get("schema")
            if version not in (SCHEMA,LEGACY_SCHEMA):
                raise ValueError("archive_manifest_schema_unrecognized")
            included={"main":MAIN_TABLES,
                      "private":PRIVATE_TABLES if version==SCHEMA
                      else LEGACY_PRIVATE_TABLES}
            expected={MANIFEST}
            expected.update(f"{ENTRY_PREFIX}/{scope}/{t}.jsonl"
                            for scope,tables in included.items() for t in tables)
            if set(z.namelist())!=expected or len(z.namelist())!=len(expected):
                raise ValueError("archive_entries_or_crc_invalid")
            # ZIP size cap checked before inflating any data entry.
            if (any(z.getinfo(name).file_size>MAX_TOTAL_BYTES
                    for name in expected if name!=MANIFEST)
                    or sum(z.getinfo(name).file_size for name in expected
                           if name!=MANIFEST)>MAX_TOTAL_BYTES):
                raise ValueError("uncompressed_archive_resource_limit")
            if (set(doc["main"])!=set(MAIN_TABLES)
                or set(doc["private"])!=set(included["private"])
                or doc.get("sourceDataDeleted") is not False
                or doc.get("includesRawOHLCOrOutcomePaths") is not False
                or (version==SCHEMA and
                    (doc.get("scanAttemptCoverageIncluded") is not True
                     or doc.get("scanAttemptHmacCanBeRecomputedWithoutPrivateKey") is not False))):
                raise ValueError("archive_manifest_contract_invalid")
            for scope,tables in included.items():
                for t in tables:
                    m=doc[scope][t]
                    entry=f"{ENTRY_PREFIX}/{scope}/{t}.jsonl"
                    if (m.get("table")!=t or m.get("entry")!=entry
                            or not isinstance(m.get("columns"),list)
                            or not m["columns"]
                            or not isinstance(m.get("createTableSql"),str)
                            or not isinstance(m.get("triggers"),list)
                            or len(m["triggers"])< (0 if t=="squalincome_history" else 2)):
                        raise ValueError("archive_table_metadata_invalid")
                    hasher=hashlib.sha256()
                    count=0
                    length=0
                    with z.open(entry) as data:
                        while True:
                            line=data.readline(500001)
                            if not line:
                                break
                            if len(line)>500000 or not line.endswith(b"\n"):
                                raise ValueError("archive_row_unbounded_or_noncanonical")
                            count+=1
                            total_rows+=1
                            length+=len(line)
                            if total_rows>MAX_TOTAL_ROWS or length>MAX_TOTAL_BYTES:
                                raise ValueError("archive_verify_resource_limit")
                            packed=json.loads(line)
                            fields=packed.get("values")
                            if not isinstance(fields,list) or len(fields)!=len(m["columns"]):
                                raise ValueError("archive_row_shape_invalid")
                            for cell in fields:
                                if isinstance(cell,dict):
                                    if set(cell)!={"kind","data"} or cell["kind"]!="blob-base64":
                                        raise ValueError("archive_blob_encoding_invalid")
                                    base64.b64decode(cell["data"],validate=True)
                                elif cell is not None and type(cell) not in (int,float,str):
                                    raise ValueError("archive_cell_type_invalid")
                            hasher.update(line)
                    if (count!=m.get("rows")
                            or length!=m.get("uncompressedBytes")
                            or hasher.hexdigest()!=m.get("sha256")):
                        raise ValueError("archive_hash_or_count_mismatch")
                    if t==SCAN_TABLE and count>MAX_SCAN_ATTEMPTS:
                        raise ValueError("archive_cvd_scan_attempts_exceed_hard_limit")
                    hashes[f"{scope}.{t}"]=count
    except (zipfile.BadZipFile,KeyError,TypeError,json.JSONDecodeError) as e:
        raise ValueError("invalid_archive_bundle") from e
    blob=hashlib.sha256()
    with target.open("rb") as f:
        for part in iter(lambda:f.read(1024*1024),b""):
            blob.update(part)
    scan_count=hashes.get("private."+SCAN_TABLE)
    scan_capacity=None if scan_count is None else {
        "archivedAttempts":scan_count,
        "hardLimitRows":MAX_SCAN_ATTEMPTS,
        "remainingRowsInArchivedSnapshot":MAX_SCAN_ATTEMPTS-scan_count,
        "status":("AT_HARD_LIMIT" if scan_count==MAX_SCAN_ATTEMPTS
                  else "WARNING_95_PERCENT" if scan_count*100>=95*MAX_SCAN_ATTEMPTS
                  else "WARNING_80_PERCENT" if scan_count*100>=80*MAX_SCAN_ATTEMPTS
                  else "WITHIN_LOCAL_HARD_LIMIT"),
        "doesNotFreeOriginalSQLiteCapacity":True,
        "isNotLiveDiskOrBillingUsage":True,
    }
    return {
        "schema":version,
        "status":"LOCAL_ARCHIVE_INTEGRITY_VERIFIED",
        "sha256":blob.hexdigest(),
        "rows":total_rows,
        "tableRowCounts":hashes,
        "cvdScanAttemptCapacity":scan_capacity,
        "cvdScanAttemptHmacIndependentVerification":False,
        "sourceIndependentTimestampAuthenticated":False,
        "sourceDatabaseModified":False,
        "freesSqliteCapacity":False,
        "readyForAutomaticPrune":False,
        "brokerCalls":0,
        "tradingEdgeEstablished":False
    }
