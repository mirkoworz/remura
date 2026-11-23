#!/usr/bin/env python3
"""REMURA V20.9 -- PRIVATE forward-only CVD decision freezer + frozen price-only baseline.

No network, API calls, orders, alerts, Git push, or production writes.
Read-only cTrader M15 existing SQLite is optional ONLY when explicitly requested
by the operator. The result is private, never suitable for public GitHub upload.
Public hash-only manifest can be manually published later after review.

A local event timestamp and broker timestamp are NOT authenticated by this tool.
V20.8 later verifies ONLY that the hash was seen on GitHub, not the source feed.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import stat

from v204_private_cvd_price_coverage import checked_m15, ms, read_local_price_db, utc, M15_MS
from v207_forward_cvd_evaluation import SCHEMA as LEDGER_SCHEMA, SIDES
from v208_github_decision_witness import manifest_for

UTC = timezone.utc
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
EVENT_SCHEMA = "remura-v209-local-cvd-observation-v1"
BASELINE_RULE = "M15_FIVE_CLOSED_CONTIGUOUS_CLOSE_MOMENTUM_SIGN_V1"
MAX_EVENT_AGE = timedelta(minutes=12)
MAX_PRICE_AGE = timedelta(minutes=20)
HEX64 = re.compile(r"[0-9a-f]{64}")


def _timestamp(value: datetime) -> str:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ValueError("aware_time_required")
    return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _validated_event(event: dict, as_of: datetime) -> tuple[str, str, datetime]:
    if type(event) is not dict or set(event) != {
        "schema", "symbol", "event_close_utc", "received_at_utc",
        "source_event_sha256", "cvd_side"
    }:
        raise ValueError("invalid_local_event_schema")
    if event["schema"] != EVENT_SCHEMA or event["symbol"] != "FX:EURUSD":
        raise ValueError("only_explicit_fx_eurusd_event")
    digest = event["source_event_sha256"]
    if type(digest) is not str or HEX64.fullmatch(digest) is None:
        raise ValueError("source_digest_required")
    side = event["cvd_side"]
    if type(side) is not str or side not in SIDES:
        raise ValueError("side_must_be_explicit")
    close = utc(event["event_close_utc"])
    received = utc(event["received_at_utc"])
    if ms(close) % (5 * 60_000):
        raise ValueError("unaligned_m5_event_close")
    if not close <= received <= as_of:
        raise ValueError("future_or_backdated_receipt")
    if as_of - close > MAX_EVENT_AGE:
        raise ValueError("stale_event_rejected")
    # Timestamp is a local declaration; this does not certify TV/CVD authenticity.
    return digest, side, close


def freeze_candidate(event: dict, market: dict, *, as_of: datetime, nonce: str | None = None) -> tuple[dict, dict]:
    """Build a PRIVATE decision & PUBLIC hash-only manifest without writing files.

    Uses the five LAST M15 closed before as_of; both CVD and price-only
    decisions are locked at the same instant. Never calculate from future OHLC.
    """
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError("aware_time_required")
    as_of = as_of.astimezone(UTC).replace(microsecond=0)
    digest, side, close = _validated_event(event, as_of)
    # checked_m15 validates provider, symbol, strict UTC ordering, OHLC, closed bars.
    closed = checked_m15(market, as_of)
    samples = sorted(closed.items())[-5:]
    if len(samples) != 5:
        raise ValueError("five_closed_m15_bars_required")
    stamps = [t for t, _ in samples]
    if any(b-a != M15_MS for a, b in zip(stamps, stamps[1:])):
        raise ValueError("m15_gap_rejected")
    if ms(as_of) - (stamps[-1] + M15_MS) > int(MAX_PRICE_AGE.total_seconds() * 1000):
        raise ValueError("stale_m15_price_rejected")
    # Timestamp of most recently closed price bar MUST NOT be in the future.
    if stamps[-1] + M15_MS > ms(as_of):
        raise ValueError("unclosed_m15_rejected")
    first_close = samples[0][1]["c"]
    last_close = samples[-1][1]["c"]
    baseline = "LONG" if last_close > first_close else "SHORT" if last_close < first_close else "FLAT"
    if nonce is None:
        nonce = secrets.token_hex(16)
    if type(nonce) is not str or re.fullmatch(r"[0-9a-f]{32,64}", nonce) is None:
        raise ValueError("nonce_must_be_secret_random_hex")
    identity = "cvd_" + hashlib.sha256(
        (event["event_close_utc"] + "|" + digest).encode("utf-8")
    ).hexdigest()[:32]
    rows = [
        {k: b[k] for k in ("t", "o", "h", "l", "c")}
        for _, b in samples
    ]
    row = {
        "decision_id": identity,
        "event_close_utc": _timestamp(close),
        "received_at_utc": event["received_at_utc"],
        "recorded_at_utc": _timestamp(as_of),
        "frozen_at_utc": _timestamp(as_of),
        "price_only_known_at_utc": _timestamp(as_of),
        "cvd_side": side,
        "price_only_side": baseline,
        "observations_count": 1,
        "decision_nonce": nonce,
        "source_event_sha256": digest,
        "cvd_source_authentication": "LOCAL_ASSERTION_UNVERIFIED",
        "price_feed_authentication": "LOCAL_CTRADER_SQLITE_UNVERIFIED",
        "price_only_rule": BASELINE_RULE,
        "price_only_input_m15": rows,
        "anchor": {
            "kind": "github_commit",
            "workflow_run_id": 0,  # Must be filled PRIVATELY after real V20.8 push run.
        },
    }
    ledger = {
        "schema": LEDGER_SCHEMA,
        "symbol": "EURUSD",
        "signal_family": "CVD_PROXY_M5",
        "decisions": [row],
    }
    manifest = manifest_for(row)
    return ledger, manifest


def _json_bytes(doc: dict) -> bytes:
    return (json.dumps(doc, ensure_ascii=False, indent=2, sort_keys=True,
                       allow_nan=False) + "\n").encode("utf-8")


def _safely_create(path: Path, content: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
    except BaseException:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        raise


def store_private_pair(ledger: dict, manifest: dict, private_dir: Path) -> dict:
    """Create files outside the public Git checkout; 0600, exclusive, no overwrite."""
    folder = private_dir.expanduser().resolve()
    if folder == REPOSITORY_ROOT or REPOSITORY_ROOT in folder.parents:
        raise ValueError("private_directory_must_be_outside_public_repository")
    if folder.exists() and (not folder.is_dir() or folder.is_symlink()):
        raise ValueError("private_directory_must_be_real_directory")
    folder.mkdir(parents=True, mode=0o700, exist_ok=True)
    if stat.S_IMODE(folder.stat().st_mode) & 0o077:
        raise ValueError("private_directory_permissions_too_open")
    if set(ledger) != {"schema", "symbol", "signal_family", "decisions"}:
        raise ValueError("bad_private_ledger")
    row = ledger["decisions"][0]
    identity = row["decision_id"]
    if type(identity) is not str or re.fullmatch(r"cvd_[a-f0-9]{32}", identity) is None:
        raise ValueError("invalid_private_filename")
    if manifest != manifest_for(row):
        raise ValueError("mismatched_public_manifest")
    local_path = folder / f"{identity}.private.json"
    hash_path = folder / f"{identity}.hash-only.json"
    if local_path.exists() or hash_path.exists():
        raise ValueError("decision_already_frozen_no_overwrite")
    _safely_create(local_path, _json_bytes(ledger))
    try:
        _safely_create(hash_path, _json_bytes(manifest))
    except BaseException:
        local_path.unlink(missing_ok=True)
        raise
    # Deliberately do not print paths, nonce, ticker/broker, rows or decisions.
    return {
        "schema": "remura-v209-freeze-local-report-v1",
        "status": "PRIVATE_LEDGER_AND_HASH_ONLY_MANIFEST_CREATED",
        "private_ledger_committed_to_github": False,
        "public_manifest_uploaded": False,
        "github_witness_verified": False,
        "cvd_source_authenticity_verified": False,
        "broker_price_authenticity_verified": False,
        "entry_or_profit_assessed": False,
        "files_created": 2,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cvd-event-file", type=Path,
                   help="Local event assertion, must be captured promptly, NOT historical reconstruction")
    p.add_argument("--private-sqlite", type=Path,
                   help="Existing cTrader M15 SQLite read-only; no collector changes")
    p.add_argument("--private-dir", type=Path,
                   help="Restricted 0700 directory OUTSIDE public repo")
    p.add_argument("--write-private", action="store_true",
                   help="Opt in to create TWO local files 0600, no GitHub uploads")
    args = p.parse_args()
    if not any((args.cvd_event_file,args.private_sqlite,args.private_dir,args.write_private)):
        print(json.dumps({
            "status": "NO_INPUT_NO_OUTPUT",
            "future_decisions_frozen": 0,
            "public_push_or_provider_calls": 0,
        }, sort_keys=True))
        return
    if not (args.cvd_event_file and args.private_sqlite and args.private_dir):
        p.error("Full local input, DB and private directory required; no file created")
    try:
        event = json.loads(args.cvd_event_file.read_text(encoding="utf-8"))
        market = read_local_price_db(args.private_sqlite)
        candidate, hash_only = freeze_candidate(event, market, as_of=datetime.now(UTC))
        if args.write_private:
            report = store_private_pair(candidate, hash_only, args.private_dir)
        else:
            report = {
                "status":"READY_ONLY_NOT_SAVED",
                "private_files_created": 0,
                "public_manifest_uploaded": False,
                "github_witness_verified": False,
                "cvd_source_authenticity_verified": False,
                "future_price_outcome_calculated": False,
            }
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        p.error("Private input or causal precommit gate rejected; sensitive details withheld")
    print(json.dumps(report, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
