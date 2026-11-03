#!/usr/bin/env python3
"""REMURA v1.60 manual guarded release. Never runs as part of auto-update.

Two explicit stages:
  --check --commit SHA: READ-ONLY. Validate pinned GitHub tree, live service,
                         local source files, and SQLite integrity/space.
  --apply --commit SHA:  exclusive lock; verify again; consistent SQLite backup
                         and isolated restore test; persist file rollback copy;
                         replace approved files; restart server; check health.
  --rollback-dir PATH:   explicit recovery from the saved file rollback bundle.
No API credentials, trading orders, private database uploads or automatic merge.
"""
from __future__ import annotations

import argparse
import datetime as dt
import fcntl
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import shutil
import sqlite3
import stat
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

APP = Path("/opt/remura")
PRIVATE = APP / "private"
BACKUPS = PRIVATE / "predeploy-backups"
WORK = Path("/var/lib/remura-autoupdate")
SERVICE = "remura-private.service"
API = "https://api.github.com/repos/mirkoworz/remura"
FILES = (
    "scripts/private_server.py", "scripts/signals_monitor.py", "nav.js", "sw.js",
    "index.html", "asset.html", "mercati.html", "forex.html", "catalogo.html",
    "statistica-squali.html", "stato-prezzi.html", "fonti.html", "impostazioni.html",
    "scripts/squalincome_timing.py",
    "squalincome-diagnostics.js", "squalincome-freshness-core.js",
)
BACKUP_MODULE = "deploy/oracle/backup_v156.py"
MAX_ZIP = 50 * 1024 * 1024
MAX_FILE = 3 * 1024 * 1024
NEW_FILE = "squalincome-freshness-core.js"
EXISTING_FILES = tuple(name for name in FILES if name != NEW_FILE)
BASE_SHA = "e924f4cf6f1a384fd84a3cef66c89a16e35de3fd"
BASE_BLOBS = {
    "scripts/private_server.py": "742ade310b91b06d508e7dc7477467581583bebc",
    "scripts/signals_monitor.py": "f03c9ae944da907faa15bc75b133cad9dc2f07eb",
    "nav.js": "38487acf42c418b28da457547d2961146667d436",
    "sw.js": "f23701d7dab7dcb32fd6a9b8306924205e75a236",
    "index.html": "cc269a24d4ee30ced19665ac8f56fa041480af23",
    "asset.html": "e0ebe131ce8716ed899a8df774f52b2140124282",
    "mercati.html": "29adf5cfae85f1d983df6a826331e4a5ec8959fe",
    "forex.html": "0da02aa6e589bf8ae638213e026e239d94af3772",
    "catalogo.html": "1d83341faabe60eb314a4eb8e30eb7d45ca7e84c",
    "statistica-squali.html": "b8869404999fedc6c65c6926c3d8655c9da7817c",
    "stato-prezzi.html": "f125e743e6b461607880c7de83b4693132e335f8",
    "fonti.html": "40e4132135e2b6ddec5d7d2e4f7e6a8a3a3d384b",
    "impostazioni.html": "f02c6f30bb199ddd62edf7864756ebc96f9ebb21",
    "scripts/squalincome_timing.py": "0034280c51fd05ac382d1f1a6d25da1d52939499",
    "squalincome-diagnostics.js": "c73f8bd4fab4165accbcc8e224720457c5eee655",
}

BACKUP_BLOB = "dc01f2b4767a5427b1d65b96f7a883870b82f608"
OLD_STAMP = b"03/11/2026 06:40 (Italia, preparazione)"
LIVE_STAMP = re.compile(rb"(?:0[1-9]|[12][0-9]|3[01])/(?:0[1-9]|1[0-2])/20[0-9]{2} (?:[01][0-9]|2[0-3]):[0-5][0-9] \(Italia\)")
PREPARED_STAMP = b"03/11/2026 11:20 (Italia, preparazione)"
WORKFLOWS = ("price-checks.yml", "insights-checks.yml")
ALLOWED = set(FILES) | {
    "ROADMAP.md","V159-SQUALINCOME-TIMING.md","V159-RELEASE-PLAN.md",
    "V160-SQUALINCOME-FRESHNESS-PROTOTYPE.md","V160-RELEASE-PLAN.md",
    "deploy/oracle/release_v160.py","deploy/oracle/reconcile_v160.py",
    "tests/test_release_v160.py","tests/test_reconcile_v160.py",
    "tests/test_release_v159.py","tests/release-consistency.test.js",
    "tests/test_signals_monitor.py","tests/test_private_server.py",
    "tests/squalincome-freshness.test.js","tests/squalincome-diagnostics.test.js",
    ".github/workflows/price-checks.yml",".github/workflows/insights-checks.yml",
}
REQUIRED = {
    "scripts/private_server.py", "scripts/signals_monitor.py",
    "squalincome-diagnostics.js","squalincome-freshness-core.js",
    "nav.js", "sw.js", "deploy/oracle/release_v160.py",
    "tests/test_release_v160.py", "tests/squalincome-freshness.test.js"
} | {p for p in FILES if p.endswith(".html")}



def require(ok, code):
    if not ok:
        raise RuntimeError("STOP_" + code)


def valid_sha(sha):
    return isinstance(sha, str) and len(sha) == 40 and all(c in "0123456789abcdef" for c in sha)


def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def digest(data):
    return hashlib.sha256(data).hexdigest()


def api_read(path, cap=MAX_ZIP):
    req = urllib.request.Request(API + path, headers={
        "Accept": "application/vnd.github+json", "User-Agent": "REMURA-v160-manual-release"
    })
    with urllib.request.urlopen(req, timeout=35) as reply:
        data = reply.read(cap + 1)
    require(len(data) <= cap, "DOWNLOAD_OVERSIZE")
    return data


def candidate(sha):
    require(valid_sha(sha), "COMMIT_INVALID")
    raw = json.loads(api_read("/git/trees/" + sha + "?recursive=1", 6 * 1024 * 1024))
    require(isinstance(raw, dict) and raw.get("truncated") is False, "TREE_INCOMPLETE")
    blobs = {x.get("path"): x.get("sha") for x in raw.get("tree", [])
             if isinstance(x, dict) and x.get("type") == "blob"}
    selected = (*FILES, BACKUP_MODULE)
    require(all(isinstance(blobs.get(p), str) and len(blobs[p]) == 40 for p in selected),
            "TREE_MISSING_FILES")
    archive = api_read("/zipball/" + sha)
    try:
        handle = zipfile.ZipFile(io.BytesIO(archive))
        with handle as zipf:
            require(len(zipf.infolist()) < 6000, "ARCHIVE_FILE_COUNT")
            chosen = {}
            for entry in zipf.infolist():
                parts = entry.filename.split("/")
                if entry.filename.startswith("/") or ".." in parts or "\\\\" in entry.filename:
                    raise RuntimeError("STOP_UNSAFE_ARCHIVE")
                if len(parts) < 2 or entry.is_dir():
                    continue
                relative = "/".join(parts[1:])
                if relative not in selected:
                    continue
                mode_type = (entry.external_attr >> 16) & 0o170000
                require(mode_type in (0, stat.S_IFREG), "ARCHIVE_NOT_REGULAR")
                require(relative not in chosen and entry.file_size <= MAX_FILE, "ARCHIVE_DUP_OR_OVERSIZE")
                content = zipf.read(entry)
                require(len(content) == entry.file_size and git_blob(content) == blobs[relative],
                        "GIT_BLOB_MISMATCH")
                chosen[relative] = content
    except (zipfile.BadZipFile, EOFError) as exc:
        raise RuntimeError("STOP_ARCHIVE_INVALID") from exc
    require(set(chosen) == set(selected), "ARCHIVE_FILES_MISSING")
    require(b"Aggiornamento v1.60" in chosen["nav.js"], "WRONG_BANNER")
    require(b"remura-shell-v74-v1.60" in chosen["sw.js"], "WRONG_CACHE")
    require(all(b"nav.js?v=160" in chosen[p] for p in FILES if p.endswith(".html")),
            "PAGE_CACHE_VERSION_MISMATCH")
    require(git_blob(chosen[BACKUP_MODULE]) == BACKUP_BLOB, "BACKUP_CHANGED")
    require(b"from squalincome_timing import record as record_scan_timing" in
            chosen["scripts/private_server.py"], "MISSING_TELEMETRY_IMPORT")
    require(b"def record(db_path, *, kind, started, completed" in
            chosen["scripts/squalincome_timing.py"], "MISSING_TIMING_MODULE")
    require(b"def observe_updated_batch(" in chosen["scripts/private_server.py"],
            "MISSING_POST_INGEST_HOOK")
    require(b"def scan_once(db_path,now=None,*,targets=None)" in chosen["scripts/signals_monitor.py"],
            "MISSING_TARGETED_SCAN")
    require(b'"squalincome-freshness-core.js"' in chosen["scripts/private_server.py"],
            "MISSING_SAFE_FRESHNESS_ASSET")
    require(b'squalincome-freshness-core.js?v=160' in chosen["mercati.html"],
            "MISSING_FRESHNESS_UI")
    require(b'./squalincome-freshness-core.js' in chosen["sw.js"],
            "MISSING_FRESHNESS_PRECACHE")
    require(b'priceQuality' in chosen["scripts/signals_monitor.py"],
            "MISSING_ATOMIC_QUALITY")
    require(b'signalAuthorized:false' in chosen[NEW_FILE],
            "FRESHNESS_SIGNAL_GATE")
    require(b'priceQuality' in chosen["squalincome-diagnostics.js"],
            "MISSING_FRESHNESS_RENDER")
    compile(chosen[BACKUP_MODULE], BACKUP_MODULE, "exec")
    for item in FILES:
        if item.endswith(".py"):
            compile(chosen[item], item, "exec")
    return chosen


def unit(action, name):
    result = subprocess.run(["systemctl", action, name],
                            capture_output=True, text=True, timeout=20)
    return result.stdout.strip()


def healthy():
    try:
        with urllib.request.urlopen("http://127.0.0.1:8765/private-api/health", timeout=5) as answer:
            return answer.status == 200 and json.load(answer).get("name") == "REMURA Private"
    except (OSError, ValueError, TimeoutError):
        return False


def release_stamp(staged, now=None):
    """Change only the reviewed banner timestamp at actual installation time.

    The source is first verified against the pinned Git tree; the one allowed
    local transformation is recorded in the rollback manifest's new hash.
    """
    from zoneinfo import ZoneInfo
    pattern = PREPARED_STAMP
    require(staged["nav.js"].count(pattern) == 1, "EXPECTED_RELEASE_STAMP")
    current = (now or dt.datetime.now(ZoneInfo("Europe/Rome")))
    stamp = current.astimezone(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M (Italia)")
    updated = dict(staged)
    updated["nav.js"] = staged["nav.js"].replace(pattern, stamp.encode("ascii"))
    return updated


def read_live_files(names):
    require(APP.is_dir() and not APP.is_symlink(), "APP_DIRECTORY")
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink(), "PRIVATE_DIRECTORY")
    originals = {}
    for name in names:
        target = APP / name
        require(target.is_file() and not target.is_symlink(), "LOCAL_FILE_MISSING")
        require(stat.S_ISREG(target.lstat().st_mode), "LOCAL_FILE_TYPE")
        info = target.stat()
        require(info.st_size <= MAX_FILE, "LOCAL_FILE_TOO_LARGE")
        originals[name] = (target.read_bytes(), info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
    return originals


def local_files():
    new = APP / NEW_FILE
    require(not os.path.lexists(new), "NEW_MODULE_ALREADY_PRESENT")
    return read_live_files(EXISTING_FILES)


def remote_doc(path):
    obj = json.loads(api_read(path, 6 * 1024 * 1024))
    require(isinstance(obj, dict), "REMOTE_INVALID")
    return obj


def verify_target(sha):
    require(remote_doc("/commits/main").get("sha") == sha, "MAIN_MOVED")
    result = remote_doc("/compare/" + BASE_SHA + "..." + sha)
    require(result.get("status") == "ahead", "INVALID_RELEASE_ANCESTRY")
    changed = result.get("files")
    require(isinstance(changed, list) and 0 < len(changed) < 200, "DIFF_INVALID")
    paths = [x.get("filename") for x in changed if isinstance(x, dict)]
    require(len(paths) == len(changed) and len(set(paths)) == len(paths), "DIFF_INVALID")
    require(REQUIRED <= set(paths), "RELEASE_INCOMPLETE")
    require(all(isinstance(p,str) and
        (p in ALLOWED or p.startswith("data/myfxbook/")) for p in paths), "UNREVIEWED_FILES")
    for name in WORKFLOWS:
        runs = remote_doc("/actions/workflows/" + name +
            "/runs?event=push&head_sha=" + sha + "&per_page=20").get("workflow_runs")
        require(isinstance(runs, list), "CI_MISSING")
        matched = [r for r in runs if isinstance(r,dict) and
                   r.get("head_sha")==sha and r.get("head_branch")=="main"
                   and r.get("event")=="push"]
        require(matched and all(r.get("status")=="completed" and
                r.get("conclusion")=="success" for r in matched), "CI_NOT_GREEN")


def verify_live_v159(originals):
    require(set(originals)==set(BASE_BLOBS)==set(EXISTING_FILES), "BASE_FILE_SET")
    for name,(content,_,_,_) in originals.items():
        if name=="nav.js":
            stamps=LIVE_STAMP.findall(content)
            require(len(stamps)==1, "LIVE_STAMP_INVALID")
            content=content.replace(stamps[0],OLD_STAMP)
        require(git_blob(content)==BASE_BLOBS[name], "LIVE_V159_DIVERGED")


def verify_flag_on():
    source=PRIVATE/"remura.env"
    require(source.is_file() and not source.is_symlink() and source.stat().st_size<32768,
            "PRIVATE_ENV_INVALID")
    values=[]
    for line in source.read_text("utf-8").splitlines():
        line=line.strip()
        if not line or line.startswith("#"):continue
        if line.startswith("REMURA_SQUALINCOME_AFTER_INGEST_ENABLED="):
            values.append(line.split("=",1)[1].strip().strip('"').strip("'"))
    require(len(values)==1 and values[0]=="1", "POST_INGEST_FLAG_NOT_ON")


def preflight(sha, staged=None):
    require(os.geteuid()==0, "ROOT_REQUIRED")
    require(valid_sha(sha), "COMMIT_INVALID")
    require(unit("is-active",SERVICE)=="active" and healthy(), "SERVER_NOT_HEALTHY")
    require(unit("is-active","remura-autoupdate.service")!="active", "AUTOUPDATE_BUSY")
    originals=local_files()
    verify_live_v159(originals)
    verify_flag_on()
    statefile=PRIVATE/"autoupdate-state.json"
    require(statefile.is_file() and not statefile.is_symlink(), "STATE_MISSING")
    state=json.loads(statefile.read_text("utf-8"))
    require(isinstance(state,dict) and state.get("enabled") is True and
        state.get("installedSha")==BASE_SHA and
        state.get("state") in ("up_to_date","data_only","manual_required") and
        state.get("failedSha") in ("",None), "STATE_UNEXPECTED")
    verify_target(sha)
    staged=staged if staged is not None else candidate(sha)
    require(all(originals[p][0]!=staged[p] for p in ("nav.js","sw.js")),
            "ALREADY_INSTALLED")
    source=PRIVATE/"remura-prices.sqlite3"
    require(source.is_file() and not source.is_symlink(), "SQLITE_SOURCE_MISSING")
    with sqlite3.connect(source.as_uri()+"?mode=ro",uri=True,timeout=25) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0]=="ok",
                "SQLITE_INTEGRITY")
        tables={r[0] for r in db.execute(
            "SELECT name FROM sqlite_master WHERE type='table'")}
        require({"prices","status"} <= tables,"SQLITE_SCHEMA")
    estimate=source.stat().st_size*3+sum(len(v[0]) for v in originals.values())*3
    require(shutil.disk_usage(PRIVATE).free>estimate+20*1024*1024,"DISK_SPACE")
    require(remote_doc("/commits/main").get("sha")==sha,"MAIN_MOVED")
    return staged,originals


def atomic_create(path, data, uid, gid, mode):
    require(path.parent.is_dir() and not path.parent.is_symlink(), "NEW_PARENT_INVALID")
    require(not os.path.lexists(path), "NEW_MODULE_ALREADY_PRESENT")
    fd, tmp = tempfile.mkstemp(prefix=".remura-v160-module-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchown(out.fileno(), uid, gid)
            os.fchmod(out.fileno(), mode)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        require(not os.path.lexists(path), "NEW_MODULE_ALREADY_PRESENT")
        os.replace(tmp, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try: os.fsync(directory)
        finally: os.close(directory)
    finally:
        if os.path.exists(tmp): os.unlink(tmp)


def remove_new_module(expected_hash):
    target = APP / NEW_FILE
    require(target.is_file() and not target.is_symlink(), "NEW_MODULE_NOT_REGULAR")
    require(digest(target.read_bytes()) == expected_hash, "NEW_MODULE_HASH_CHANGED")
    target.unlink()
    directory = os.open(target.parent, os.O_RDONLY | os.O_DIRECTORY)
    try: os.fsync(directory)
    finally: os.close(directory)


def atomic_write(path, data, uid, gid, mode):
    require(path.is_file() and not path.is_symlink(), "DESTINATION_INVALID")
    fd, tmp = tempfile.mkstemp(prefix=".remura-v160-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as out:
            os.fchown(out.fileno(), uid, gid)
            os.fchmod(out.fileno(), mode)
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
        folder = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(folder)
        finally:
            os.close(folder)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def saved_rollback(originals, staged, sha):
    require(BACKUPS.is_dir() and not BACKUPS.is_symlink(), "BACKUP_DIR_MISSING")
    os.umask(0o077)
    path = Path(tempfile.mkdtemp(prefix="rollback-v160-", dir=BACKUPS))
    try:
        path.chmod(0o700)
        manifest = {"schema": "remura-v160-rollback-v1", "commit": sha, "files": {}}
        manifest["files"][NEW_FILE] = {"old": None, "new": digest(staged[NEW_FILE])}
        for name, (content, _, _, _) in originals.items():
            output = path / name
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_bytes(content)
            output.chmod(0o600)
            manifest["files"][name] = {
                "old": digest(content), "new": digest(staged[name]),
            }
        info = path / "manifest.json"
        info.write_text(json.dumps(manifest, sort_keys=True), encoding="utf-8")
        info.chmod(0o600)
        return path
    except BaseException:
        shutil.rmtree(path, ignore_errors=True)
        raise


def restore_originals(originals):
    for name, (content, uid, gid, mode) in originals.items():
        atomic_write(APP / name, content, uid, gid, mode)
        require(digest((APP / name).read_bytes()) == digest(content), "ROLLBACK_HASH")


def wait_health():
    for _ in range(12):
        if unit("is-active", SERVICE) == "active" and healthy():
            return True
        time.sleep(1)
    return False


def apply(sha):
    # Uses the same lock as autoupdate to avoid simultaneous code replacement.
    require(os.geteuid() == 0, "ROOT_REQUIRED")
    require(WORK.is_dir() and not WORK.is_symlink(), "AUTOUPDATE_LOCK_DIR")
    require((WORK/"lock").is_file() and not (WORK/"lock").is_symlink(),"LOCK_INVALID")
    with (WORK / "lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        staged, originals = preflight(sha)
        staged = release_stamp(staged)
        require(remote_doc("/commits/main").get("sha")==sha,"MAIN_MOVED")
        # Run the audited backup module from the verified candidate, not an
        # arbitrary local path. Its __name__ is not '__main__'.
        namespace = {"__name__": "remura_backup_v160"}
        exec(compile(staged[BACKUP_MODULE], BACKUP_MODULE, "exec"), namespace)
        backup_status = namespace["create_backup"]()
        require("RESTORE_TEST=OK" in backup_status, "BACKUP_RESTORE_TEST")
        rollback = saved_rollback(originals, staged, sha)
        print("BACKUP_SQLITE=VERIFICATO", flush=True)
        print("RESTORE_TEST=OK", flush=True)
        print("ROLLBACK_DIR=" + str(rollback), flush=True)
        changed = []
        stopped = False
        try:
            result = subprocess.run(["systemctl", "stop", SERVICE], capture_output=True, timeout=35)
            stopped = (unit("is-active", SERVICE) != "active")
            require(result.returncode == 0, "SERVICE_STOP")
            stopped = True
            for name in EXISTING_FILES:
                previous = originals[name]
                changed.append(name)
                atomic_write(APP / name, staged[name], previous[1], previous[2], previous[3])
            changed.append(NEW_FILE)
            owner = originals["scripts/private_server.py"]
            atomic_create(APP / NEW_FILE, staged[NEW_FILE], owner[1], owner[2], owner[3])
            require(all(digest((APP / name).read_bytes()) == digest(staged[name])
                        for name in FILES), "POST_INSTALL_HASH")
            result = subprocess.run(["systemctl", "start", SERVICE], capture_output=True, timeout=35)
            require(result.returncode == 0 and wait_health(), "POST_INSTALL_HEALTH")
            print("RILASCIO_V160=OK", flush=True)
            print("FILE_INSTALLATI=" + str(len(FILES)), flush=True)
            print("DATABASE_LIVE_NON_RIPRISTINATO=SI", flush=True)
            print("AUTUPDATE_STATE_NON_MODIFICATO=SI", flush=True)
        except BaseException:
            if stopped:
                try:
                    restore_originals({name: originals[name] for name in changed
                                       if name in originals})
                    if os.path.lexists(APP / NEW_FILE):
                        remove_new_module(digest(staged[NEW_FILE]))
                    subprocess.run(["systemctl", "restart", SERVICE],
                                   capture_output=True, timeout=35)
                    require(wait_health(), "ROLLBACK_HEALTH")
                    print("ROLLBACK=OK", flush=True)
                except BaseException:
                    print("ROLLBACK=ATTENZIONE_CONTROLLO_MANUALE", flush=True)
            raise


def rollback_from(path):
    require(os.geteuid() == 0, "ROOT_REQUIRED")
    require(WORK.is_dir() and not WORK.is_symlink(), "AUTOUPDATE_LOCK_DIR")
    require(BACKUPS.is_dir() and not BACKUPS.is_symlink(), "BACKUP_DIR_MISSING")
    require(path.parent == BACKUPS and path.name.startswith("rollback-v160-"),
            "ROLLBACK_PATH")
    require(path.is_dir() and not path.is_symlink(), "ROLLBACK_DIRECTORY")
    manifest = json.loads((path / "manifest.json").read_text("utf-8"))
    require(manifest.get("schema") == "remura-v160-rollback-v1", "ROLLBACK_SCHEMA")
    require(set(manifest.get("files", {})) == set(FILES), "ROLLBACK_FILE_SET")
    require((WORK/"lock").is_file() and not (WORK/"lock").is_symlink(),"LOCK_INVALID")
    with (WORK / "lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        originals = read_live_files(FILES)
        prior = {}
        require(manifest["files"][NEW_FILE].get("old") is None
                and not (path / NEW_FILE).exists(), "ROLLBACK_NEW_FILE")
        for name in FILES:
            require(digest(originals[name][0]) == manifest["files"][name]["new"],
                    "ROLLBACK_HASH_OR_LIVE_CHANGED")
            if name == NEW_FILE:
                continue
            target = path / name
            require(target.is_file() and not target.is_symlink(), "ROLLBACK_OLD_MISSING")
            data = target.read_bytes()
            require(digest(data) == manifest["files"][name]["old"],
                    "ROLLBACK_HASH_OR_LIVE_CHANGED")
            previous = originals[name]
            prior[name] = (data, previous[1], previous[2], previous[3])
        result = subprocess.run(["systemctl", "stop", SERVICE], capture_output=True, timeout=35)
        require(result.returncode == 0, "ROLLBACK_STOP")
        restore_originals(prior)
        remove_new_module(manifest["files"][NEW_FILE]["new"])
        result = subprocess.run(["systemctl", "start", SERVICE], capture_output=True, timeout=35)
        require(result.returncode == 0 and wait_health(), "ROLLBACK_RESTART")
        print("ROLLBACK_V160=OK")


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--check", action="store_true")
    choice.add_argument("--apply", action="store_true")
    choice.add_argument("--rollback-dir", type=Path)
    parser.add_argument("--commit", default="")
    args = parser.parse_args()
    try:
        if args.rollback_dir:
            require(not args.commit, "ROLLBACK_SHA_NOT_ALLOWED")
            rollback_from(args.rollback_dir)
        else:
            require(valid_sha(args.commit), "COMMIT_INVALID")
            if args.check:
                preflight(args.commit)
                print("PREFLIGHT_V160=OK")
                print("VERSIONE_LIVE_INVARIATA=SI")
                print("BACKUP_SQLITE_NON_ANCORA_ESEGUITO=SI")
            else:
                apply(args.commit)
        return 0
    except BaseException as error:
        # Path/body/URL/traceback and broker tokens are deliberately never logged.
        print("ESITO=STOP")
        code = str(error)
        print("MOTIVO=" + (code if code.startswith("STOP_") else "ERRORE_NON_PUBBLICO"))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
