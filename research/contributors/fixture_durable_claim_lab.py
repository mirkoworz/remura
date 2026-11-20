# REMURA Contributors v0.54 LAB — 20/11/2026 CET
"""Synthetic local durable one-shot claim. No provider entry point."""
import os
import stat
from pathlib import Path

MARKER = "fixture-session-consumed-v1"
RECORD = b"REMURA SYNTHETIC SESSION CONSUMED V1\n"

def claim(directory):
    """Consume once before opening a synthetic session; never reset automatically."""
    directory = Path(directory)
    if not directory.is_absolute() or directory.resolve(strict=True) != directory:
        raise RuntimeError("fixture_claim_denied")
    dfd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        st = os.fstat(dfd)
        if not stat.S_ISDIR(st.st_mode) or st.st_uid != os.geteuid() or stat.S_IMODE(st.st_mode) != 0o700:
            raise RuntimeError("fixture_claim_denied")
        fd = os.open(MARKER, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600, dir_fd=dfd)
        try:
            os.fchmod(fd, 0o600)
            if os.write(fd, RECORD) != len(RECORD):
                raise RuntimeError("fixture_claim_incomplete")
            os.fsync(fd)
        finally:
            os.close(fd)
        os.fsync(dfd)
    finally:
        os.close(dfd)
    return {"status": "SYNTHETIC_LOCAL_CLAIM_CONSUMED", "provider_called": False, "authorization_granted": False}
