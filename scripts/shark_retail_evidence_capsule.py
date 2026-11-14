"""REMURA Track B: private, OFFLINE original retail evidence capsules.

A self-contained pre-prune snapshot of a *specified* set of ORIGINAL
EURUSD/XAUUSD decision rows and their already-linked Myfxbook receipts.
One query-only SQLite read snapshot, no source writes, backfills or API calls.
Capsules preserve the values necessary to revalidate the existing numeric
FIRST-SEEN link after the ordinary 30-day Squalincome history is pruned.

The archive contains private original Squalincome evidence and six Myfxbook
aggregate metrics: use a restricted local 0700 directory. NEVER upload
to GitHub, Actions artifacts or public object stores. No encryption,
external signature, external provider clock attestation, off-host restore,
retention policy or live activation is supplied here. This is NOT a
replacement for SQLite backups, and never permits deleting source data.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import zipfile

from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from scripts import shark_signal_ingest_decision_link as signal

SCHEMA="remura-track-b-private-retail-original-capsule-v1"
MANIFEST="manifest.json"
CAPSULES="original-capsules.jsonl"
HISTORY="squalincome_history"
MAX_CAPSULES=256
MAX_UNCOMPRESSED=8_000_000
MAX_COMPRESSED=5_000_000
MAX_LINE_BYTES=150_000
TABLES=(HISTORY,signal.TABLE,retail.LINK,retail.TABLE,numeric.TABLE)
KINDS=("history","source","retailLink","receipt","features")
PILOT=frozenset(("EURUSD","XAUUSD"))


def _json(value):
    return (json.dumps(value,sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False)+"\n").encode("ascii")


def _cols(db,table):
    # All table names are constants from first-party modules, never input.
    cols=[row[1] for row in db.execute(f"PRAGMA table_info({table})")]
    if not cols:
        raise ValueError("private_retail_archive_schema_missing")
    return cols


def _fetch(db,table,key,ident,cols):
    cursor=db.execute(f"SELECT * FROM {table} WHERE {key}=?",(ident,))
    row=cursor.fetchone()
    if row is None:
        return None
    if cursor.fetchone() is not None:
        raise ValueError("non_unique_original_archive_source")
    values=dict(zip(cols,row))
    # Only bounded canonical scalar SQLite values, never binary broker files.
    if any(v is not None and type(v) not in (int,float,str)
           for v in values.values()):
        raise ValueError("unsupported_private_archive_sqlite_cell")
    return values


def _preflight(db,history_ids,target):
    if (not isinstance(db,sqlite3.Connection) or db.in_transaction
            or db.execute("PRAGMA query_only").fetchone()[0]!=1):
        raise ValueError("read_only_clean_sqlite_connection_required")
    if (type(history_ids) not in (tuple,list) or not history_ids
            or len(history_ids)>MAX_CAPSULES
            or any(type(x) is not int or x<=0 for x in history_ids)
            or len(set(history_ids))!=len(history_ids)):
        raise ValueError("bounded_unique_explicit_history_ids_required")
    dest=Path(target)
    if dest.suffix!=".zip" or not dest.parent.is_dir():
        raise ValueError("private_archive_destination_required")
    if dest.exists() or dest.is_symlink():
        raise FileExistsError("archive_never_overwrites")
    # Reject public / shared folders, including the GitHub workspace.
    if dest.parent.stat().st_mode & 0o077:
        raise ValueError("private_archive_parent_must_be_0700")
    return dest


def _capsule(db,ident,cols):
    history=_fetch(db,HISTORY,"id",ident,cols[HISTORY])
    if history is None or history.get("symbol") not in PILOT:
        raise ValueError("original_pilot_history_not_available_before_prune")
    source=_fetch(db,signal.TABLE,"history_id",ident,cols[signal.TABLE])
    link=_fetch(db,retail.LINK,"history_id",ident,cols[retail.LINK])
    receipt=features=None
    if link is not None:
        receipt=_fetch(db,retail.TABLE,"id",link.get("retail_witness_id"),
                       cols[retail.TABLE])
        if receipt is None or source is None:
            raise ValueError("linked_original_retail_proof_is_incomplete")
        features=_fetch(db,numeric.TABLE,"receipt_id",
                        link.get("retail_witness_id"),cols[numeric.TABLE])
    return {"history":history,"source":source,"retailLink":link,
            "receipt":receipt,"features":features}


def _validate_capsule(capsule):
    if type(capsule) is not dict or set(capsule)!=set(KINDS):
        raise ValueError("invalid_original_retail_capsule_shape")
    h=capsule["history"]
    if (type(h) is not dict or type(h.get("id")) is not int
            or h["id"]<=0 or h.get("symbol") not in PILOT
            or type(h.get("observed_at")) is not str):
        raise ValueError("invalid_original_decision_capsule")
    src,link,receipt,feat=(capsule[k] for k in
                           ("source","retailLink","receipt","features"))
    if src is not None and (
            type(src) is not dict or src.get("history_id")!=h["id"]):
        raise ValueError("invalid_original_ingest_link_capsule")
    if link is None:
        if receipt is not None or feat is not None:
            raise ValueError("unlinked_retail_values_forbidden")
        return "UNKNOWN_NO_ORIGINAL_RETAIL_LINK"
    if (type(link) is not dict or link.get("history_id")!=h["id"]
            or link.get("symbol")!=h["symbol"]
            or link.get("observed_at")!=h["observed_at"]
            or src is None or type(receipt) is not dict
            or receipt.get("id")!=link.get("retail_witness_id")
            or receipt.get("symbol")!=h["symbol"]):
        raise ValueError("original_retail_capsule_lineage_broken")
    if feat is not None and (
            type(feat) is not dict
            or feat.get("receipt_id")!=receipt["id"]
            or feat.get("symbol")!=h["symbol"]):
        raise ValueError("retail_feature_capsule_id_mismatch")
    # Reconstruct ONLY a trusted *fixed* five-table validation view.
    # NEVER execute SQL from the archive or from its manifest.
    memory=sqlite3.connect(":memory:")
    try:
        memory.executescript(f"""
            CREATE TABLE {HISTORY}(
                id INTEGER PRIMARY KEY,symbol TEXT,observed_at TEXT);
            CREATE TABLE {signal.TABLE}(
                history_id INTEGER PRIMARY KEY,
                observed_at_utc TEXT,linked_at_utc TEXT);
            CREATE TABLE {retail.LINK}(
                history_id INTEGER PRIMARY KEY,retail_witness_id INTEGER,
                symbol TEXT,observed_at TEXT,linked_at TEXT,
                original_numeric_sha256 TEXT);
            CREATE TABLE {retail.TABLE}(
                id INTEGER PRIMARY KEY,symbol TEXT,source_updated_at TEXT,
                original_read_at TEXT,recorded_at TEXT,numeric_sha256 TEXT);
            CREATE TABLE {numeric.TABLE}(
                receipt_id INTEGER PRIMARY KEY,symbol TEXT,
                original_sha256 TEXT,recorded_at TEXT,
                long_pct REAL,short_pct REAL,long_lots REAL,short_lots REAL,
                long_positions INTEGER,short_positions INTEGER,
                features_sha256 TEXT,algorithm TEXT);
        """)
        for table,record,fields in (
            (HISTORY,h,("id","symbol","observed_at")),
            (signal.TABLE,src,("history_id","observed_at_utc","linked_at_utc")),
            (retail.LINK,link,("history_id","retail_witness_id","symbol",
                              "observed_at","linked_at","original_numeric_sha256")),
            (retail.TABLE,receipt,("id","symbol","source_updated_at",
                                  "original_read_at","recorded_at","numeric_sha256")),
            (numeric.TABLE,feat,("receipt_id","symbol","original_sha256",
                                "recorded_at","long_pct","short_pct","long_lots",
                                "short_lots","long_positions","short_positions",
                                "features_sha256","algorithm"))):
            if record is not None:
                # Fixed field order, parameterized values, no archive SQL.
                values=[record[k] for k in fields]
                memory.execute(f"INSERT INTO {table} VALUES("
                               +",".join("?" for _ in fields)+")",values)
        result=numeric.read_linked(memory,history_id=h["id"])
        status=result["status"]
        if feat is not None:
            if status!="LOCAL_ORIGINAL_RETAIL_NUMERIC_CONTEXT_FOR_RESEARCH":
                raise ValueError("original_numeric_capsule_failed_revalidation")
            return "COMPLETE_LOCAL_ORIGINAL_NUMERIC_LINK"
        if status!="UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN":
            raise ValueError("unverifiable_missing_numeric_context")
        return "UNKNOWN_NUMERIC_FEATURE_NOT_CAPTURED_AT_FIRST_SEEN"
    except (KeyError,sqlite3.DatabaseError) as exc:
        raise ValueError("malformed_private_retail_capsule") from exc
    finally:
        memory.close()


def verify_archive(path):
    """Verify size, hashes and original numeric linkage WITHOUT original DB.

    No file is executed, and original Myfxbook numbers are never returned.
    A local hash proves neither external source authenticity nor OOS edge.
    """
    path=Path(path)
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_mode & 0o077
            or path.stat().st_size>MAX_COMPRESSED):
        raise ValueError("private_retail_archive_missing_or_unsafe")
    try:
        with zipfile.ZipFile(path,"r") as z:
            names=z.namelist()
            if len(names)!=2 or set(names)!={MANIFEST,CAPSULES}:
                raise ValueError("private_capsule_entries_invalid")
            if (z.getinfo(MANIFEST).file_size>15000
                    or z.getinfo(CAPSULES).file_size>MAX_UNCOMPRESSED):
                raise ValueError("private_capsule_uncompressed_limit")
            manifest=json.loads(z.read(MANIFEST))
            if (type(manifest) is not dict
                    or manifest.get("schema")!=SCHEMA
                    or manifest.get("status")!="LOCAL_PRIVATE_SNAPSHOT_NOT_BACKUP"):
                raise ValueError("private_capsule_manifest_invalid")
            raw=z.read(CAPSULES)
            if len(raw)>MAX_UNCOMPRESSED or not raw.endswith(b"\n"):
                raise ValueError("private_capsule_payload_invalid")
            if hashlib.sha256(raw).hexdigest()!=manifest.get("payloadSha256"):
                raise ValueError("private_capsule_digest_mismatch")
            lines=raw.splitlines()
            if not 1<=len(lines)<=MAX_CAPSULES or len(lines)!=manifest.get("records"):
                raise ValueError("private_capsule_record_count_invalid")
            seen=set()
            complete=unknown=0
            for line in lines:
                if len(line)>MAX_LINE_BYTES:
                    raise ValueError("private_capsule_row_too_large")
                data=json.loads(line)
                decision_id=data["history"]["id"]
                if decision_id in seen:
                    raise ValueError("duplicate_archive_original_decision")
                seen.add(decision_id)
                status=_validate_capsule(data)
                if status=="COMPLETE_LOCAL_ORIGINAL_NUMERIC_LINK":
                    complete+=1
                else:
                    unknown+=1
            if complete!=manifest.get("completeLocalLinks") or unknown!=manifest.get("unknownRetail"):
                raise ValueError("private_capsule_census_mismatch")
    except (KeyError,TypeError,UnicodeDecodeError,json.JSONDecodeError,
            zipfile.BadZipFile) as exc:
        raise ValueError("malformed_private_retail_archive") from exc
    return {
        "schema":SCHEMA,
        "status":"LOCAL_RETAIL_HISTORY_CAPSULE_VERIFIED_NOT_LIVE_GO",
        "originalDecisionsPreserved":len(seen),
        "completeLocalNumericLinks":complete,
        "retailUnknownPreserved":unknown,
        "privateLocalArchiveOnly":True,
        "usableAfterOriginalSqliteHistoryPrune":True,
        "providerSignedReceipt":False,
        "authenticMarketOutcomesMeasured":False,
        "offHostRecoveryVerified":False,
        "liveAuthorized":False,
        "sourceWrites":0,
        "additionalBrokerOrMyfxbookCalls":0,
        "statisticalEdgeEstablished":False,
    }


def export_archive(db,target,*,history_ids):
    """Create a NO-OVERWRITE 0600 ZIP from one single SQLite read snapshot.

    Caller supplies ORIGINAL row IDs before pruning. No scheduled exports.
    Each pack holds at most 256 decisions; multiple packs require separate
    controlled destinations and an explicit future retention/index policy.
    """
    dest=_preflight(db,history_ids,target)
    cols={table:_cols(db,table) for table in TABLES}
    db.execute("BEGIN")
    temp=None
    try:
        # Read the original five tables in ONE query-only SQLite snapshot.
        rows=[]
        complete=unknown=0
        for ident in sorted(history_ids):
            capsule=_capsule(db,ident,cols)
            kind=_validate_capsule(capsule)
            complete+=int(kind=="COMPLETE_LOCAL_ORIGINAL_NUMERIC_LINK")
            unknown+=int(kind!="COMPLETE_LOCAL_ORIGINAL_NUMERIC_LINK")
            rows.append(_json(capsule))
        if any(len(r)>MAX_LINE_BYTES for r in rows):
            raise ValueError("private_capsule_row_too_large")
        payload=b"".join(rows)
        if len(payload)>MAX_UNCOMPRESSED:
            raise ValueError("private_capsule_total_bytes_exceeded")
        manifest={
            "schema":SCHEMA,"status":"LOCAL_PRIVATE_SNAPSHOT_NOT_BACKUP",
            "records":len(rows),"payloadSha256":hashlib.sha256(payload).hexdigest(),
            "completeLocalLinks":complete,"unknownRetail":unknown,
            "singleSqliteSourceReadSnapshot":True,
            "sourceDataDeleted":False,"sourceRowsModified":0,
            "includesPrivateRetailMetrics":True,"atRestEncryption":False,
            "externallySignedOrAttested":False,"offHostRestoreVerified":False,
            "authorizesLiveOrPrune":False,
        }
        fd,name=tempfile.mkstemp(prefix=".remura-retail-",suffix=".tmp",
                                 dir=str(dest.parent))
        temp=Path(name)
        os.fchmod(fd,0o600)
        with os.fdopen(fd,"wb") as stream:
            with zipfile.ZipFile(stream,"w",zipfile.ZIP_DEFLATED,
                                 compresslevel=6,allowZip64=False) as z:
                z.writestr(CAPSULES,payload)
                z.writestr(MANIFEST,_json(manifest))
            stream.flush()
            os.fsync(stream.fileno())
        if temp.stat().st_size>MAX_COMPRESSED:
            raise ValueError("private_capsule_compressed_limit")
        result=verify_archive(temp)
        os.link(temp,dest)  # no-clobber atomic publish in same private folder
        return {**result,"noOverwrite":True,"originalDBModified":False,
                "automaticPruningAuthorized":False}
    finally:
        if temp is not None:
            temp.unlink(missing_ok=True)
        db.rollback()
