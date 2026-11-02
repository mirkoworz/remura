#!/usr/bin/env python3
"""REMURA v1.56 manual guarded release. Never runs as part of auto-update.

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
    "scripts/price_feed.py", "scripts/ctrader_feed.py", "scripts/price_store.py",
    "price-core.js", "price.js", "price.css", "nav.js", "sw.js",
    "index.html", "asset.html", "mercati.html", "forex.html", "catalogo.html",
    "statistica-squali.html", "stato-prezzi.html", "fonti.html", "impostazioni.html",
)
BACKUP_MODULE = "deploy/oracle/backup_v156.py"
MAX_ZIP = 50 * 1024 * 1024
MAX_FILE = 3 * 1024 * 1024


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
        "Accept": "application/vnd.github+json", "User-Agent": "REMURA-v156-manual-release"
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
    require(b"Aggiornamento v1.56" in chosen["nav.js"], "WRONG_BANNER")
    require(b"remura-shell-v70-v1.56" in chosen["sw.js"], "WRONG_CACHE")
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


def local_files():
    require(APP.is_dir() and not APP.is_symlink(), "APP_DIRECTORY")
    require(PRIVATE.is_dir() and not PRIVATE.is_symlink(), "PRIVATE_DIRECTORY")
    originals = {}
    for path in FILES:
        target = APP / path
        require(target.is_file() and not target.is_symlink(), "LOCAL_FILE_MISSING")
        require(stat.S_ISREG(target.lstat().st_mode), "LOCAL_FILE_TYPE")
        info = target.stat()
        require(info.st_size <= MAX_FILE, "LOCAL_FILE_TOO_LARGE")
        originals[path] = (target.read_bytes(), info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode))
    return originals


def preflight(sha, staged=None):
    require(os.geteuid() == 0, "ROOT_REQUIRED")
    require(unit("is-active", SERVICE) == "active" and healthy(), "SERVER_NOT_HEALTHY")
    require(unit("is-active", "remura-autoupdate.service") != "active", "AUTOUPDATE_BUSY")
    originals = local_files()
    # Do not silently apply to an unknown version or an already installed v1.56.
    require(b"Aggiornamento v1.55" in originals["nav.js"][0], "EXPECTED_V155")
    staged = staged if staged is not None else candidate(sha)
    require(all(originals[p][0] != staged[p] for p in ("nav.js", "sw.js")), "ALREADY_INSTALLED")
    # Existing SQLite file, integrity and disk free space.
    source = PRIVATE / "remura-prices.sqlite3"
    require(source.is_file() and not source.is_symlink(), "SQLITE_SOURCE_MISSING")
    import sqlite3
    with sqlite3.connect(source.as_uri() + "?mode=ro", uri=True, timeout=25) as db:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "SQLITE_INTEGRITY")
        tables = {x[0] for x in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        require({"prices", "status"} <= tables, "SQLITE_SCHEMA")
    estimate = source.stat().st_size * 3 + sum(len(v[0]) for v in originals.values()) * 3
    require(shutil.disk_usage(PRIVATE).free > estimate + 20 * 1024 * 1024, "DISK_SPACE")
    return staged, originals


def atomic_write(path, data, uid, gid, mode):
    require(path.is_file() and not path.is_symlink(), "DESTINATION_INVALID")
    fd, tmp = tempfile.mkstemp(prefix=".remura-v156-", dir=path.parent)
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
    path = Path(tempfile.mkdtemp(prefix="rollback-v156-", dir=BACKUPS))
    try:
        path.chmod(0o700)
        manifest = {"schema": "remura-v156-rollback-v1", "commit": sha, "files": {}}
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
    with (WORK / "lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        staged, originals = preflight(sha)
        # Run the audited backup module from the verified candidate, not an
        # arbitrary local path. Its __name__ is not '__main__'.
        namespace = {"__name__": "remura_backup_v156"}
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
            for name in FILES:
                previous = originals[name]
                changed.append(name)
                atomic_write(APP / name, staged[name], previous[1], previous[2], previous[3])
            require(all(digest((APP / name).read_bytes()) == digest(staged[name])
                        for name in FILES), "POST_INSTALL_HASH")
            result = subprocess.run(["systemctl", "start", SERVICE], capture_output=True, timeout=35)
            require(result.returncode == 0 and wait_health(), "POST_INSTALL_HEALTH")
            print("RILASCIO_V156=OK", flush=True)
            print("FILE_INSTALLATI=" + str(len(FILES)), flush=True)
            print("DATABASE_LIVE_NON_RIPRISTINATO=SI", flush=True)
            print("AUTUPDATE_STATE_NON_MODIFICATO=SI", flush=True)
        except BaseException:
            if stopped:
                try:
                    restore_originals({name: originals[name] for name in changed})
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
    require(path.parent == BACKUPS and path.name.startswith("rollback-v156-"),
            "ROLLBACK_PATH")
    require(path.is_dir() and not path.is_symlink(), "ROLLBACK_DIRECTORY")
    manifest = json.loads((path / "manifest.json").read_text("utf-8"))
    require(manifest.get("schema") == "remura-v156-rollback-v1", "ROLLBACK_SCHEMA")
    require(set(manifest.get("files", {})) == set(FILES), "ROLLBACK_FILE_SET")
    with (WORK / "lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        originals = local_files()
        prior = {}
        for name in FILES:
            data = (path / name).read_bytes()
            require(digest(data) == manifest["files"][name]["old"] and
                    digest(originals[name][0]) == manifest["files"][name]["new"],
                    "ROLLBACK_HASH_OR_LIVE_CHANGED")
            previous = originals[name]
            prior[name] = (data, previous[1], previous[2], previous[3])
        result = subprocess.run(["systemctl", "stop", SERVICE], capture_output=True, timeout=35)
        require(result.returncode == 0, "ROLLBACK_STOP")
        restore_originals(prior)
        result = subprocess.run(["systemctl", "start", SERVICE], capture_output=True, timeout=35)
        require(result.returncode == 0 and wait_health(), "ROLLBACK_RESTART")
        print("ROLLBACK_V156=OK")


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
                print("PREFLIGHT_V156=OK")
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
