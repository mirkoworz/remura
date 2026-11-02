#!/usr/bin/env python3
"""REMURA v1.57: reconcile installed Git SHA WITHOUT deploying code.

--check is read-only. --apply backs up and replaces ONLY
/opt/remura/private/autoupdate-state.json under the exclusive updater lock.
The already installed 12 code files must match the requested GitHub main
commit, except the verified live install-time nav.js timestamp substitution.
No restart, broker calls, changes to remura.env, trading or DB writes.
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
import sqlite3
import stat
import subprocess
import sys
import tempfile
import urllib.request

APP=Path("/opt/remura")
PRIVATE=APP/"private"
STATE=PRIVATE/"autoupdate-state.json"
WORK=Path("/var/lib/remura-autoupdate")
BACKUPS=PRIVATE/"predeploy-backups"
API="https://api.github.com/repos/mirkoworz/remura"
RAW="https://raw.githubusercontent.com/mirkoworz/remura"
OLD="d6e2cd7575e0e58a36d1512f6ccffee24fe2438a"
RELEASE_SHA="9ad5fe9a4f139aa2c6cbf7b9e10e8b68e054180f"
RELEASE_BLOB="66b1b47dffdba04218af79250c883b7adc5fc6fc"
PREPARED_STAMP=b"02/11/2026 16:25 (Italia, preparazione)"
LIVE_STAMP=re.compile(rb"02/11/2026 (?:[01][0-9]|2[0-3]):[0-5][0-9] \(Italia\)")
SHA=re.compile(r"^[0-9a-f]{40}$")
ALLOWED_CODE={
    "asset.html","catalogo.html","fonti.html","forex.html","impostazioni.html",
    "index.html","mercati.html","nav.js","scripts/private_server.py",
    "statistica-squali.html","stato-prezzi.html","sw.js",
    "deploy/oracle/release_v157.py","deploy/oracle/priority_v157.py",
    "deploy/oracle/reconcile_v157.py",
    ".github/workflows/price-checks.yml",
    "tests/price-status.test.js","tests/release-consistency.test.js",
    "tests/statistica-squali.test.js","tests/test_priority_v157.py",
    "tests/test_private_server.py","tests/test_release_v157.py",
    "tests/test_reconcile_v157.py",
}
ALLOWED_DOCS={"ROADMAP.md","CVD-DIVERGENZE-ROADMAP.md","V157-RELEASE-PLAN.md"}
WORKFLOWS=("price-checks.yml","insights-checks.yml")


def require(ok,reason):
    if not ok:raise RuntimeError("STOP_"+reason)


def blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def request(url,limit):
    req=urllib.request.Request(url,headers={"Accept":"application/vnd.github+json",
            "User-Agent":"REMURA-v157-state-reconcile"})
    with urllib.request.urlopen(req,timeout=40) as response:
        data=response.read(limit+1)
    require(len(data)<=limit,"REMOTE_OVERSIZE")
    return data


def json_api(path):
    value=json.loads(request(API+path,6_000_000))
    require(isinstance(value,dict),"REMOTE_INVALID")
    return value


def release_module():
    raw=request(RAW+"/"+RELEASE_SHA+"/deploy/oracle/release_v157.py",3_000_000)
    require(blob(raw)==RELEASE_BLOB,"RELEASE_PIN_MISMATCH")
    ns={"__name__":"verified_v157_release_module"}
    exec(compile(raw,"verified_release_v157.py","exec"),ns)
    return ns


def correct_live_code(candidate,release):
    require(APP.is_dir() and not APP.is_symlink(),"APP_INVALID")
    expected=release["FILES"]
    require(len(expected)==12,"FILE_COUNT")
    for file in expected:
        path=APP/file
        require(path.is_file() and not path.is_symlink() and
                path.stat().st_size<=3_000_000,"LIVE_FILE_INVALID")
        existing=path.read_bytes()
        want=candidate[file]
        if file=="nav.js":
            require(want.count(PREPARED_STAMP)==1,"SOURCE_STAMP_UNEXPECTED")
            found=LIVE_STAMP.findall(existing)
            require(len(found)==1,"LIVE_STAMP_INVALID")
            require(existing==want.replace(PREPARED_STAMP,found[0]),
                    "LIVE_NAV_DIVERGED")
        else:
            require(existing==want,"LIVE_FILE_DIVERGED")
    return expected


def healthy():
    proc=subprocess.run(["systemctl","is-active","remura-private.service"],
            capture_output=True,timeout=15)
    require(proc.returncode==0 and proc.stdout.strip()==b"active","SERVER_INACTIVE")
    with urllib.request.urlopen("http://127.0.0.1:8765/private-api/health",
                                 timeout=6) as response:
        require(response.status==200 and json.load(response).get("name")=="REMURA Private",
                "HEALTH_INVALID")


def backups_present(expected):
    require(BACKUPS.is_dir() and not BACKUPS.is_symlink(),"BACKUPS_INVALID")
    rollback=False
    for folder in sorted(BACKUPS.glob("rollback-v157-*"),reverse=True)[:12]:
        try:
            if not folder.is_dir() or folder.is_symlink():continue
            manifest_path=folder/"manifest.json"
            if not manifest_path.is_file() or manifest_path.is_symlink():continue
            manifest=json.loads(manifest_path.read_text("utf-8"))
            if (manifest.get("schema")!="remura-v157-rollback-v1" or
                manifest.get("commit")!=RELEASE_SHA or
                not isinstance(manifest.get("files"),dict) or
                set(manifest["files"])!=set(expected)):continue
            if all(isinstance(manifest["files"][name],dict) and
                   manifest["files"][name].get("new")==
                     hashlib.sha256((APP/name).read_bytes()).hexdigest()
                   for name in expected):
                rollback=True
                break
        except (OSError,ValueError,TypeError,KeyError):
            continue
    require(rollback,"ROLLBACK_MANIFEST_UNVERIFIED")
    snapshot=False
    for folder in sorted(BACKUPS.glob("backup-v156-*"),reverse=True)[:14]:
        try:
            if not folder.is_dir() or folder.is_symlink():continue
            p=folder/"remura-prices.sqlite3"
            manifest=folder/"manifest.txt"
            if not p.is_file() or p.is_symlink() or not manifest.is_file():continue
            h=re.search(r"(?m)^sha256=([0-9a-f]{64})$",manifest.read_text("ascii"))
            if not h:continue
            digest=hashlib.sha256()
            with p.open("rb") as stream:
                for part in iter(lambda:stream.read(1024*1024),b""):
                    digest.update(part)
            if digest.hexdigest()!=h.group(1):continue
            with sqlite3.connect(p.as_uri()+"?mode=ro",uri=True,timeout=12) as db:
                if db.execute("PRAGMA integrity_check").fetchone()[0]=="ok":
                    snapshot=True;break
        except (OSError,ValueError,sqlite3.Error):
            continue
    require(snapshot,"SQLITE_BACKUP_UNVERIFIED")


def validate_target(target):
    require(isinstance(target,str) and SHA.fullmatch(target),"TARGET_INVALID")
    current=json_api("/commits/main").get("sha")
    require(current==target,"MAIN_MOVED")
    diff=json_api("/compare/"+OLD+"..."+target)
    require(diff.get("status")=="ahead","MAIN_NOT_AHEAD")
    items=diff.get("files")
    require(isinstance(items,list) and 0<len(items)<300,"DIFF_TOO_LARGE")
    paths=[item.get("filename") for item in items if isinstance(item,dict)]
    require(len(paths)==len(items) and all(isinstance(x,str) for x in paths),
            "DIFF_INVALID")
    require("scripts/private_server.py" in paths and
            "deploy/oracle/reconcile_v157.py" in paths,"VERSION_DIFF_MISSING")
    require(all(p in ALLOWED_CODE or p in ALLOWED_DOCS or p.startswith("data/myfxbook/")
                for p in paths),"UNREVIEWED_FILES")
    for workflow in WORKFLOWS:
        response=json_api("/actions/workflows/"+workflow+"/runs?event=push&head_sha="+target+"&per_page=20")
        runs=response.get("workflow_runs")
        require(isinstance(runs,list),"CI_MISSING")
        passed=[x for x in runs if isinstance(x,dict) and
                x.get("head_sha")==target and x.get("head_branch")=="main" and
                x.get("event")=="push"]
        require(bool(passed) and all(x.get("status")=="completed" and
                    x.get("conclusion")=="success" for x in passed),"CI_NOT_GREEN")


def state_read():
    require(STATE.is_file() and not STATE.is_symlink(),"STATE_MISSING")
    raw=STATE.read_bytes()
    require(0<len(raw)<32768,"STATE_SIZE")
    obj=json.loads(raw)
    require(isinstance(obj,dict) and obj.get("enabled") is True and
            obj.get("installedSha")==OLD and
            obj.get("state") in ("up_to_date","manual_required"),"STATE_UNEXPECTED")
    require(obj.get("failedSha") in ("",None),"FAILED_RELEASE_PENDING")
    return obj,raw,STATE.stat()


def inspect(target):
    require(os.geteuid()==0,"ROOT")
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink() and
            WORK.is_dir() and not WORK.is_symlink(),"PRIVATE_INVALID")
    obj,raw,meta=state_read()
    require(subprocess.run(["systemctl","is-active","remura-autoupdate.service"],
            capture_output=True,timeout=12).returncode!=0,"UPDATER_BUSY")
    healthy()
    validate_target(target)
    mod=release_module()
    candidate=mod["candidate"](target)
    files=correct_live_code(candidate,mod)
    backups_present(files)
    # Avoid TOCTOU: don't reconcile to a main commit that changed during scan.
    require(json_api("/commits/main").get("sha")==target,"MAIN_MOVED")
    return obj,raw,meta,files


def commit_state(target,obj,raw,meta):
    updated=dict(obj)
    updated.update(installedSha=target,targetSha=target,
        state="up_to_date",manualSha="",skippedSha="",failedSha="",
        lastCheck=dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        message="Riconciliazione REMURA v1.57 verificata, nessun nuovo deploy")
    content=json.dumps(updated,sort_keys=True,separators=(",",":")).encode()
    os.umask(0o077)
    fd,snapshot=tempfile.mkstemp(prefix="state-before-v157-",suffix=".json",dir=BACKUPS)
    with os.fdopen(fd,"wb") as f:
        os.fchmod(f.fileno(),0o600)
        f.write(raw);f.flush();os.fsync(f.fileno())
    fd,temp=tempfile.mkstemp(prefix=".reconcile-v157-",dir=PRIVATE)
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchown(f.fileno(),meta.st_uid,meta.st_gid)
            os.fchmod(f.fileno(),stat.S_IMODE(meta.st_mode))
            f.write(content);f.flush();os.fsync(f.fileno())
        os.replace(temp,STATE)
        fd=os.open(PRIVATE,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(fd)
        finally:os.close(fd)
    finally:
        if os.path.exists(temp):os.unlink(temp)


def main():
    parser=argparse.ArgumentParser()
    a=parser.add_mutually_exclusive_group(required=True)
    a.add_argument("--check",action="store_true")
    a.add_argument("--apply",action="store_true")
    parser.add_argument("--target",required=True)
    options=parser.parse_args()
    try:
        if options.check:
            _,_,_,files=inspect(options.target)
            print("RICONCILIAZIONE_V157=VERIFICATA")
            print("FILE_INSTALLATI="+str(len(files)))
            print("BACKUP_ROLLBACK=VERIFICATI")
            print("CI_MAIN=VERDE")
            print("STATO_INVARIATO=SI")
            return 0
        lock=WORK/"lock"
        require(lock.is_file() and not lock.is_symlink(),"LOCK_INVALID")
        with lock.open("a+") as fd:
            fcntl.flock(fd.fileno(),fcntl.LOCK_EX|fcntl.LOCK_NB)
            obj,raw,meta,files=inspect(options.target)
            commit_state(options.target,obj,raw,meta)
        print("RICONCILIAZIONE_V157=OK")
        print("FILE_INSTALLATI="+str(len(files)))
        print("BACKUP_STATO=CREATO")
        print("CODICE_DATABASE_CONFIG_LIVE_INVARIATI=SI")
        return 0
    except BaseException as exc:
        print("RICONCILIAZIONE_V157=STOP")
        message=str(exc)
        print("MOTIVO="+(message if message.startswith("STOP_") else "VERIFICA_NON_SUPERATA"))
        return 1


if __name__=="__main__":
    sys.exit(main())
