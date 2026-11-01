#!/usr/bin/env python3
"""REMURA v1.53: guarded manual release, read-only preflight and rollback."""
import argparse
import fcntl
import hashlib
import json
import os
import pwd
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import urlopen

APP = Path("/opt/remura")
STAGE = APP / "private/predeploy-staging/remura-v153"
BACKUPS = APP / "private/predeploy-backups"
STATE = APP / "private/autoupdate-state.json"
LOCK = Path("/var/lib/remura-autoupdate/lock")
TARGET = "cd54befa0234add86077eee1d3d56a8469d1df54"
OLD = "3e2a263d07e466373495e22a5eb37cbb548d2742"
FILES = (
    "index.html", "forex.html", "mercati.html", "asset.html", "catalogo.html",
    "fonti.html", "impostazioni.html", "stato-prezzi.html", "statistica-squali.html",
    "nav.js", "sw.js", "resource-health.js", "resource-health.css",
    "scripts/private_server.py", "scripts/resource_monitor.py",
)


def require(condition, reason):
    if not condition:
        raise RuntimeError("STOP_" + reason)


def run(*args):
    return subprocess.run(args, check=True, capture_output=True, text=True, timeout=60).stdout.strip()


def git_blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def request_json(path):
    try:
        with urlopen("http://127.0.0.1:8765" + path, timeout=5) as response:
            return json.load(response) if response.status == 200 else {}
    except (OSError, ValueError, TimeoutError):
        return {}


def wait_for(path, key, expected):
    for _ in range(20):
        if request_json(path).get(key) == expected:
            return True
        time.sleep(1)
    return False


def replace_file(src, dst, uid, gid, mode):
    fd, temp = tempfile.mkstemp(prefix=".remura-v153-", dir=dst.parent)
    try:
        with os.fdopen(fd, "wb") as out, src.open("rb") as inp:
            shutil.copyfileobj(inp, out)
            out.flush()
            os.fsync(out.fileno())
            os.fchown(out.fileno(), uid, gid)
            os.fchmod(out.fileno(), mode)
        os.replace(temp, dst)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)


def preflight():
    require(os.geteuid() == 0, "ROOT_RICHIESTO")
    require(STAGE.is_dir() and not STAGE.is_symlink(), "STAGING_MANCANTE")
    require(run("git", "-C", str(STAGE), "rev-parse", "HEAD") == TARGET, "SHA_STAGING_INATTESTO")
    require(not run("git", "-C", str(STAGE), "status", "--porcelain", "--untracked-files=no"), "STAGING_MODIFICATO")
    require(git_blob(APP / "scripts/private_server.py") == "f84a66d1fbd27adb80d29cb6c36e305d359944f5", "SERVER_LIVE_DIVERSO")
    require(git_blob(APP / "nav.js") == "fd00e36ad78890c027050cf08c8f2b1a0e88048c", "NAV_LIVE_DIVERSO")
    require(run("systemctl", "is-active", "remura-private.service") == "active", "SERVER_NON_ATTIVO")
    require(request_json("/private-api/health").get("name") == "REMURA Private", "HEALTH_NON_SANO")
    require(STATE.is_file() and not STATE.is_symlink(), "STATO_AUTOUPDATE_MANCANTE")
    require(BACKUPS.is_dir() and not BACKUPS.is_symlink(), "BACKUP_DIR_ASSENTE")
    require(LOCK.is_file() and not LOCK.is_symlink(), "LOCK_AUTOUPDATE_ASSENTE")
    copies = sorted(BACKUPS.glob("before-v153-*/remura-prices.sqlite3"))
    require(bool(copies), "BACKUP_SQLITE_ASSENTE")
    require(copies[-1].is_file() and not copies[-1].is_symlink(), "BACKUP_SQLITE_NON_REGOLARE")
    db = sqlite3.connect(copies[-1].as_uri() + "?mode=ro", uri=True)
    try:
        require(db.execute("PRAGMA integrity_check").fetchone()[0] == "ok", "BACKUP_SQLITE_NON_INTEGRO")
    finally:
        db.close()
    for name in FILES:
        path = STAGE / name
        require(path.is_file() and not path.is_symlink(), "FILE_STAGING_ASSENTE_" + name)
    return copies[-1]


def main():
    parser = argparse.ArgumentParser(description="REMURA v1.53 rilascio manuale protetto")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    preflight()
    with LOCK.open("r+") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError("STOP_AUTOUPDATE_OCCUPATO")
        state = json.loads(STATE.read_text(encoding="utf-8"))
        require(state.get("enabled") is True, "AUTOUPDATE_DISABILITATO")
        require(state.get("state") == "manual_required", "GATE_MANUALE_ASSENTE")
        require(state.get("installedSha") == OLD, "INSTALLED_SHA_INATTESO")
        require(state.get("targetSha") == TARGET, "TARGET_SHA_INATTESO")
        if args.check:
            print("ESITO=PRECHECK_V153_OK")
            print("TARGET=" + TARGET[:12])
            print("FILE_DA_INSTALLARE=" + str(len(FILES)))
            print("SERVER_NON_RIAVVIATO=SI")
            return

        user = pwd.getpwnam("remura")
        folder = BACKUPS / ("rollback-v153-" + datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S-%f"))
        folder.mkdir(mode=0o700)
        shutil.copy2(STATE, folder / "autoupdate-state.json")
        original = {}
        for name in FILES:
            path = APP / name
            if path.exists() or path.is_symlink():
                require(path.is_file() and not path.is_symlink(), "FILE_LIVE_NON_REGOLARE_" + name)
                st = path.stat()
                original[name] = (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode))
                backup = folder / name
                backup.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, backup)
                require(backup.read_bytes() == path.read_bytes(), "BACKUP_FILE_NON_VALIDO_" + name)
            else:
                original[name] = None
        print("BACKUP_CODICE=OK", flush=True)
        stopped = False
        try:
            run("systemctl", "stop", "remura-private.service")
            stopped = True
            for name in FILES:
                replace_file(STAGE / name, APP / name, user.pw_uid, user.pw_gid, 0o644)
            run("systemctl", "start", "remura-private.service")
            require(wait_for("/private-api/health", "name", "REMURA Private"), "HEALTH_V153_NON_SANO")
            require(wait_for("/private-api/resources", "schema", "remura-resources-v1"), "RISORSE_V153_NON_SANE")
            state.update(state="up_to_date", installedSha=TARGET, targetSha=TARGET,
                         manualSha="", failedSha="", skippedSha="",
                         lastSuccess=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                         message="Rilascio v1.53 verificato manualmente")
            fd, tmp = tempfile.mkstemp(prefix=".v153-update-", dir=STATE.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as output:
                    json.dump(state, output)
                    output.flush()
                    os.fsync(output.fileno())
                os.chmod(tmp, 0o644)
                os.replace(tmp, STATE)
            finally:
                if os.path.exists(tmp):
                    os.unlink(tmp)
            print("ESITO=RELEASE_V153_OK")
            print("API_METRICHE=OK")
            print("BACKUP_ROLLBACK=" + str(folder))
            print("NESSUNA_MIGRAZIONE_DATABASE=SI")
        except BaseException as exc:
            if stopped:
                errors = []
                try:
                    run("systemctl", "stop", "remura-private.service")
                except Exception:
                    errors.append("STOP_SERVER")
                for name in FILES:
                    try:
                        if original[name] is None:
                            (APP / name).unlink(missing_ok=True)
                        else:
                            replace_file(folder / name, APP / name, *original[name])
                    except Exception:
                        errors.append("RIPRISTINO_" + name)
                try:
                    shutil.copy2(folder / "autoupdate-state.json", STATE)
                    run("systemctl", "start", "remura-private.service")
                    require(wait_for("/private-api/health", "name", "REMURA Private"), "ROLLBACK_HEALTH")
                except Exception:
                    errors.append("RIPRISTINO_SERVER")
                print("ROLLBACK=" + ("OK" if not errors else "VERIFICARE"), flush=True)
                if errors:
                    print("ERRORI=" + ",".join(errors), flush=True)
            print("ESITO=STOP_" + type(exc).__name__, flush=True)
            raise SystemExit(1)


if __name__ == "__main__":
    main()
