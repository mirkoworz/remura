"""REMURA Track B — custody inventory v0.1 LAB, 18/11/2026, session after 11:07 CET.

Owner-only, already recovered CLOSED copies. No decryption, extraction, backup,
source-row export, live ledger access, write, network or external attestation.
Use python -B -m scripts.shark_closed_custody_inventory --confirm-closed ROOT.
"""
from __future__ import annotations
import argparse
from collections import Counter
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

from scripts import shark_cvd_shard_backup as backup
from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_scan_coverage as scan

MAX_NODES=12000
MAX_DEPTH=12
MAX_DB_BYTES=64*1024*1024
MAX_SNAPSHOTS=64
LIMIT_SECONDS=120
TABLES=("research_cvd_observations",scan.TABLE,shards.META,
        "research_squalincome_cot_links","research_retail_original_first_seen",
        "research_first_periodic_invocation","research_retail_segment_metadata")
SIDECARS=("-wal","-shm","-journal")
LIVE=Path("/opt/remura")

def private_root(raw):
    p=Path(raw)
    if not p.is_absolute() or p.resolve()!=p or p==Path("/") or p==LIVE or LIVE in p.parents or p in LIVE.parents:
        raise ValueError("CLOSED_PRIVATE_ROOT_REQUIRED")
    s=p.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or s.st_mode&0o077:
        raise ValueError("CLOSED_PRIVATE_ROOT_REQUIRED")
    return p

def metadata(p,deadline):
    s=p.lstat()
    if not stat.S_ISREG(s.st_mode) or not 100<=s.st_size<=MAX_DB_BYTES or p.resolve()!=p:
        raise ValueError("CLOSED_DATABASE_REQUIRED")
    if any(os.path.lexists(str(p)+x) for x in SIDECARS):
        raise ValueError("CLOSED_DATABASE_SIDECAR")
    with p.open("rb") as f:
        header=f.read(100)
    # Immutable reads are only appropriate for owner-confirmed closed
    # standalone copies. Do not interpret a WAL-mode header as complete.
    if header[:16]!=b"SQLite format 3\x00" or header[18:20]!=b"\x01\x01":
        raise ValueError("CLOSED_DATABASE_HEADER")
    with closing(sqlite3.connect(p.as_uri()+"?mode=ro&immutable=1",uri=True,timeout=1)) as db:
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        db.set_progress_handler(lambda:int(time.monotonic()>deadline),1000)
        names={row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 4097")}
        if len(names)>4096:
            raise ValueError("SCHEMA_LIMIT")
    z=p.lstat()
    fingerprint=lambda a:(a.st_dev,a.st_ino,a.st_size,a.st_mtime_ns,a.st_ctime_ns)
    if fingerprint(s)!=fingerprint(z) or any(os.path.lexists(str(p)+x) for x in SIDECARS):
        raise ValueError("COPY_CHANGED")
    return names

def inventory(raw,*,confirmed_closed=False):
    if confirmed_closed is not True:
        raise ValueError("OWNER_CLOSED_COPY_CONFIRMATION_REQUIRED")
    root=private_root(raw)
    counts=Counter()
    tables=Counter({name:0 for name in TABLES})
    candidates=[]
    deadline=time.monotonic()+LIMIT_SECONDS
    def onerror(_):
        counts["unreadable_nodes"]+=1
    for folder,dirs,files in os.walk(root,topdown=True,followlinks=False,onerror=onerror):
        p=Path(folder)
        counts["nodes_seen"]+=len(dirs)+len(files)
        if counts["nodes_seen"]>MAX_NODES or time.monotonic()>deadline:
            counts["truncated"]+=1
            break
        depth=len(p.relative_to(root).parts)
        if depth>=MAX_DEPTH and dirs:
            counts["truncated"]+=1
            dirs[:]=[]
        for name in list(dirs):
            if (p/name).is_symlink():
                counts["symlinks_skipped"]+=1
                dirs.remove(name)
        if backup.MANIFEST in files:
            if len(candidates)>=MAX_SNAPSHOTS:
                counts["truncated"]+=1
            else:
                candidates.append(p)
        for name in files:
            if time.monotonic()>deadline:
                counts["truncated"]+=1
                break
            item=p/name
            if item.is_symlink():
                counts["symlinks_skipped"]+=1
                continue
            if shards.NAME.fullmatch(name):
                counts["shard_named_occurrences"]+=1
            if name.endswith(".seal.json"):
                counts["seal_named_occurrences"]+=1
            if not name.lower().endswith((".sqlite",".sqlite3",".db")):
                continue
            counts["sqlite_occurrences"]+=1
            try:
                names=metadata(item,deadline)
                counts["sqlite_schema_read"]+=1
                counts["sqlite_with_research_tables"]+=int(any(n.startswith("research_") for n in names))
                for n in TABLES:
                    tables[n]+=int(n in names)
            except (OSError,ValueError,sqlite3.Error):
                counts["sqlite_unverified"]+=1
    for p in candidates:
        if time.monotonic()>deadline:
            counts["truncated"]+=1
            break
        counts["snapshot_manifest_candidates"]+=1
        try:
            # Use the existing B verifier on a complete, private, closed copy.
            # Never invoke the writer lock or create_snapshot/restore_snapshot.
            children=list(p.iterdir())
            if len(children)>2*shards.MAX_SHARDS+32:
                raise ValueError("SNAPSHOT_LIMIT")
            for item in children:
                if item.is_symlink() or not item.is_file() or item.name.endswith(SIDECARS):
                    raise ValueError("SNAPSHOT_NOT_CLOSED")
                if shards.NAME.fullmatch(item.name):
                    names=metadata(item,deadline)
                    if not {scan.TABLE,shards.META}.issubset(names):
                        raise ValueError("SHARD_SCHEMA_MISSING")
            result=backup.verify_snapshot(p)
            counts["locally_verified_snapshot_occurrences"]+=1
            counts["verified_segment_occurrences"]+=result["segments"]
        except (OSError,ValueError,sqlite3.Error,KeyError,TypeError):
            counts["unverified_snapshot_candidates"]+=1
    partial=any(counts[k] for k in ("truncated","unreadable_nodes","symlinks_skipped","sqlite_unverified","unverified_snapshot_candidates"))
    return {"schema":"remura.shark.closed.custody.inventory.v1",
            "status":"PARTIAL" if partial else "CLOSED_COPY_INVENTORY_ONLY",
            "counts":{k:counts[k] for k in ("nodes_seen","sqlite_occurrences","sqlite_schema_read",
            "sqlite_with_research_tables","sqlite_unverified","shard_named_occurrences","seal_named_occurrences",
            "snapshot_manifest_candidates","locally_verified_snapshot_occurrences","verified_segment_occurrences",
            "unverified_snapshot_candidates","unreadable_nodes","symlinks_skipped","truncated")},
            "known_table_occurrences":dict(tables),"unique_databases_attested":False,
            "all_archives_attested":False,"external_authentication":False,
            "absence_elsewhere_proven":False,"writes_or_live_changes":False,"edge_established":False}

def main():
    p=argparse.ArgumentParser(description="Closed owner copies only; output aggregate schema counts.")
    p.add_argument("root",type=Path)
    p.add_argument("--confirm-closed",action="store_true",required=True)
    a=p.parse_args()
    try:
        print(json.dumps(inventory(a.root,confirmed_closed=a.confirm_closed),sort_keys=True))
    except (OSError,ValueError):
        print('{"status":"STOP_CLOSED_PRIVATE_ROOT_REQUIRED"}')
        return 2
    return 0

if __name__=="__main__":
    raise SystemExit(main())
