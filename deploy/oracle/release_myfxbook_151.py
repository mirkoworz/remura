#!/usr/bin/env python3
"""REMURA v1.51 manual release. Standard library, no credentials or data copies.
--check is read-only; --apply is intended ONLY for systemd-run (survives SSH loss).
"""
import argparse
import hashlib
import json
import os
import shutil
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from urllib.request import urlopen

APP = Path("/opt/remura")
BACKUP = APP / "private/predeploy-backups/myfxbook-20261030-125735"
STAGE = APP / "private/predeploy-staging/myfxbook-20261030-130003"
WEB = APP / "private/predeploy-staging/remura-web-v151-pr61"
SERVICE = "remura-private.service"
OLD_TIMER = "remura-myfxbook-sync.timer"
SCRIPTS = {
    "update_myfxbook.py": "63b7838f394253579f8a3ee67be7556c71c75367",
    "myfxbook_store.py": "e7a0977a02c7ec86f2d03d174a37e208491bd9f4",
}
PAGES = ("nav.js", "sw.js", "index.html", "forex.html", "mercati.html",
         "asset.html", "catalogo.html", "fonti.html", "impostazioni.html",
         "stato-prezzi.html", "statistica-squali.html")


def command(*parts, check=True):
    return subprocess.run(parts, check=check, capture_output=True, text=True, timeout=45)


def unit(action, name):
    return command("systemctl", action, name, check=False).stdout.strip()


def health():
    try:
        with urlopen("http://127.0.0.1:8765/private-api/health", timeout=5) as res:
            return res.status == 200
    except Exception:
        return False


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def blob_sha(data):
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def atomic_write(path, data, uid, gid, mode):
    require(not path.is_symlink(), "Destinazione symlink: " + path.name)
    fd, name = tempfile.mkstemp(prefix=".rm151-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as stream:
            os.fchown(stream.fileno(), uid, gid)
            os.fchmod(stream.fileno(), mode)
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
        dfd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dfd)
        finally:
            os.close(dfd)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def prepare():
    require(os.geteuid() == 0, "Root richiesto")
    require(unit("is-active", SERVICE) == "active" and health(), "Backend/API non sano")
    require(unit("is-active", OLD_TIMER) == "inactive" and
            unit("is-enabled", OLD_TIMER) == "disabled", "Sync vecchio non disabled")
    require(unit("is-active", "remura-autoupdate.service") != "active",
            "Autoupdate in esecuzione")
    require(BACKUP.is_dir() and STAGE.is_dir() and WEB.is_dir(), "Backup/staging mancante")
    manifest = json.loads((WEB / "manifest.json").read_text())
    require(set(manifest) == set(PAGES), "Manifest web incompleto")
    changes = {}
    for name in PAGES:
        live = APP / name
        require(live.is_file() and not live.is_symlink(), "Pagina mancante: " + name)
        meta = manifest[name]
        old = (WEB / "old" / name).read_bytes()
        new = (WEB / "new" / name).read_bytes()
        st = live.stat()
        require(digest(live.read_bytes()) == meta["old_sha256"] == digest(old),
                "Pagina cambiata da staging: " + name)
        require(digest(new) == meta["new_sha256"], "Nuova pagina alterata: " + name)
        require((st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) ==
                (meta["old_uid"], meta["old_gid"], meta["old_mode"]),
                "Permessi pagina cambiati: " + name)
        changes[live] = new
    require("Aggiornamento v1.51" in changes[APP / "nav.js"].decode(),
            "Banner v1.51 mancante")
    require("v1.51" in changes[APP / "sw.js"].decode(), "Cache v1.51 mancante")
    old_script = APP / "scripts/update_myfxbook.py"
    require(old_script.read_bytes() == (BACKUP / "script/update_myfxbook.py").read_bytes(),
            "Script vecchio non corrisponde al backup")
    for name, expected in SCRIPTS.items():
        new = (STAGE / name).read_bytes()
        require(blob_sha(new) == expected, "Codice GitHub non coincide: " + name)
        compile(new, name, "exec")
        live = APP / "scripts" / name
        require(not live.is_symlink(), "Symlink script imprevisto")
        changes[live] = new
    return changes


def live_collector_process():
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit() or int(proc.name) == os.getpid():
            continue
        try:
            cmd = (proc / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="ignore")
        except (OSError, PermissionError):
            continue
        if "/opt/remura/scripts/update_myfxbook.py" in cmd:
            return True
    return False


def restart_and_check():
    command("systemctl", "start", SERVICE, check=False)
    for _ in range(20):
        if unit("is-active", SERVICE) == "active" and health():
            return True
        time.sleep(2)
    return False


def deploy(changes):
    root = APP / "private/predeploy-backups"
    folder = Path(tempfile.mkdtemp(prefix="rollback-v151-", dir=root))
    originals = {}
    service_stopped = False
    success = False
    try:
        for dest in changes:
            require(not dest.is_symlink(), "File live symlink")
            st = dest.stat() if dest.exists() else None
            old = dest.read_bytes() if st is not None else None
            meta = (st.st_uid, st.st_gid, stat.S_IMODE(st.st_mode)) if st else None
            originals[dest] = (old, meta)
            if old is not None:
                save = folder / dest.relative_to(APP)
                save.parent.mkdir(parents=True, exist_ok=True)
                save.write_bytes(old)
                os.chmod(save, 0o600)
        print("BACKUP_RELEASE=" + str(folder), flush=True)
        command("systemctl", "stop", SERVICE)
        service_stopped = True
        require(unit("is-active", SERVICE) != "active", "Backend non fermo")
        require(not live_collector_process(), "Collector Myfxbook ancora in esecuzione")
        script_st = (APP / "scripts/update_myfxbook.py").stat()
        for dest, data in changes.items():
            old, meta = originals[dest]
            uid, gid, mode = meta if meta else (script_st.st_uid, script_st.st_gid, 0o644)
            atomic_write(dest, data, uid, gid, mode)
        require(restart_and_check(), "Health fallita dopo installazione")
        for dest, data in changes.items():
            require(dest.read_bytes() == data, "File installato differente")
        require(unit("is-active", OLD_TIMER) == "inactive" and
                unit("is-enabled", OLD_TIMER) == "disabled", "Timer vecchio cambiato")
        success = True
        print("ESITO=RELEASE_151_OK", flush=True)
        print("FILE_INSTALLATI=" + str(len(changes)), flush=True)
        print("BACKEND=ACTIVE", flush=True)
        print("API_HEALTH=HTTP_200", flush=True)
        print("COLLECTOR_LEGACY_TIMER=DISABLED", flush=True)
        print("STORICI_SQLITE_CREDENZIALI_NON_COPIATI=SI", flush=True)
    finally:
        if service_stopped and not success:
            command("systemctl", "stop", SERVICE, check=False)
            errors = []
            for dest, (old, meta) in originals.items():
                try:
                    if old is None:
                        dest.unlink(missing_ok=True)
                    else:
                        atomic_write(dest, old, *meta)
                except Exception as exc:
                    errors.append(dest.name + ":" + type(exc).__name__)
            restored = restart_and_check()
            print("ROLLBACK=" + ("OK" if not errors else "PARZIALE"), flush=True)
            print("HEALTH_POST_ROLLBACK=" + ("OK" if restored else "ERRORE"), flush=True)
            print("ERRORI_ROLLBACK=" + repr(errors), flush=True)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    require(args.check != args.apply, "Specificare --check oppure --apply")
    changes = prepare()
    print("PREFLIGHT=OK", flush=True)
    print("FILE_STAGING_VALIDATI=" + str(len(changes)), flush=True)
    if args.check:
        print("LIVE_NON_MODIFICATO=SI", flush=True)
        print("ESITO=PRONTO_PER_APPLICAZIONE", flush=True)
    else:
        deploy(changes)


if __name__ == "__main__":
    main()
