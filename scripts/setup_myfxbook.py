#!/usr/bin/env python3
"""Enable private Myfxbook collection via a local, non-echoing terminal prompt.

Only edits the existing ignored/private systemd EnvironmentFile on the VPS.
Never print, log, commit or pass the Myfxbook credentials on a command line.
Does not alter cTrader, broker tokens, symbol selections or price history.
"""
from __future__ import annotations

import getpass
import os
from pathlib import Path
import stat
import sys
import tempfile

ENV_FILE = Path("/opt/remura/private/remura.env")
RETAIL_KEYS = frozenset({"REMURA_RETAIL_ENABLED", "MYFXBOOK_EMAIL", "MYFXBOOK_PASSWORD"})


def quote_systemd(value: str) -> str:
    """Quote a single-line EnvironmentFile value using systemd double-quote rules."""
    if not isinstance(value, str) or not value or len(value) > 1024:
        raise ValueError("Valore non valido.")
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("I dati devono essere su una sola riga, senza caratteri di controllo.")
    return '"' + "".join("\\" + ch if ch in '\\"$`' else ch for ch in value) + '"'


def updated_environment(original: str, email: str, password: str) -> str:
    if not isinstance(email, str) or len(email) > 254 or email.count("@") != 1 or any(ch.isspace() for ch in email):
        raise ValueError("Indirizzo email non valido.")
    email_line = "MYFXBOOK_EMAIL=" + quote_systemd(email)
    password_line = "MYFXBOOK_PASSWORD=" + quote_systemd(password)
    kept = []
    for line in original.splitlines(keepends=True):
        field = line.split("=", 1)[0].strip() if "=" in line and not line.lstrip().startswith(("#", ";")) else ""
        if field not in RETAIL_KEYS:
            kept.append(line)
    if kept and not kept[-1].endswith("\n"):
        kept.append("\n")
    return "".join(kept) + "REMURA_RETAIL_ENABLED=1\n" + email_line + "\n" + password_line + "\n"


def save_private_credentials(path: Path, email: str, password: str) -> None:
    path = Path(path)
    if path.is_symlink() or not path.is_file():
        raise RuntimeError("File di configurazione privata non valido.")
    file_info = path.stat()
    if file_info.st_uid != os.geteuid() or not stat.S_ISREG(file_info.st_mode):
        raise RuntimeError("Esegui con l'utente remura, non root.")
    if file_info.st_mode & 0o077:
        raise RuntimeError("Permessi del file non riservati: richiede chmod 600.")
    original = path.read_text("utf-8")
    replacement = updated_environment(original, email, password)
    fd, temp_name = tempfile.mkstemp(prefix=".remura-myfxbook-", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            os.fchmod(file.fileno(), 0o600)
            file.write(replacement)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def main() -> int:
    if not sys.stdin.isatty():
        print("Serve un terminale interattivo (Termius). Nessuna modifica effettuata.")
        return 1
    print("Configurazione Myfxbook PRIVATA per REMURA.")
    print("Email e password non verranno visualizzate. Non incollarle in chat.")
    try:
        email = getpass.getpass("Email Myfxbook (nascosta): ").strip()
        password = getpass.getpass("Password Myfxbook (nascosta): ")
        save_private_credentials(ENV_FILE, email, password)
    except (EOFError, KeyboardInterrupt, OSError, ValueError, RuntimeError):
        print("\nConfigurazione non completata. Nessun dato delle credenziali visualizzato.")
        return 1
    print("MYFXBOOK CONFIGURATO: SI. Riavvia remura-private per attivare la raccolta.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
