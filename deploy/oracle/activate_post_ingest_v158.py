#!/usr/bin/env python3
"""Guarded v1.58 post-ingest opt-in: backup, restart, verify, auto-rollback."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from urllib.request import urlopen

ROOT = Path("/opt/remura")
PRIVATE = ROOT / "private"
ENV = PRIVATE / "remura.env"
STATE = PRIVATE / "autoupdate-state.json"
BACKUPS = PRIVATE / "predeploy-backups"
WORK = Path("/var/lib/remura-autoupdate")
LOCK = WORK / "lock"
SERVICE = "remura-private.service"
EXPECTED = "112da31cb10c34477642e2822c78b267cb88978d"
KEY = "REMURA_SQUALINCOME_AFTER_INGEST_ENABLED"
REQUIRED = {
    "REMURA_COLLECTOR_ENABLED": "1",
    "REMURA_COT_SYNC_ENABLED": "1",
    "REMURA_SQUALINCOME_MONITOR_ENABLED": "1",
}

def guard(ok, reason):
    if not ok:
        raise RuntimeError("STOP_" + reason)

def cmd(*args, timeout=35):
    return subprocess.run(list(args), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                          timeout=timeout, check=False)

def active():
    r = cmd("systemctl", "is-active", SERVICE)
    return r.returncode == 0 and r.stdout.strip() == b"active"

def healthy():
    try:
        with urlopen("http://127.0.0.1:8765/private-api/health", timeout=5) as r:
            return r.status == 200 and json.load(r).get("name") == "REMURA Private"
    except (OSError, ValueError, TimeoutError):
        return False

def live_flag():
    r = cmd("systemctl", "show", "-p", "MainPID", "--value", SERVICE)
    guard(r.returncode == 0, "PID_QUERY")
    pid = r.stdout.strip()
    guard(pid.isdigit() and int(pid) > 1, "PID_INVALID")
    process = (Path("/proc") / pid.decode("ascii") / "environ").read_bytes()
    items = [v for v in process.split(b"\0") if v.startswith(KEY.encode() + b"=")]
    guard(len(items) <= 1, "LIVE_FLAG_DUPLICATE")
    return items[0].partition(b"=")[2].decode("ascii") if items else "0"

def wait_health(flag, attempts=12):
    for index in range(attempts):
        try:
            if active() and healthy() and live_flag() == flag:
                return True
        except (OSError, ValueError, RuntimeError, UnicodeError):
            pass
        if index + 1 < attempts:
            time.sleep(2)
    return False

def restart():
    guard(cmd("systemctl", "restart", SERVICE, timeout=55).returncode == 0,
          "SERVICE_RESTART")

def entries(data):
    lines = data.decode("utf-8").splitlines(keepends=True)
    found = {}
    for index, line in enumerate(lines):
        row = line.strip()
        if not row or row.startswith("#") or "=" not in row:
            continue
        key, value = row.split("=", 1)
        key = key.strip()
        if key in REQUIRED or key == KEY:
            found.setdefault(key, []).append((index, value.strip().strip('"').strip("'")))
    return found, lines

def check():
    guard(os.geteuid() == 0, "ROOT_REQUIRED")
    guard(ENV.is_file() and not ENV.is_symlink(), "ENV_NOT_FILE")
    guard(STATE.is_file() and not STATE.is_symlink(), "STATE_NOT_FILE")
    guard(BACKUPS.is_dir() and not BACKUPS.is_symlink(), "BACKUPS_INVALID")
    guard(WORK.is_dir() and not WORK.is_symlink() and
          LOCK.is_file() and not LOCK.is_symlink(), "LOCK_INVALID")
    meta = ENV.stat()
    guard(stat.S_ISREG(meta.st_mode) and 0 < meta.st_size < 32768, "ENV_INVALID")
    guard(shutil.disk_usage(BACKUPS).free > 20 * 1024 * 1024, "DISK_SPACE")
    old = ENV.read_bytes()
    found, lines = entries(old)
    for key, target in REQUIRED.items():
        default = "0" if key == "REMURA_COLLECTOR_ENABLED" else "1"
        value = found.get(key, [(None, default)])
        guard(len(value) == 1 and value[0][1] == target, "PREREQUISITE_" + key)
    flag = found.get(KEY, [(None, "0")])
    guard(len(flag) == 1 and flag[0][1] == "0", "FLAG_NOT_OFF")
    state = json.loads(STATE.read_text("utf-8"))
    guard(isinstance(state, dict) and state.get("enabled") is True and
          state.get("installedSha") == EXPECTED and state.get("state") == "up_to_date"
          and state.get("failedSha") in (None, ""), "SHA_OR_STATE")
    guard(cmd("systemctl", "is-active", "remura-autoupdate.service").returncode != 0,
          "UPDATER_BUSY")
    guard(active() and healthy() and live_flag() == "0", "SERVICE_NOT_READY")
    if flag[0][0] is None:
        separator = b"" if old.endswith((b"\n", b"\r")) else b"\n"
        new = old + separator + KEY.encode() + b"=1\n"
    else:
        index = flag[0][0]
        ending = "\r\n" if lines[index].endswith("\r\n") else (
            "\n" if lines[index].endswith("\n") else "")
        lines[index] = KEY + "=1" + ending
        new = "".join(lines).encode("utf-8")
    guard(old != new and len(new) < 32768, "INVALID_CONFIG_CHANGE")
    return old, new, meta

def atomic_env(data, meta):
    fd, path = tempfile.mkstemp(prefix=".remura-post-ingest-", dir=PRIVATE)
    try:
        with os.fdopen(fd, "wb") as f:
            os.fchown(f.fileno(), meta.st_uid, meta.st_gid)
            os.fchmod(f.fileno(), stat.S_IMODE(meta.st_mode))
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(path, ENV)
        fd = os.open(PRIVATE, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(path):
            os.unlink(path)

def backup(data):
    os.umask(0o077)
    fd, path = tempfile.mkstemp(prefix="post-ingest-v158-before-",
                                suffix=".env", dir=BACKUPS)
    with os.fdopen(fd, "wb") as f:
        os.fchmod(f.fileno(), 0o600)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    guard(hashlib.sha256(Path(path).read_bytes()).digest() ==
          hashlib.sha256(data).digest(), "BACKUP_HASH")
    return path

def apply():
    guard(LOCK.is_file() and not LOCK.is_symlink(), "LOCK_INVALID")
    with LOCK.open("a+") as lock:
        try:
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("STOP_LOCK_BUSY")
        old, new, meta = check()
        path = backup(old)
        print("PREFLIGHT_POST_INGEST_V158=OK", flush=True)
        print("BACKUP_CONFIG=CREATO", flush=True)
        modified = False
        try:
            atomic_env(new, meta)
            modified = True
            guard(ENV.read_bytes() == new, "CONFIG_WRITE")
            restart()
            guard(wait_health("1"), "POST_RESTART_HEALTH_OR_FLAG")
            print("ATTIVAZIONE_POST_INGEST_V158=OK")
            print("FLAG_RUNTIME=ON")
            print("SERVIZIO_REMURA=ATTIVO")
            print("SHA_AUTUPDATE_INVARIATO=SI")
            print("BACKUP_CONFIG_PATH=" + path)
        except BaseException:
            if modified:
                try:
                    atomic_env(old, meta)
                    guard(ENV.read_bytes() == old, "ROLLBACK_CONFIG_HASH")
                    restart()
                    guard(wait_health("0"), "ROLLBACK_SERVICE")
                    print("ROLLBACK_CONFIG=OK", flush=True)
                except BaseException:
                    print("ROLLBACK_CONFIG=ATTENZIONE_CONTROLLO_MANUALE", flush=True)
                    print("BACKUP_CONFIG_PATH=" + path, flush=True)
            raise

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true", required=True)
    p.parse_args()
    try:
        apply()
        return 0
    except BaseException as exc:
        msg = str(exc)
        print("ATTIVAZIONE_POST_INGEST_V158=STOP")
        print("MOTIVO=" + (msg if re.fullmatch(r"STOP_[A-Z_0-9]+", msg)
                           else "ERRORE_NON_PUBBLICO"))
        return 1

if __name__ == "__main__":
    sys.exit(main())
