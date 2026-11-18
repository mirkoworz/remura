"""REMURA Track B — closed custody reconciliation v0.2 LAB, 18/11/2026, after 15:49 CET.
Owner-local closed recovered copies only. No backup, extraction, network, writes,
source rows, path/digest exports, or evaluation of prospective outcomes.
Requires Python with SQLite deserialize; run as ordinary owner, not root.
"""
import argparse
from collections import Counter
from contextlib import closing
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import time

TABLES=("research_cvd_observations","research_cvd_scan_attempts",
        "research_cvd_shard_metadata","research_squalincome_cot_links",
        "research_retail_original_first_seen","research_first_periodic_invocation",
        "research_retail_segment_metadata")
LIMIT=64*1024*1024
TOTAL=256*1024*1024
NODES=12000
SECONDS=90
SIDECARS=("-wal","-shm","-journal")

def need(ok):
    if not ok:raise ValueError("CLOSED_CUSTODY_GATE")

def stamp(s):
    return s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_nlink,s.st_size,s.st_mtime_ns,s.st_ctime_ns

def closed_bytes(fd,name,deadline):
    def sidecar_absent():
        for suffix in SIDECARS:
            try:os.stat(name+suffix,dir_fd=fd,follow_symlinks=False)
            except FileNotFoundError:continue
            raise ValueError("SIDECAR")
    sidecar_absent()
    a=os.stat(name,dir_fd=fd,follow_symlinks=False)
    need(stat.S_ISREG(a.st_mode) and a.st_uid==os.getuid()
         and not a.st_mode&0o022 and 100<=a.st_size<=LIMIT)
    f=os.open(name,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK|os.O_CLOEXEC,dir_fd=fd)
    try:
        need(stamp(a)==stamp(os.fstat(f)))
        with os.fdopen(os.dup(f),"rb") as stream:
            data=stream.read(a.st_size+1)
        need(len(data)==a.st_size and time.monotonic()<deadline)
        need(stamp(a)==stamp(os.fstat(f))==stamp(os.stat(name,dir_fd=fd,follow_symlinks=False)))
        sidecar_absent()
        need(data[:16]==b"SQLite format 3\x00" and data[18:20]==b"\x01\x01")
        return data
    finally:os.close(f)

def schema(data,deadline):
    with closing(sqlite3.connect(":memory:")) as db:
        db.deserialize(data)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        db.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
        names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 4097")}
        need(len(names)<=4096 and time.monotonic()<deadline)
        return frozenset(n for n in TABLES if n in names)

def reconcile(raw,*,confirmed_closed=False):
    need(confirmed_closed is True and os.geteuid()!=0 and hasattr(sqlite3.Connection,"deserialize"))
    root=Path(raw)
    live=Path("/opt/remura")
    need(root.is_absolute() and root==root.resolve() and root!=Path("/")
        and root!=Path.home() and live!=root and live not in root.parents and root not in live.parents)
    s=root.lstat()
    need(stat.S_ISDIR(s.st_mode) and s.st_uid==os.getuid() and not s.st_mode&0o077)
    deadline=time.monotonic()+SECONDS
    counts=Counter()
    known=Counter({n:0 for n in TABLES})
    seen={}
    used=0
    def error(_):counts["unverified"]+=1
    for folder,dirs,files,fd in os.fwalk(root,follow_symlinks=False,onerror=error):
        if counts["nodes"]+len(dirs)+len(files)>NODES or time.monotonic()>=deadline:
            counts["truncated"]+=1
            break
        counts["nodes"]+=len(dirs)+len(files)
        ds=os.fstat(fd)
        if ds.st_uid!=os.getuid() or ds.st_mode&0o022:
            dirs.clear();counts["unverified"]+=1;continue
        if len(Path(folder).relative_to(root).parts)>=12 and dirs:
            dirs.clear();counts["truncated"]+=1
        for name in list(dirs):
            try:
                st=os.stat(name,dir_fd=fd,follow_symlinks=False)
                if stat.S_ISLNK(st.st_mode):dirs.remove(name);counts["unverified"]+=1
            except OSError:
                dirs.remove(name);counts["unverified"]+=1
        for name in files:
            if not name.lower().endswith((".sqlite",".sqlite3",".db")):continue
            counts["occurrences"]+=1
            try:
                size=os.stat(name,dir_fd=fd,follow_symlinks=False).st_size
                if used+size>TOTAL:
                    counts["truncated"]+=1;continue
                data=closed_bytes(fd,name,deadline)
                used+=len(data)
                digest=hashlib.sha256(data).digest()
                if digest not in seen:
                    seen[digest]=schema(data,deadline)
                    counts["distinct_verified_byte_groups"]+=1
                    for table in seen[digest]:known[table]+=1
                else:counts["duplicate_verified_occurrences"]+=1
                counts["verified_occurrences"]+=1
            except (OSError,ValueError,sqlite3.Error,OverflowError):
                counts["unverified"]+=1
            if time.monotonic()>=deadline:
                counts["truncated"]+=1
                break
    return {"schema":"remura.shark.closed.custody.reconcile.v1",
            "status":"PARTIAL" if counts["unverified"] or counts["truncated"] else "SCOPED_BYTE_RECONCILIATION_ONLY",
            "counts":{k:counts[k] for k in ("occurrences","verified_occurrences","distinct_verified_byte_groups","duplicate_verified_occurrences","unverified","truncated")},
            "table_presence_in_distinct_byte_groups":dict(known),
            "logical_database_identity_attested":False,"all_archives_attested":False,
            "external_authentication":False,"absence_elsewhere_proven":False,
            "outcomes_evaluated":False,"edge_established":False,"writes":False}

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("root",type=Path)
    p.add_argument("--confirm-closed",action="store_true",required=True)
    a=p.parse_args()
    try:result=reconcile(a.root,confirmed_closed=a.confirm_closed)
    except (OSError,ValueError,sqlite3.Error):
        print('{"status":"STOP_CLOSED_OWNER_COPY_REQUIRED"}');return 2
    print(json.dumps(result,sort_keys=True))
    return 0
if __name__=="__main__":raise SystemExit(main())
