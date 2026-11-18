"""REMURA Track B — closed custody reconciliation v0.4 LAB, 18/11/2026, after 18:27 CET.
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
SOURCE_TABLES=("prices","status","cot_reports","cot_first_seen")
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

# Metadata requirements for the existing exact causal audit; names alone
# are insufficient. No data row query, no proof of valid trigger semantics.
CAUSAL_COLUMNS={
    "squalincome_history":("symbol","report_date","price_time","observed_at","state","cot_side","price_state"),
    "research_squalincome_cot_links":("symbol","cot_week","price_closed_at","observed_at","linked_at","cot_side","price_state","source_version_evidence","evidence_digest","algorithm"),
    "research_squalincome_price_evidence":("symbol","report_date","price_time","observed_at","witnessed_at","source_document_sha256","m15_closed_at","h1_closed_at","h4_closed_at","last16_tick_volume_complete","algorithm"),
    "research_cot_asof_attestations":("dataset","code","report_date","value_digest","witnessed_at","evidence_kind")
}
CAUSAL_TRIGGERS={
    "research_squalincome_cot_links":("research_squalincome_links_no_update","research_squalincome_links_no_delete"),
    "research_squalincome_price_evidence":("research_price_asof_no_update","research_price_asof_no_delete"),
    "research_cot_asof_attestations":("research_cot_asof_no_update","research_cot_asof_no_delete")
}
def causal_metadata(db):
    need(isinstance(db,sqlite3.Connection) and db.execute("PRAGMA query_only").fetchone()==(1,))
    # table_list distinguishes ordinary tables from virtual and shadow tables.
    catalog={r[1]:r[2] for r in db.execute("PRAGMA main.table_list") if r[0]=="main"}
    if not catalog:return "METADATA_UNAVAILABLE"
    if any(catalog.get(name)!="table" for name in CAUSAL_COLUMNS):
        return "REQUIRED_ORDINARY_TABLES_MISSING"
    for name,required in CAUSAL_COLUMNS.items():
        columns={r[1] for r in db.execute('PRAGMA main.table_xinfo("'+name+'")') if r[6]==0}
        if not set(required)<=columns:return "REQUIRED_COLUMNS_MISSING"
    for name,required in CAUSAL_TRIGGERS.items():
        names={r[0] for r in db.execute("SELECT name FROM main.sqlite_master WHERE type='trigger' AND tbl_name=? LIMIT 4097",(name,))}
        if len(names)>4096:raise ValueError("TRIGGER_METADATA_CAP")
        if not set(required)<=names:return "REQUIRED_TRIGGER_NAMES_MISSING"
    return "CAUSAL_QUERY_METADATA_PRESENT"

def schema(data,deadline,*,include_capability=False):
    with closing(sqlite3.connect(":memory:")) as db:
        db.deserialize(data)
        db.execute("PRAGMA trusted_schema=OFF")
        db.execute("PRAGMA query_only=ON")
        db.set_progress_handler(lambda:int(time.monotonic()>=deadline),1000)
        names={r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' LIMIT 4097")}
        need(len(names)<=4096 and time.monotonic()<deadline)
        present=frozenset(n for n in TABLES+SOURCE_TABLES if n in names)
        if not include_capability:return present
        capability=causal_metadata(db)
        need(time.monotonic()<deadline)
        return present,capability

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
    known=Counter({n:0 for n in TABLES+SOURCE_TABLES})
    co=Counter({"prices_and_status":0,"cot_and_first_seen":0,"prices_cot_and_first_seen":0})
    seen={}
    capability_counts=Counter()
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
                    seen[digest],capability=schema(data,deadline,include_capability=True)
                    capability_counts[capability]+=1
                    counts["distinct_verified_byte_groups"]+=1
                    for table in seen[digest]:known[table]+=1
                    present=seen[digest]
                    co["prices_and_status"]+=int({"prices","status"}<=present)
                    co["cot_and_first_seen"]+=int({"cot_reports","cot_first_seen"}<=present)
                    co["prices_cot_and_first_seen"]+=int({"prices","cot_reports","cot_first_seen"}<=present)
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
            "table_presence_in_distinct_byte_groups":{n:known[n] for n in TABLES},
            "source_table_presence_in_distinct_byte_groups":{n:known[n] for n in SOURCE_TABLES},
            "source_table_copresence_in_distinct_byte_groups":dict(co),
            "causal_query_metadata_in_distinct_byte_groups":dict(sorted(capability_counts.items())),
            "trigger_semantics_attested":False,"causal_pairs_verified":False,
            "source_rows_checked":False,"asof_availability_attested":False,
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
