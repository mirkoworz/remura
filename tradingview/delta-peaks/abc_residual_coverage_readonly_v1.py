#!/usr/bin/env python3
# REMURA v0.8.141 LAB — 18/11/2026, sessione 09:19 CET
"""Targeted residual coverage, not a new backup or a release gate.
Only closed recovered SQLite, or metadata of explicitly selected Oracle paths.
Never prints a private path, environment value, SQL row, credential or exception.
"""
import argparse
import hashlib
import json
import os
import re
import sqlite3
import stat
import subprocess
from pathlib import Path

SCHEMA = "remura.recovery.residual.readonly.v1"
TABLES = {
    "cot_reports": {"dataset", "code", "report_date", "oi", "first_long",
                    "first_short", "second_long", "second_short"},
    "cot_first_seen": {"dataset", "code", "report_date", "first_seen_at"},
}
FIXED = {
    "capital_budget": "capital/budget.json",
    "capital_lock": "capital/budget.lock",
    "capital_markets": "capital/markets.json",
    "ctrader_primary_token": "ctrader-tokens.json",
    "ctrader_backup_token": "ctrader-backup-tokens.json",
}

def metadata(path):
    try:
        s = path.lstat()
    except FileNotFoundError:
        return "absent"
    except OSError:
        return "unavailable"
    if not stat.S_ISREG(s.st_mode):
        return "unsafe_or_nonregular"
    return "regular_restricted" if not s.st_mode & 0o077 else "regular_review_permissions"

def cot_connection(db):
    db.execute("PRAGMA trusted_schema=OFF")
    db.execute("PRAGMA query_only=ON")
    result = {}
    for table, required in TABLES.items():
        row = db.execute("SELECT type,sql FROM sqlite_master WHERE name=?", (table,)).fetchone()
        if row is None:
            result[table] = {"state":"absent"}
            continue
        if row[0] != "table" or not re.match(r"^CREATE\s+TABLE\s", row[1] or "", re.I):
            result[table] = {"state":"unexpected_object"}
            continue
        columns = {r[1] for r in db.execute("PRAGMA table_info("+table+")")}
        if not required <= columns:
            result[table] = {"state":"schema_mismatch"}
            continue
        rows, codes, weeks = db.execute(
            "SELECT count(*),count(DISTINCT code),count(DISTINCT report_date) FROM "+table
        ).fetchone()
        result[table] = {"state":"present","rows":rows,"codes":codes,"weeks":weeks}
    if all(result[t]["state"] == "present" for t in TABLES):
        result["reports_without_first_seen"] = db.execute(
            "SELECT count(*) FROM cot_reports r WHERE NOT EXISTS "
            "(SELECT 1 FROM cot_first_seen f WHERE f.dataset=r.dataset "
            "AND f.code=r.code AND f.report_date=r.report_date)"
        ).fetchone()[0]
        result["first_seen_without_reports"] = db.execute(
            "SELECT count(*) FROM cot_first_seen f WHERE NOT EXISTS "
            "(SELECT 1 FROM cot_reports r WHERE r.dataset=f.dataset "
            "AND r.code=f.code AND r.report_date=f.report_date)"
        ).fetchone()[0]
    return result

def cot_closed(path):
    # Explicit custody copy only. Never point this at the live database.
    if not path.is_file() or path.is_symlink():
        raise ValueError("not_closed_regular")
    if any(os.path.lexists(str(path)+s) for s in ("-wal","-shm","-journal")):
        raise ValueError("sidecar_present")
    before = path.stat()
    uri = path.resolve().as_uri()+"?mode=ro&immutable=1"
    db = sqlite3.connect(uri,uri=True)
    try:
        result = cot_connection(db)
    finally:
        db.close()
    after = path.stat()
    key = lambda s:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns,s.st_ctime_ns)
    if key(before)!=key(after) or any(os.path.lexists(str(path)+s) for s in ("-wal","-shm","-journal")):
        raise ValueError("unstable")
    return result

def classify_environment_files(raw):
    # systemctl show format: /path (ignore_errors=yes|no).
    # Reject ambiguous escaping/multiline syntax rather than guess.
    if not raw.strip():
        return {"state":"none_reported","count":0}
    pattern = r"(/[^\s\\]+) \(ignore_errors=(yes|no)\)"
    matches = list(re.finditer(pattern, raw.strip()))
    if not matches or re.sub(pattern, "", raw.strip()).strip():
        return {"state":"unparsed","count":None}
    states = {}
    for m in matches:
        state = metadata(Path(m.group(1)))
        states[state] = states.get(state,0)+1
    return {"state":"metadata_only","count":len(matches),"classes":states}

def oracle_metadata():
    names = ("LoadState","ActiveState","MainPID","User","WorkingDirectory",
             "EnvironmentFiles","ProtectSystem","NoNewPrivileges","DropInPaths")
    call = ["systemctl","show","remura-private.service","--no-pager"]
    for n in names:
        call.extend(("-p",n))
    raw = subprocess.check_output(call,stderr=subprocess.DEVNULL,text=True,timeout=10)
    props = dict(line.split("=",1) for line in raw.splitlines() if "=" in line)
    result = {"service_loaded":props.get("LoadState")=="loaded",
              "service_active":props.get("ActiveState")=="active",
              "expected_user":props.get("User")=="remura",
              "expected_workdir":props.get("WorkingDirectory")=="/opt/remura",
              "protect_system_strict":props.get("ProtectSystem")=="strict",
              "no_new_privileges":props.get("NoNewPrivileges")=="yes",
              "dropins_reported":bool(props.get("DropInPaths")),
              "environment_files":classify_environment_files(props.get("EnvironmentFiles","")) if "EnvironmentFiles" in props else {"state":"unavailable"},
              "inline_environment_not_inspected":True,
              "effective_environment_not_inspected":True}
    pid = int(props.get("MainPID","0"))
    result["database_path_state"] = "unresolved"
    if pid <= 0 or not result["expected_workdir"]:
        return result
    try:
        with open("/proc/"+str(pid)+"/cmdline","rb") as f:
            data = f.read(32769)
        if len(data)>32768 or not data.endswith(b"\0"):
            return result
        args = [os.fsdecode(v) for v in data[:-1].split(b"\0")]
        if sum(a in ("scripts/private_server.py","/opt/remura/scripts/private_server.py") for a in args)!=1:
            return result
        found = []
        for i,a in enumerate(args):
            if a == "--database":
                if i+1>=len(args) or args[i+1].startswith("-"):
                    return result
                found.append(args[i+1])
            elif a.startswith("--database="):
                found.append(a.split("=",1)[1])
        if len(found)>1 or (found and not found[0]):
            return result
        location = Path(found[0]) if found else Path("/opt/remura/private/remura-prices.sqlite3")
        if not location.is_absolute():
            location = Path("/opt/remura")/location
        if ".." in location.parts or any(p.is_symlink() for p in (location,*location.parents)):
            return result
        # Recheck PID before reporting metadata; no runtime DB open.
        live = subprocess.check_output(["systemctl","show","remura-private.service","-p","MainPID","--value"],stderr=subprocess.DEVNULL,text=True,timeout=10).strip()
        if live != str(pid):
            return result
        result["database_path_state"] = "explicit_arg" if found else "repository_default_candidate"
        result["database_metadata"] = metadata(location)
        result["fixed_candidates"] = {k:metadata(location.parent/v) for k,v in FIXED.items()}
        disk = os.statvfs("/opt/remura")
        result["disk_available_bytes"] = disk.f_bavail*disk.f_frsize
    except (OSError,ValueError,subprocess.SubprocessError):
        result["database_path_state"] = "unavailable"
    return result

def main():
    p = argparse.ArgumentParser(description=__doc__)
    m = p.add_mutually_exclusive_group(required=True)
    m.add_argument("--closed-db",type=Path,help="existing closed recovered copy, NEVER live")
    m.add_argument("--oracle-metadata",action="store_true")
    p.add_argument("--confirm-closed-copy",action="store_true")
    a = p.parse_args()
    try:
        if a.closed_db:
            if not a.confirm_closed_copy:
                raise ValueError("explicit_closed_copy_required")
            report = cot_closed(a.closed_db)
        else:
            report = oracle_metadata()
        print(json.dumps({"schema":SCHEMA,"status":"diagnostic_only",
                          "release_authorized":False,"result":report},sort_keys=True))
    except (OSError,ValueError,sqlite3.Error,subprocess.SubprocessError):
        print(json.dumps({"schema":SCHEMA,"status":"unavailable_or_unsafe","release_authorized":False}))
        return 2
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
