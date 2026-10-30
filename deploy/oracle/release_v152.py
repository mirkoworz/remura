#!/usr/bin/env python3
"""REMURA v1.52 guarded manual release. No automatic trades or database writes.
--check: read only. --apply: explicit manual approval; resilient via systemd-run.
"""
import argparse
import hashlib
import json
import os
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

APP = Path("/opt/remura")
PRIVATE = APP / "private"
STAGE = PRIVATE / "predeploy-staging/remura-v152-pr62"
BACKUP_DIR = PRIVATE / "predeploy-backups"
MANIFEST = "staging-manifest.json"
SOURCE_COMMIT = "51bcdb2f73204ec98acd5b8338daadd68d696caf"
BLOBS = {
    "nav.js": "fd00e36ad78890c027050cf08c8f2b1a0e88048c",
    "sw.js": "4d00413c74927bda244a165fe569bde9a74d256e",
    "index.html": "b00a010ac57ac4fbb32b944ba5e6f729c4e6c228",
    "forex.html": "df2cf0de6e58fd7bd84931f7fc0d6bdea9f14a66",
    "mercati.html": "c89476f73a2d621310f495d8553e1ccef50dd188",
    "asset.html": "11d3f53f500e43178e78f59edcfab45b43c4eee8",
    "catalogo.html": "a21554fe4ca5c2a67fa22e6a7415b3786657c8f1",
    "fonti.html": "0c67de41e6cf50d51403d191747aa040c5553dc1",
    "impostazioni.html": "71cab3fff2dc91dc2fdd3d957c4d117fe25cc149",
    "stato-prezzi.html": "530894d44051e8d01d3d27fb28c3a6923f3d0c7a",
    "statistica-squali.html": "6ab89b5c05e87745eb554ff84f8dd6eb4facdb03",
    "deploy/oracle/autoupdate.py": "53ca8ec381e30d019f1cc8570e33e0150e6c233e"
}
SERVICE = "remura-private.service"
LEGACY_TIMER = "remura-myfxbook-sync.timer"

def require(condition, message):
    if not condition:
        raise RuntimeError("STOP: " + message)

def git_blob(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\\0" + data).hexdigest()

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def unit(action, name):
    r = subprocess.run(["systemctl", action, name], capture_output=True, text=True, timeout=10)
    return r.stdout.strip()

def healthy():
    try:
        with urlopen("http://127.0.0.1:8765/private-api/health", timeout=5) as r:
            return r.status == 200 and json.load(r).get("name") == "REMURA Private"
    except (OSError, ValueError, TimeoutError):
        return False

def fresh_backup():
    backups = sorted(BACKUP_DIR.glob("safe-v151-before-v152-*"),
                     key=lambda p: p.stat().st_mtime, reverse=True)
    require(bool(backups), "backup pre-release assente")
    path = backups[0]
    require(path.is_dir() and not path.is_symlink(), "backup non regolare")
    manifest = json.loads((path / "manifest.json").read_text())
    require(isinstance(manifest, dict) and len(manifest) >= 52,
            "manifest backup inatteso")
    for rel, expected in manifest.items():
        source = path / rel
        require(source.is_file() and not source.is_symlink() and
                sha256(source.read_bytes()) == expected,
                "copia backup non valida: " + str(rel))
    sql = path / "sqlite/remura-prices.sqlite3"
    connection = sqlite3.connect(sql.as_uri() + "?mode=ro", uri=True)
    try:
        require(connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok",
                "integrita SQLite backup non OK")
    finally:
        connection.close()
    return path, manifest

def prepare():
    require(os.geteuid() == 0, "root richiesto")
    require(STAGE.is_dir() and not STAGE.is_symlink(), "staging non regolare")
    require(unit("is-active", SERVICE) == "active" and healthy(), "backend/API non sano")
    require(unit("is-enabled", LEGACY_TIMER) == "disabled" and
            unit("is-active", LEGACY_TIMER) == "inactive", "sync legacy non disabilitato")
    require(unit("is-active", "remura-autoupdate.service") != "active",
            "autoupdate attualmente in esecuzione")
    state = json.loads((PRIVATE / "autoupdate-state.json").read_text())
    require(state.get("state") == "manual_required",
            "autoupdate non in stato manual_required")
    backup, manifest = fresh_backup()
    stage_manifest = json.loads((STAGE / MANIFEST).read_text())
    require(stage_manifest.get("commit") == SOURCE_COMMIT and
            stage_manifest.get("files") == BLOBS,
            "manifest staging differente da codice verificato")
    changes = {}
    for rel, expected_blob in BLOBS.items():
        source, live = STAGE / rel, APP / rel
        require(source.is_file() and not source.is_symlink() and
                live.is_file() and not live.is_symlink(),
                "file mancante o symlink: " + rel)
        new, old = source.read_bytes(), live.read_bytes()
        require(git_blob(new) == expected_blob, "hash staging diverso: " + rel)
        require(manifest.get(rel) == sha256(old) and
                sha256((backup / rel).read_bytes()) == sha256(old),
                "file live cambiato dal backup: " + rel)
        mode = live.stat()
        changes[rel] = (old, new, mode.st_uid, mode.st_gid, stat.S_IMODE(mode.st_mode))
    require("Aggiornamento v1.51" in (APP / "nav.js").read_text(),
            "banner live inatteso")
    require("Aggiornamento v1.52" in (STAGE / "nav.js").read_text(),
            "banner staging inatteso")
    require("v1.52-autoupdate-guard" in (STAGE / "sw.js").read_text(),
            "cache staging inattesa")
    compile((STAGE / "deploy/oracle/autoupdate.py").read_bytes(),
            "autoupdate.py", "exec")
    return changes

def atomic_write(path, data, uid, gid, mode):
    require(path.is_file() and not path.is_symlink(), "destinazione non regolare")
    descriptor, tmp = tempfile.mkstemp(prefix=".remura-v152-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            os.fchown(stream.fileno(), uid, gid)
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
        fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)

def apply(changes):
    # All file originals are kept in memory and in a private on-disk rollback copy.
    os.umask(0o077)
    rollback = Path(tempfile.mkdtemp(prefix="rollback-v152-", dir=BACKUP_DIR))
    rollback.chmod(0o700)
    changed = []
    try:
        for rel, (old, new, uid, gid, mode) in changes.items():
            dst = rollback / rel
            dst.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with dst.open("xb") as f:
                f.write(old)
                f.flush()
                os.fsync(f.fileno())
            dst.chmod(0o600)
            require(sha256(dst.read_bytes()) == sha256(old), "rollback non integro: " + rel)
        print("ROLLBACK_BACKUP=" + str(rollback), flush=True)
        for rel, (old, new, uid, gid, mode) in changes.items():
            changed.append(rel)
            atomic_write(APP / rel, new, uid, gid, mode)
        for rel, (_, new, _, _, _) in changes.items():
            require(sha256((APP / rel).read_bytes()) == sha256(new),
                    "post-install hash mismatch: " + rel)
        require(unit("is-active", SERVICE) == "active" and healthy(),
                "backend/API post-install non sano")
        require(unit("is-enabled", LEGACY_TIMER) == "disabled",
                "timer legacy riabilitato")
        print("ESITO=RELEASE_V152_OK", flush=True)
        print("FILE_INSTALLATI=" + str(len(changes)), flush=True)
        print("BACKEND_NON_RIAVVIATO=SI", flush=True)
        print("DATABASE_STORICI_NON_TOCcATI_DAL_RELEASE=SI", flush=True)
        print("AUTOUPDATE_SHA_NON_MODIFICATO=SI", flush=True)
    except BaseException:
        errors = []
        for rel in reversed(changed):
            old, _, uid, gid, mode = changes[rel]
            try:
                atomic_write(APP / rel, old, uid, gid, mode)
                require(sha256((APP / rel).read_bytes()) == sha256(old),
                        "hash di ripristino errato")
            except Exception as ex:
                errors.append(rel + ":" + str(ex))
        print("ROLLBACK=" + ("OK" if not errors else "PARZIALE"), flush=True)
        print("ERRORI_ROLLBACK=" + repr(errors), flush=True)
        print("BACKEND_POST_ROLLBACK=" + unit("is-active", SERVICE), flush=True)
        raise

def main():
    parser = argparse.ArgumentParser()
    options = parser.add_mutually_exclusive_group(required=True)
    options.add_argument("--check", action="store_true")
    options.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    changes = prepare()
    print("PREFLIGHT_V152=OK", flush=True)
    print("FILE_VERIFICATI=" + str(len(changes)), flush=True)
    if args.check:
        print("ESITO=PRONTO_PER_RELEASE_V152", flush=True)
        print("CODICE_LIVE_INVARIATO=SI", flush=True)
        print("NESSUN_SERVIZIO_RIAVVIATO=SI", flush=True)
    else:
        apply(changes)

if __name__ == "__main__":
    main()
