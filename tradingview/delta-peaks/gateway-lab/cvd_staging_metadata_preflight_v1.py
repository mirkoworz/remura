#!/usr/bin/env python3
# REMURA v0.8.86 LAB — 14/11/2026 20:43 CET
"""One-shot metadata-only local staging probe; no real SQLite opens, file
contents, secrets, network, service changes or writes. Does NOT admit runtime.
Trusted caller and paths required. No automatic CLI or scheduler.
"""
from pathlib import Path
import os,stat,sqlite3,sys,time
from zoneinfo import ZoneInfo
from cvd_linux_host_evidence_v1 import sample_host
from cvd_detached_snapshots_v1 import MAX_TOTAL_BYTES,NAMES
from cvd_runtime_private_state_v1 import MAX_BYTES
from cvd_runtime_resource_gate_v1 import MIN_MEMORY_BYTES,MAX_LOAD_PER_CPU,fresh,MAX_HOST_AGE_MS
from cvd_runtime_singleflight_v1 import NAME as LOCK

MIN_DISK_RESERVE=256*1024*1024
B_PIN="8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b"

def _directory(path):
    fd=os.open(path,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
    try:
        s=os.fstat(fd)
        if s.st_uid!=os.geteuid() or s.st_mode&0o077:
            raise ValueError("preflight_directory_permissions")
        return fd
    except BaseException:
        os.close(fd);raise

def _file(fd,name):
    s=os.stat(name,dir_fd=fd,follow_symlinks=False)
    if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077 or s.st_nlink!=1:
        raise ValueError("preflight_file_scope")
    return s

def _volume(fd):
    v=os.fstatvfs(fd)
    total=v.f_blocks*v.f_frsize;free=v.f_bavail*v.f_frsize
    if not 0<=free<=total or total<=0:
        raise ValueError("preflight_disk")
    return total,free

def _versions():
    try:
        ZoneInfo("Europe/Rome")
        tz=True
    except Exception:tz=False
    # Test deserialize on synthetic in-memory bytes only, not an actual file.
    support=False
    try:
        src=sqlite3.connect(":memory:");dst=None
        try:
            src.execute("CREATE TABLE probe (v INTEGER)")
            src.execute("INSERT INTO probe VALUES (1)")
            src.commit()
            dst=sqlite3.connect(":memory:")
            dst.deserialize(src.serialize())
            support=dst.execute("SELECT v FROM probe").fetchone()==(1,)
        finally:
            if dst is not None:dst.close()
            src.close()
    except (AttributeError,sqlite3.Error,NotImplementedError):pass
    return {"python_supported":sys.version_info>=(3,11),
            "sqlite_deserialize_works":support,"rome_timezone_available":tz}

def inspect(root,state_root,*,include_private=False,explicit=False):
    if explicit is not True or type(include_private) is not bool:
        raise ValueError("explicit_metadata_preflight_required")
    reasons=[]
    result={"schema":"remura.tv.staging.metadata.preflight.v1","version":"0.8.86-lab",
            "status":"BLOCKED","checks":{},"snapshot_bytes":None,"state_free_bytes":None,
            "host_available_bytes":None,"host_visible_cpus":None,"host_load1":None,
            "source_content_read":False,"real_sqlite_opened":False,"network_calls":0,
            "source_provenance_verified":False,"code_pin_verified":False,
            "cost_verified_zero":False,"live_authorized":False,"runtime_admitted":False}
    checks=result["checks"]
    checks.update(_versions())
    for k,v in checks.items():
        if not v:reasons.append(k.upper()+"_FAILED")
    try:
        host=sample_host();now=time.time_ns()//1000000
        result.update(host_available_bytes=host["available_bytes"],host_visible_cpus=host["visible_cpus"],host_load1=host["load1"])
        checks["host_headroom"]=bool(fresh(host["observed_ms"],now,MAX_HOST_AGE_MS) and
            host["available_bytes"]>=MIN_MEMORY_BYTES and host["load1"]/host["visible_cpus"]<=MAX_LOAD_PER_CPU)
    except (ValueError,OSError,KeyError,TypeError,ZeroDivisionError):
        checks["host_headroom"]=False
    if not checks["host_headroom"]:reasons.append("HOST_HEADROOM_UNVERIFIED")
    try:
        fd=_directory(root)
        try:
            size=0
            for name in NAMES[:2 if include_private else 1]:
                info=_file(fd,name)
                if info.st_size<100:raise ValueError("snapshot_metadata_size")
                for ext in ("-wal","-shm","-journal"):
                    try:os.stat(name+ext,dir_fd=fd,follow_symlinks=False)
                    except FileNotFoundError:pass
                    else:raise ValueError("snapshot_sidecar_present")
                size+=info.st_size
            result["snapshot_bytes"]=size
            checks["snapshot_size_scope"]=size<=MAX_TOTAL_BYTES
        finally:os.close(fd)
    except (OSError,ValueError):checks["snapshot_size_scope"]=False
    if not checks["snapshot_size_scope"]:reasons.append("SNAPSHOT_METADATA_UNVERIFIED_OR_OVERSIZE")
    try:
        fd=_directory(state_root)
        try:
            lock=_file(fd,LOCK)
            total,free=_volume(fd);result["state_free_bytes"]=free
            checks["state_lock_metadata"]=lock.st_size==0
            checks["state_disk_headroom"]=free>=max(MIN_DISK_RESERVE,(total+9)//10)+2*MAX_BYTES
        finally:os.close(fd)
    except (OSError,ValueError):
        checks["state_lock_metadata"]=False;checks["state_disk_headroom"]=False
    for k in ("state_lock_metadata","state_disk_headroom"):
        if not checks[k]:reasons.append(k.upper()+"_FAILED")
    result["status"]="METADATA_PLAUSIBLE_ONLY" if not reasons else "BLOCKED"
    result["reasons"]=sorted(reasons)
    return result

def admission(*,metadata,review,explicit=False):
    """Review checklist only; caller attestations are not authentication.
    No automatic real execution even when everything is supplied.
    """
    if explicit is not True:raise ValueError("explicit_review_required")
    reasons=[]
    if (type(metadata) is not dict or metadata.get("schema")!="remura.tv.staging.metadata.preflight.v1" or
        metadata.get("status")!="METADATA_PLAUSIBLE_ONLY" or metadata.get("runtime_admitted") is not False):
        reasons.append("METADATA_NOT_PLAUSIBLE")
    required={"b_checkout_sha","d_checkout_sha","authorized_detached_exports","core_schema_and_restore_reviewed",
              "token_scopes_reviewed","oracle_continuity_reviewed","first_fx_receipt_verified",
              "private_execution_authorized","no_live_changes","fresh_quota_plan_reviewed"}
    if type(review) is not dict or set(review)!=required:
        reasons.append("REVIEW_INCOMPLETE")
    else:
        if review["b_checkout_sha"]!=B_PIN:reasons.append("B_PIN_MISMATCH")
        d=review["d_checkout_sha"]
        if type(d) is not str or len(d)!=40 or any(c not in "0123456789abcdef" for c in d):
            reasons.append("D_PIN_UNVERIFIED")
        for k in required-{"b_checkout_sha","d_checkout_sha"}:
            if review[k] is not True:reasons.append(k.upper()+"_UNVERIFIED")
    return {"schema":"remura.tv.staging.review.v1","version":"0.8.86-lab",
            "status":"REVIEW_CHECKLIST_COMPLETE_ONLY" if not reasons else "BLOCKED",
            "reasons":sorted(reasons),"caller_attestations_only":True,
            "checked_out_code_authenticated":False,"runtime_admitted":False,
            "orders_enabled":False,"notifications_enabled":False,"live_authorized":False}
