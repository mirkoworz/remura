"""Track B OFFLINE: private consistent CVD scan shard backup + restore.

Backs up the *entire* standalone sharded scan ledger, not OCI, cTrader price
storage, COT/price causal graph, HMAC secret or the full REMURA deployment.
No network/CLI/scheduler, no VPS access, no source mutation or pruning.

All copies stay in pre-existing private parent directories (0700), use new
output directories, 0600 files, strong per-file SHA256 and a manifest written
LAST. The live writable shard uses sqlite3.Connection.backup() while the
cooperating writer is locked; sealed shards retain byte-for-byte DB hashes.
The restore never overwrites, invents timestamps or backfills M15 slots.
No external signature/notary: an attacker able to rewrite all backup files
and the manifest is outside this offline integrity model.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import stat

from scripts import shark_cvd_sharded_ledger as shards

SCHEMA="remura-private-cvd-shard-snapshot-v1"
MANIFEST="snapshot-manifest.json"
MAX_MANIFEST_BYTES=150_000
RETAINED=re.compile(r"^unpublished-retained-\.cvd-init-[A-Za-z0-9_.-]+\.sqlite3$")


def _private_parent(target):
    path=Path(target)
    if (path.exists() or path.is_symlink() or
            not path.parent.is_dir() or path.parent.is_symlink()
            or stat.S_IMODE(path.parent.stat().st_mode)&0o077):
        raise ValueError("new_backup_directory_under_private_0700_parent_required")
    return path


def _inventory(folder,segments, *, is_snapshot=False):
    valid={shards._name(seq) for seq,_,_ in segments}
    valid.update(shards._seal_name(seq) for seq,_,sealed in segments if sealed)
    valid.update(p.name for p in folder.iterdir() if RETAINED.fullmatch(p.name))
    actual={p.name for p in folder.iterdir()}
    actual.discard(".cvd-shards.lock")
    if is_snapshot:
        actual.discard(MANIFEST)
    if actual!=valid:
        raise ValueError("unexpected_or_missing_cvd_archive_files")
    for name in valid:
        path=folder/name
        if (path.is_symlink() or not path.is_file()
                or stat.S_IMODE(path.stat().st_mode)&0o077):
            raise ValueError("private_cvd_archive_file_untrusted")
    return sorted(valid)


def _new_dir(target):
    target.mkdir(mode=0o700,parents=False,exist_ok=False)
    shards._fsync_dir(target.parent)


def _new_file(target,source,*, active=False):
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,"O_NOFOLLOW",0)
    fd=os.open(target,flags,0o600)
    os.close(fd)
    if active:
        with shards._readonly(source) as src,sqlite3.connect(target) as dst:
            src.execute("PRAGMA query_only=ON")
            src.backup(dst)
            if dst.execute("PRAGMA integrity_check").fetchone()[0]!="ok":
                raise ValueError("snapshot_active_sqlite_integrity_failed")
    else:
        with source.open("rb") as src, target.open("wb") as out:
            shutil.copyfileobj(src,out,length=1024*1024)
            out.flush()
            os.fsync(out.fileno())
    with target.open("rb") as stream:
        os.fsync(stream.fileno())


def _snapshot_manifest(files,segments,total):
    return {
        "schema":SCHEMA,
        "sourceLedgerSchema":shards.SCHEMA,
        "scope":"ONLY_PRIVATE_CVD_SCAN_SHARDS_AND_LOCAL_SEALS",
        "sourceSnapshots":"EXCLUSIVE_COOPERATING_WRITER_LOCK_AND_SQLITE_BACKUP_FOR_ACTIVE",
        "allArchivedSegments":len(segments),
        "sealedSegments":sum(int(sealed) for _,_,sealed in segments),
        "totalObservedAttempts":total,
        "maxRowsPerSegment":shards.PER_SHARD,
        "files":files,
        "containsHmacKey":False,
        "containsRawOhlcOrBrokerMapping":False,
        "isEntireRemuraOrOCIBackup":False,
        "sourceDataDeleted":False,
        "externallyAuthenticated":False,
        "provesUnobservedScansAbsent":False,
        "edgeEstablished":False,
    }


def _publish_manifest(target,doc):
    raw=(json.dumps(doc,sort_keys=True,separators=(",",":"),
                    ensure_ascii=True,allow_nan=False)+"\n").encode("ascii")
    if len(raw)>MAX_MANIFEST_BYTES:
        raise ValueError("cvd_snapshot_manifest_too_large")
    tmp=target/".snapshot-manifest-incomplete"
    flags=os.O_CREAT|os.O_EXCL|os.O_WRONLY|getattr(os,"O_NOFOLLOW",0)
    fd=os.open(tmp,flags,0o600)
    with os.fdopen(fd,"wb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    os.link(tmp,target/MANIFEST)
    tmp.unlink()
    shards._fsync_dir(target)


def _file_hash(path):
    if path.is_symlink() or not path.is_file():
        raise ValueError("cvd_snapshot_file_missing_or_symlink")
    h=hashlib.sha256()
    size=0
    with path.open("rb") as stream:
        for part in iter(lambda:stream.read(1024*1024),b""):
            size+=len(part)
            if size>shards.MAX_SHARD_FILE_BYTES:
                raise ValueError("cvd_snapshot_file_oversized")
            h.update(part)
    return {"name":path.name,"sha256":h.hexdigest(),"bytes":size}


def create_snapshot(source_root,destination):
    """Create a new local-only private folder; never overwrite a backup.

    If interrupted before manifest publication, the incomplete destination
    must be reviewed manually. It is NOT promoted to a valid snapshot.
    """
    destination=_private_parent(destination)
    with shards._exclusive(source_root) as root:
        segments,_,total,_=shards._inspect(root)
        names=_inventory(root,segments)
        _new_dir(destination)
        for name in names:
            src=root/name
            dst=destination/name
            match=shards.NAME.fullmatch(name)
            active=bool(match and int(match[1])==len(segments)
                        and segments and not segments[-1][2])
            _new_file(dst,src,active=active)
        # Validate the entire replicated chain before committing manifest.
        copy_segments,_,copied_total,_=shards._inspect(destination)
        if copy_segments!=segments or copied_total!=total:
            raise ValueError("cvd_snapshot_row_or_chain_mismatch")
        files=[_file_hash(destination/name) for name in names]
        _publish_manifest(destination,_snapshot_manifest(files,segments,total))
    return verify_snapshot(destination)


def verify_snapshot(destination):
    """Read-only self-consistency of the private snapshot and its local hash."""
    root=shards._root(destination)
    path=root/MANIFEST
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_MANIFEST_BYTES:
        raise ValueError("cvd_snapshot_not_finalized")
    try:
        doc=json.loads(path.read_bytes())
    except (OSError,ValueError) as exc:
        raise ValueError("cvd_snapshot_manifest_invalid") from exc
    expected_fields={"schema","sourceLedgerSchema","scope","sourceSnapshots",
                     "allArchivedSegments","sealedSegments","totalObservedAttempts",
                     "maxRowsPerSegment","files","containsHmacKey",
                     "containsRawOhlcOrBrokerMapping","isEntireRemuraOrOCIBackup",
                     "sourceDataDeleted","externallyAuthenticated",
                     "provesUnobservedScansAbsent","edgeEstablished"}
    if (not isinstance(doc,dict) or set(doc)!=expected_fields
            or doc["schema"]!=SCHEMA or doc["sourceLedgerSchema"]!=shards.SCHEMA
            or doc["scope"]!="ONLY_PRIVATE_CVD_SCAN_SHARDS_AND_LOCAL_SEALS"
            or doc["sourceSnapshots"]!="EXCLUSIVE_COOPERATING_WRITER_LOCK_AND_SQLITE_BACKUP_FOR_ACTIVE"
            or doc["maxRowsPerSegment"]!=shards.PER_SHARD
            or any(doc[k] is not False for k in (
                "containsHmacKey","containsRawOhlcOrBrokerMapping",
                "isEntireRemuraOrOCIBackup","sourceDataDeleted",
                "externallyAuthenticated","provesUnobservedScansAbsent",
                "edgeEstablished")) or not isinstance(doc["files"],list)):
        raise ValueError("cvd_snapshot_manifest_contract_invalid")
    file_names=[item.get("name") for item in doc["files"]
                if isinstance(item,dict)]
    if len(file_names)!=len(doc["files"]) or len(set(file_names))!=len(file_names):
        raise ValueError("cvd_snapshot_file_manifest_invalid")
    actual={p.name for p in root.iterdir()}
    if actual!={MANIFEST,*file_names}:
        raise ValueError("cvd_snapshot_missing_or_extra_files")
    for item in doc["files"]:
        if (set(item)!={"name","sha256","bytes"}
                or not isinstance(item["name"],str) or "/" in item["name"]
                or item["name"] in (".","..") or item["name"].startswith(".")
                or not isinstance(item["sha256"],str)
                or not shards.HEX.fullmatch(item["sha256"])
                or type(item["bytes"]) is not int):
            raise ValueError("cvd_snapshot_file_manifest_invalid")
        if _file_hash(root/item["name"])!=item:
            raise ValueError("cvd_snapshot_file_hash_mismatch")
    segments,_,count,_=shards._inspect(root)
    if (len(segments)!=doc["allArchivedSegments"]
            or sum(int(x[2]) for x in segments)!=doc["sealedSegments"]
            or count!=doc["totalObservedAttempts"]
            or set(file_names)!=set(_inventory(root,segments,is_snapshot=True))):
        raise ValueError("cvd_snapshot_chain_or_count_mismatch")
    return {
        "status":"PRIVATE_CVD_SHARD_SNAPSHOT_VERIFIED_LOCAL_ONLY",
        "segments":len(segments),"observedAttempts":count,
        "storedFiles":len(file_names),
        "notAnOCIBackup":True,"hmacKeyIncluded":False,
        "originalDataPruned":False,"independentSignature":False,
        "readyForVpsDeployment":False,"brokerCalls":0,
    }


def restore_snapshot(snapshot,target):
    """Replay all byte-verified files to an unused private 0700 directory.

    Does not import missing CVD observations, invent attempts, overwrite an
    existing directory, or automatically delete partially restored files.
    """
    verify_snapshot(snapshot)
    dest=_private_parent(target)
    source=shards._root(snapshot)
    manifest=json.loads((source/MANIFEST).read_bytes())
    _new_dir(dest)
    for entry in manifest["files"]:
        name=entry["name"]
        _new_file(dest/name,source/name)
        if _file_hash(dest/name)!=entry:
            raise ValueError("cvd_restore_file_hash_mismatch")
    segments,_,total,_=shards._inspect(dest)
    if (len(segments)!=manifest["allArchivedSegments"]
            or total!=manifest["totalObservedAttempts"]):
        raise ValueError("cvd_restore_row_count_mismatch")
    _publish_manifest(dest,manifest)
    result=verify_snapshot(dest)
    return {**result,"status":"PRIVATE_CVD_SHARD_RESTORED_AND_VERIFIED",
            "existingDataOverwritten":False,"missingScansBackfilled":False}
