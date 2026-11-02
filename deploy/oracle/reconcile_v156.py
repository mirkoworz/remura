#!/usr/bin/env python3
"""Reconcile Git SHA after independently installed REMURA v1.56.

Read-only by default. --apply changes ONLY private/autoupdate-state.json after:
  - verifying pinned release script, 20 deployed files + banner timestamp
  - checking GitHub main SHA / CI, VPS health, backup + rollback manifests
  - checking existing state and taking the autoupdater's exclusive lock
No code installation, service restart, trading orders, broker calls or DB writes.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import urllib.request
import urllib.error
import sqlite3

APP=Path("/opt/remura")
PRIVATE=APP/"private"
STATE=PRIVATE/"autoupdate-state.json"
BACKUPS=PRIVATE/"predeploy-backups"
WORK=Path("/var/lib/remura-autoupdate")
ROOT="https://raw.githubusercontent.com/mirkoworz/remura"
API="https://api.github.com/repos/mirkoworz/remura"
OLD="d8ae01e19dd87e21b48c0d08c4b0c46a66b1eee4"
TARGET="b4ec4cdee133d3cdf97b94abf75f5f13c5872cf1"
RELEASE_COMMIT="3e0e34169ab89ccb2d6c09d777817ae3f705352b"
RELEASE_BLOB="8997906ee3d246b5c5d3f13a700b546c112dc525"
EXTRA=("scripts/private_server.py", "deploy/oracle/autoupdate.py", "deploy/oracle/remura.service")
WORKFLOWS=("insights-checks.yml","price-checks.yml")
STAMP=b"02/11/2026 07:43 (Italia, candidato al rilascio)"
STAMP_PATTERN=re.compile(rb"02/11/2026 (?:[01][0-9]|2[0-3]):[0-5][0-9] \(Italia\)")


def require(value,code):
    if not value:
        raise RuntimeError("STOP_"+code)


def sha_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\x00"+data).hexdigest()


def request(url,limit=50_000_000):
    req=urllib.request.Request(url,headers={"User-Agent":"REMURA-v156-state-reconcile",
                                            "Accept":"application/vnd.github+json"})
    with urllib.request.urlopen(req,timeout=35) as r:
        body=r.read(limit+1)
    require(len(body)<=limit,"REMOTE_TOO_LARGE")
    return body


def json_api(path):
    obj=json.loads(request(API+path,6_000_000))
    require(isinstance(obj,dict),"GITHUB_RESPONSE")
    return obj


def release_module():
    path=("/"+RELEASE_COMMIT+"/deploy/oracle/release_v156.py")
    raw=request(ROOT+path,3_000_000)
    require(sha_blob(raw)==RELEASE_BLOB,"RELEASE_SCRIPT_UNVERIFIED")
    ns={"__name__":"remura_release_v156_verified"}
    exec(compile(raw,"verified_release_v156.py","exec"),ns)
    ns["FILES"]=tuple(ns["FILES"])+EXTRA
    return ns


def candidate(ns):
    # Pinned to the already-reviewed GitHub main merge commit.
    return ns["candidate"](TARGET)


def live_code(staged,ns):
    app_files=ns["FILES"]
    require(APP.is_dir() and not APP.is_symlink(),"APP_INVALID")
    for name in app_files:
        local=APP/name
        require(local.is_file() and not local.is_symlink(),"FILE_MISSING")
        require(local.stat().st_size<=3_000_000,"FILE_TOO_LARGE")
        actual=local.read_bytes()
        expected=staged[name]
        if name=="nav.js":
            require(expected.count(STAMP)==1,"RELEASE_STAMP_SOURCE")
            # Only the date/time substitution performed by the audited release
            # installer is tolerated, never other changes to nav.js.
            require(STAMP_PATTERN.search(actual) is not None,"LIVE_STAMP_MISSING")
            live_stamp=STAMP_PATTERN.search(actual).group(0)
            require(expected.replace(STAMP,live_stamp)==actual,"LIVE_NAV_DIVERGED")
        else:
            require(actual==expected,"LIVE_CODE_DIVERGED")
    return len(app_files)


def live_healthy():
    cmd=subprocess.run(["systemctl","is-active","remura-private.service"],
                       capture_output=True,timeout=15)
    require(cmd.returncode==0 and cmd.stdout.strip()==b"active","SERVER_NOT_ACTIVE")
    with urllib.request.urlopen("http://127.0.0.1:8765/private-api/health",timeout=6) as r:
        doc=json.load(r)
        require(r.status==200 and doc.get("name")=="REMURA Private","SERVER_NOT_HEALTHY")


def check_archives(staged,ns):
    require(BACKUPS.is_dir() and not BACKUPS.is_symlink(),"BACKUPS_MISSING")
    backups=sorted(BACKUPS.glob("backup-v156-*"),reverse=True)
    rollbacks=sorted(BACKUPS.glob("rollback-v156-*"),reverse=True)
    require(bool(backups) and bool(rollbacks),"BACKUP_ROLLBACK_NOT_FOUND")
    valid_snapshot=False
    for item in backups[:8]:
        if not item.is_dir() or item.is_symlink(): continue
        doc=item/"remura-prices.sqlite3"
        manifest=item/"manifest.txt"
        if not doc.is_file() or doc.is_symlink() or not manifest.is_file() or manifest.is_symlink():continue
        m=re.search(r"(?m)^sha256=([0-9a-f]{64})$",manifest.read_text("ascii"))
        if not m:continue
        h=hashlib.sha256()
        with doc.open("rb") as inp:
            for block in iter(lambda:inp.read(1024*1024),b""):
                h.update(block)
        if h.hexdigest()!=m.group(1):continue
        with sqlite3.connect(doc.as_uri()+"?mode=ro",uri=True,timeout=12) as db:
            if db.execute("PRAGMA integrity_check").fetchone()[0]=="ok":
                valid_snapshot=True
                break
    require(valid_snapshot,"BACKUP_SNAPSHOT_UNVERIFIED")
    valid_rollback=False
    for item in rollbacks[:8]:
        if not item.is_dir() or item.is_symlink(): continue
        info=item/"manifest.json"
        if not info.is_file() or info.is_symlink():continue
        obj=json.loads(info.read_text("utf-8"))
        files=obj.get("files")
        if obj.get("schema")!="remura-v156-rollback-v1" or not isinstance(files,dict):
            continue
        expected_files=set(ns["FILES"])-set(EXTRA)
        if set(files)!=expected_files:continue
        if all(isinstance(x,dict) and
               x.get("new")==hashlib.sha256((APP/name).read_bytes()).hexdigest()
               for name,x in files.items()):
            valid_rollback=True
            break
    require(valid_rollback,"ROLLBACK_MANIFEST_DIVERGED")


def remote_main_ci():
    main=json_api("/commits/main").get("sha")
    require(isinstance(main,str) and re.fullmatch(r"[a-f0-9]{40}",main),"MAIN_SHA_INVALID")
    if main!=TARGET:
        cmp=json_api("/compare/"+TARGET+"..."+main)
        paths=[f.get("filename") for f in cmp.get("files",[])
               if isinstance(f,dict)]
        require(cmp.get("status")=="ahead" and 0<len(paths)<300 and
                all(isinstance(p,str) and
                    (p.startswith("data/") or p.endswith(".md")) for p in paths),
                "MAIN_MOVED_WITH_CODE")
    for workflow in WORKFLOWS:
        runs=json_api("/actions/workflows/"+workflow+"/runs?event=push&head_sha="+TARGET+"&per_page=20").get("workflow_runs",[])
        matched=[r for r in runs if isinstance(r,dict) and
                 r.get("head_sha")==TARGET and r.get("event")=="push" and
                 r.get("head_branch")=="main"]
        require(bool(matched) and all(r.get("status")=="completed" and
                                      r.get("conclusion")=="success" for r in matched),
                "MAIN_CI_NOT_GREEN")
    return main


def load_state():
    require(STATE.is_file() and not STATE.is_symlink(),"STATE_NOT_REGULAR")
    data=STATE.read_bytes()
    require(0<len(data)<32000,"STATE_SIZE")
    obj=json.loads(data)
    require(isinstance(obj,dict),"STATE_FORMAT")
    require(obj.get("enabled") is True,"AUTOUPDATE_NOT_ENABLED")
    require(obj.get("installedSha") in (OLD,TARGET),"UNEXPECTED_INSTALLED_SHA")
    require(obj.get("failedSha") in ("",None),"PENDING_FAILED_RELEASE")
    return obj,data,STATE.stat()


def inspection():
    require(os.geteuid()==0,"ROOT_REQUIRED")
    state,raw,meta=load_state()
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink(),"PRIVATE_DIRECTORY")
    require(WORK.is_dir() and not WORK.is_symlink(),"LOCK_DIRECTORY")
    mod=release_module()
    stage=candidate(mod)
    file_count=live_code(stage,mod)
    live_healthy()
    check_archives(stage,mod)
    remote=remote_main_ci()
    return state,raw,meta,file_count,remote


def atomic_state(state,raw,meta):
    updated=dict(state)
    updated["installedSha"]=TARGET
    updated["targetSha"]=TARGET
    updated["state"]="up_to_date"
    updated["manualSha"]=""
    updated["skippedSha"]=""
    updated["message"]="Riallineamento v1.56 verificato su codice e backup; nessun deploy"
    updated["lastCheck"]=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    contents=json.dumps(updated,sort_keys=True,separators=(",",":")).encode()
    require(BACKUPS.is_dir(),"BACKUP_FOLDER_MISSING")
    fd,snapshot=tempfile.mkstemp(prefix="state-before-v156-",suffix=".json",dir=BACKUPS)
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchmod(f.fileno(),0o600)
            f.write(raw)
            f.flush()
            os.fsync(f.fileno())
        temporary=None
        try:
            fd,temporary=tempfile.mkstemp(prefix=".reconciled-",dir=PRIVATE)
            with os.fdopen(fd,"wb") as f:
                os.fchown(f.fileno(),meta.st_uid,meta.st_gid)
                os.fchmod(f.fileno(),stat.S_IMODE(meta.st_mode))
                f.write(contents)
                f.flush()
                os.fsync(f.fileno())
            os.replace(temporary,STATE)
            directory=os.open(PRIVATE,os.O_RDONLY|os.O_DIRECTORY)
            try:os.fsync(directory)
            finally:os.close(directory)
        finally:
            if temporary and os.path.exists(temporary):os.unlink(temporary)
    except BaseException:
        # Preserve original file if replacement did not happen.
        raise


def perform(apply):
    if not apply:
        state,_,_,count,_=inspection()
        print("RICONCILIAZIONE=VERIFICATA")
        print("FILE_CONTROLLATI="+str(count))
        print("BACKUP_E_ROLLBACK=VERIFICATI")
        print("SHA_LIVE_STATO="+("VECCHIO" if state["installedSha"]==OLD else "GIA_RIALLINEATO"))
        print("STATO_INVARIATO=SI")
        return
    require(WORK.is_dir() and not WORK.is_symlink(),"LOCK_DIRECTORY")
    lock=WORK/"lock"
    require(lock.is_file() and not lock.is_symlink(),"LOCK_FILE_INVALID")
    with lock.open("a+") as f:
        fcntl.flock(f.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
        state,raw,meta,count,_=inspection()
        if state["installedSha"]==TARGET:
            print("RICONCILIAZIONE=GIA_ESEGUITA")
            return
        atomic_state(state,raw,meta)
    print("RICONCILIAZIONE=OK")
    print("FILE_CONTROLLATI="+str(count))
    print("STATO_AUTOUPDATE=ALLINEATO")
    print("CODICE_E_DATABASE_LIVE_INVARIATI=SI")
    print("BACKUP_STATO_PRECEDENTE=CREATO")


def main():
    p=argparse.ArgumentParser()
    mode=p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check",action="store_true")
    mode.add_argument("--apply",action="store_true")
    args=p.parse_args()
    try:
        perform(args.apply)
        return 0
    except BaseException as e:
        print("RICONCILIAZIONE=STOP")
        code=str(e)
        print("MOTIVO="+(code if code.startswith("STOP_") else "VERIFICA_NON_SUPERATA"))
        return 1


if __name__=="__main__":
    sys.exit(main())
