# REMURA TradingView v0.8.182 LAB — 21/11/2026 Europe/Rome
# Immutable holdout calendar preflight. NO market input, outcome analysis or capture.
"""Guard preregistered prospective V2 dates; never reinterpret old outcomes."""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha1
from pathlib import Path
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
PROTOCOL = ROOT / "tradingview/delta-peaks/CVD-PROSPECTIVE-PROTOCOL-V2.md"
PINNED_PROTOCOL_GIT_BLOB = "4b0f5d5defacfdbf8e902af5a8eea32947cabeca"

def utc(iso: str) -> datetime:
    return datetime.fromisoformat(iso.replace("Z", "+00:00"))

DEV_START = utc("2026-11-16T00:00:00Z")
H1_START = utc("2026-11-23T00:00:00Z")
H2_START = utc("2026-11-30T00:00:00Z")
H2_END = utc("2026-12-07T00:00:00Z")

class FreezeError(ValueError):
    pass

def git_blob_hash(payload: bytes) -> str:
    return sha1(b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload).hexdigest()

def phase(timestamp: datetime) -> str:
    if not isinstance(timestamp, datetime) or timestamp.tzinfo is None or timestamp.utcoffset() != timezone.utc.utcoffset(None):
        raise FreezeError("utc_timestamp_required")
    stamp = timestamp.astimezone(timezone.utc)
    if DEV_START <= stamp < H1_START:
        return "DEVELOPMENT_FROZEN"
    if H1_START <= stamp < H2_START:
        return "HOLDOUT_1"
    if H2_START <= stamp < H2_END:
        return "HOLDOUT_2"
    return "OUTSIDE_RESERVED_WINDOWS"

def guard(path: Path = PROTOCOL) -> dict[str, object]:
    if not isinstance(path, Path) or path.is_symlink() or not path.is_file():
        raise FreezeError("protocol_missing_or_symlink")
    payload = path.read_bytes()
    if not payload or len(payload) > 20_000 or git_blob_hash(payload) != PINNED_PROTOCOL_GIT_BLOB:
        raise FreezeError("protocol_changed")
    if not (DEV_START < H1_START < H2_START < H2_END):
        raise FreezeError("windows_overlap")
    text = payload.decode("utf-8")
    for needle in (
        "Development: 16–22 novembre UTC",
        "primo holdout: 23–29 novembre",
        "replica: 30 novembre–6 dicembre",
        "Primario: CVD vs price-only a 60 minuti",
        "Niente matching tra fold",
        "nessun registro live indipendente",
    ):
        if needle not in text:
            raise FreezeError("preregistration_condition_missing")
    return {
        "schema": "remura.tradingview.holdout_freeze.v0182.lab",
        "version": "0.8.182",
        "protocol": "CVD_PROSPECTIVE_V2_PINNED",
        "development_utc": ["2026-11-16T00:00:00Z", "2026-11-23T00:00:00Z"],
        "holdout_1_utc": ["2026-11-23T00:00:00Z", "2026-11-30T00:00:00Z"],
        "holdout_2_utc": ["2026-11-30T00:00:00Z", "2026-12-07T00:00:00Z"],
        "interval_end_exclusive": True,
        "primary": "CVD_VS_PRICE_ONLY_60_MINUTES",
        "outcomes_measured": False,
        "institutional_edge_established": False,
        "captures_active": False,
        "holdout_protocol_modified": False,
        "release_deploy_allowed": False,
        "decision": "LAB_CALENDAR_REVIEW_ONLY",
    }

def main(argv: list[str]) -> int:
    if argv != ["--check"]:
        print("REMURA_V0182_HOLDOUT=BAD_ARGUMENTS")
        return 2
    try:
        print(json.dumps(guard(), sort_keys=True, separators=(",", ":")))
    except (FreezeError, UnicodeError, OSError):
        print("REMURA_V0182_HOLDOUT=NO_GO_PROTOCOL_DRIFT")
        return 3
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
