#!/usr/bin/env python3
"""Enable/disable REMURA priority schedule with private, reversible env editing.

This script NEVER changes broker accounts, trading orders, SQLite or Git SHA.
--check is read-only. --enable / --disable require an exclusive autoupdate lock.
The scheduler is inactive until the service is restarted successfully.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import tempfile
import time
import urllib.request

APP=Path("/opt/remura")
PRIVATE=APP/"private"
ENV=PRIVATE/"remura.env"
BACKUPS=PRIVATE/"predeploy-backups"
WORK=Path("/var/lib/remura-autoupdate")
SERVER=APP/"scripts/private_server.py"
STATE=PRIVATE/"autoupdate-state.json"
SERVICE="remura-private.service"
SHA_V156="d6e2cd7575e0e58a36d1512f6ccffee24fe2438a"
# v1.57 manually installed candidate, NOT the v1.56 autoupdate-state SHA.
V157_SERVER_BLOB="4dfdf667a46893e1fc7acbbb19dc25b7f9f9f621"
FLAG=b"REMURA_PRIORITY_COLLECTOR_ENABLED"
LINE=re.compile(rb"^\s*"+FLAG+rb"\s*=\s*(.*?)\s*$")
LIMIT=1_048_576


def guard(value, code):
    if not value:
        raise RuntimeError("STOP_"+code)


def git_blob(data):
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\x00"+data).hexdigest()


def is_regular(p):
    return p.is_file() and not p.is_symlink() and stat.S_ISREG(p.lstat().st_mode)


def service_active():
    out=subprocess.run(["systemctl","is-active",SERVICE],capture_output=True,timeout=18)
    return out.returncode==0 and out.stdout.strip()==b"active"


def health():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/private-api/health",timeout=5) as response:
            data=json.load(response)
            return response.status==200 and data.get("name")=="REMURA Private"
    except (OSError,ValueError,TimeoutError):
        return False


def environment_mode(data):
    guard(b"\x00" not in data and b"\r" not in data, "ENV_FORMAT")
    found=[]
    for item in data.split(b"\n"):
        clean=item.strip()
        if not clean or clean.startswith(b"#"):
            continue
        match=LINE.fullmatch(item)
        if match:
            value=match.group(1).strip()
            guard(value in (b"0",b"1",b'"0"',b'"1"',b"'0'",b"'1'"),
                  "PRIORITY_VALUE")
            found.append(value.strip(b"'\"").decode("ascii"))
        elif (FLAG in item.split(b"=",1)[0] or
              item.lstrip().startswith(b"export "+FLAG)):
            raise RuntimeError("STOP_PRIORiTY_SYNTAX")
    guard(len(found)<=1,"PRIORITY_DUPLICATE")
    return found[0] if found else "0"


def edited(data, mode):
    guard(mode in ("0","1"),"MODE")
    previous=environment_mode(data)
    if previous==mode:
        return data
    result=[]
    replaced=False
    for item in data.split(b"\n"):
        if LINE.fullmatch(item):
            result.append(FLAG+b"="+mode.encode("ascii"))
            replaced=True
        else:
            result.append(item)
    if not replaced:
        if result and result[-1]!=b"":
            result.append(b"")
        result.append(FLAG+b"="+mode.encode("ascii"))
        result.append(b"")
    updated=b"\n".join(result)
    guard(0<len(updated)<=LIMIT,"ENV_SIZE")
    return updated


def preflight():
    guard(os.geteuid()==0,"ROOT_REQUIRED")
    guard(PRIVATE.is_dir() and not PRIVATE.is_symlink(),"PRIVATE_DIRECTORY")
    guard(BACKUPS.is_dir() and not BACKUPS.is_symlink(),"BACKUP_DIRECTORY")
    guard(WORK.is_dir() and not WORK.is_symlink(),"LOCK_DIRECTORY")
    guard(is_regular(ENV) and is_regular(SERVER) and is_regular(STATE),"FILES_INVALID")
    guard(0<ENV.stat().st_size<=LIMIT,"ENV_SIZE")
    guard(stat.S_IMODE(ENV.stat().st_mode)&0o077==0,"ENV_PERMISSIONS")
    guard(SERVER.stat().st_size<100_000,"SERVER_SIZE")
    guard(git_blob(SERVER.read_bytes())==V157_SERVER_BLOB,"SERVER_NOT_V157")
    state=json.loads(STATE.read_text("utf-8"))
    guard(isinstance(state,dict) and state.get("installedSha")==SHA_V156 and
          state.get("state")=="up_to_date", "AUTOUPDATE_STATE_UNEXPECTED")
    guard(not (subprocess.run(["systemctl","is-active","remura-autoupdate.service"],
                              capture_output=True,timeout=16).returncode==0),"AUTOUPDATE_BUSY")
    guard(service_active() and health(),"SERVER_UNHEALTHY")
    original=ENV.read_bytes()
    mode=environment_mode(original)
    guard(shutil.disk_usage(PRIVATE).free>max(20_000_000, len(original)*10),
          "DISK_SPACE")
    return original, ENV.stat(), mode


def running_mode():
    # Read ONLY the target process's startup environment. Never log it.
    out=subprocess.run(["systemctl","show",SERVICE,"-p","MainPID","--value"],
                       capture_output=True,timeout=12)
    guard(out.returncode==0 and out.stdout.strip().isdigit(),"PID_LOOKUP")
    pid=int(out.stdout.strip())
    guard(pid>1,"PID_NOT_ACTIVE")
    env_file=Path("/proc")/str(pid)/"environ"
    blob=env_file.read_bytes()
    guard(len(blob)<2_000_000,"PROCESS_ENV_TOO_LARGE")
    active=[s.split(b"=",1)[1] for s in blob.split(b"\x00") if s.startswith(FLAG+b"=")]
    guard(len(active)<=1,"PROCESS_ENV_DUPLICATE")
    return active[0].decode("ascii") if active else "0"


def replace_env(data, meta):
    fd,name=tempfile.mkstemp(prefix=".remura-priority-",dir=PRIVATE)
    try:
        with os.fdopen(fd,"wb") as f:
            os.fchown(f.fileno(),meta.st_uid,meta.st_gid)
            os.fchmod(f.fileno(),stat.S_IMODE(meta.st_mode))
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name,ENV)
        directory=os.open(PRIVATE,os.O_RDONLY|os.O_DIRECTORY)
        try:os.fsync(directory)
        finally:os.close(directory)
    finally:
        if os.path.exists(name):os.unlink(name)


def restart_and_verify(mode):
    r=subprocess.run(["systemctl","restart",SERVICE],capture_output=True,timeout=45)
    guard(r.returncode==0,"SERVICE_RESTART")
    for _ in range(12):
        if service_active() and health():
            guard(running_mode()==mode,"PROCESS_ENV_MISMATCH")
            return
        time.sleep(1)
    raise RuntimeError("STOP_SERVER_UNHEALTHY_AFTER_RESTART")


def backup_env(data):
    os.umask(0o077)
    fd,name=tempfile.mkstemp(prefix="priority-v157-env-",suffix=".bak",dir=BACKUPS)
    with os.fdopen(fd,"wb") as f:
        os.fchmod(f.fileno(),0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    guard(hashlib.sha256(Path(name).read_bytes()).digest()==hashlib.sha256(data).digest(),
          "ENV_BACKUP_MISMATCH")
    return Path(name)


def change(mode):
    guard(WORK.is_dir() and not WORK.is_symlink(),"LOCK_DIRECTORY")
    lockfile=WORK/"lock"
    guard(is_regular(lockfile),"LOCK_FILE")
    with lockfile.open("a+") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original,meta,previous=preflight()
        live=running_mode()
        guard(live==previous,"ENV_PROCESS_NOT_ALIGNED")
        if previous==mode:
            print("PRIORITA=GIA_"+("ATTIVA" if mode=="1" else "DISATTIVA"))
            return
        new=edited(original,mode)
        snapshot=backup_env(original)
        print("BACKUP_CONFIGURAZIONE=CREATO",flush=True)
        try:
            replace_env(new,meta)
            restart_and_verify(mode)
        except BaseException:
            try:
                replace_env(original,meta)
                restart_and_verify(previous)
                print("ROLLBACK_CONFIGURAZIONE=OK",flush=True)
            except BaseException:
                print("ROLLBACK_CONFIGURAZIONE=VERIFICA_MANUALE_NECESSARIA",flush=True)
            raise
        print("PRIORITA="+("ATTIVA" if mode=="1" else "DISATTIVA"),flush=True)
        print("SERVIZIO=ATTIVO",flush=True)
        print("ENV_PROCESSO=VERIFICATO",flush=True)
        print("BACKUP_PRIVATO=CONSERVATO",flush=True)
        print("DATABASE_INVARIATO=SI",flush=True)
        print("SHA_AUTOUPDATE_INVARIATO=SI",flush=True)


def main():
    p=argparse.ArgumentParser()
    a=p.add_mutually_exclusive_group(required=True)
    a.add_argument("--check",action="store_true")
    a.add_argument("--enable",action="store_true")
    a.add_argument("--disable",action="store_true")
    args=p.parse_args()
    try:
        if args.check:
            _,_,mode=preflight()
            print("PRIORITY_PREFLIGHT=OK")
            print("PRIORITA_CONFIGURATA="+("ATTIVA" if mode=="1" else "DISATTIVA"))
            print("SERVIZIO=ATTIVO")
            print("NESSUNA_MODIFICA=SI")
        else:
            change("1" if args.enable else "0")
        return 0
    except BaseException as exc:
        message=str(exc)
        print("PRIORITA_OPERAZIONE=STOP")
        print("MOTIVO="+(message if message.startswith("STOP_") else "VERIFICA_NON_SUPERATA"))
        return 1


if __name__=="__main__":
    raise SystemExit(main())
