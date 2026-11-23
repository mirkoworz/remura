#!/usr/bin/env python3
"""REMURA V21.1 -- prospective RAW CVD pair -> deterministic side -> PRIVATE freeze.

This is a NEW, strictly defined, opt-in local input format, NOT a claim about
the existing TradingView payload or authenticated institutional order flow.
No live collector is implemented or activated. The 12 V20.3 aggregated
OBSERVATION_ONLY receipts CANNOT satisfy this raw schema and cannot be
converted into historical trading decisions.

Only a self-reported CVD-PROXY M5 difference is classified. Do not label this
as executed buy/sell lots. A hash and deterministic classifier do NOT attest
who generated the numbers or when the source was actually first received.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re

from v204_private_cvd_price_coverage import ms, read_local_price_db, utc
from v208_github_decision_witness import manifest_for
from v209_private_decision_freezer import (
    MAX_EVENT_AGE, REPOSITORY_ROOT, freeze_candidate, store_private_pair,
)
from v210_forward_integrity_gate import _row, adjudicate as old_adjudicate

UTC = timezone.utc
RAW_SCHEMA = "remura-v211-closed-m5-cvd-pair-v1"
RULE = "M5_CLOSED_CVD_DIFFERENCE_SIGN_ZERO_THRESHOLD_V1"
SOURCE_FAMILY = "UNVERIFIED_CVD_PROXY_NOT_EXECUTED_VOLUME"
RAW_FIELDS = frozenset((
    "schema", "symbol", "timeframe", "source_family",
    "prior_close_utc", "event_close_utc", "prior_cvd", "event_cvd",
))
MAX_RAW_BYTES = 64_000
FIXED_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]{0,11})(?:\.[0-9]{1,6})?")
MAX_CVD = Decimal("999999999999.999999")


def _pairs(items: list[tuple[str, object]]) -> dict:
    out = {}
    for key, value in items:
        if key in out:
            raise ValueError("duplicate_source_json_key")
        out[key] = value
    return out


def _decimal(value: object) -> Decimal:
    if type(value) is not str or FIXED_DECIMAL.fullmatch(value) is None:
        raise ValueError("noncanonical_fixed_decimal_cvd")
    number = Decimal(value)
    if abs(number) > MAX_CVD:
        raise ValueError("cvd_magnitude_limit")
    return number


def classify_raw(raw: bytes) -> tuple[str, str, str]:
    """Compute direction from TWO adjacent CLOSED-M5 CVD values, never from side."""
    if type(raw) is not bytes or not 1 <= len(raw) <= MAX_RAW_BYTES:
        raise ValueError("missing_or_oversize_original_source")
    try:
        doc = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs,
                         parse_constant=lambda _: (_ for _ in ()).throw(
                             ValueError("nonfinite_json_constant")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("not_valid_utf8_raw_cvd_json") from None
    if type(doc) is not dict or set(doc) != RAW_FIELDS:
        raise ValueError("unknown_original_source_contract")
    if (doc["schema"] != RAW_SCHEMA or doc["symbol"] != "FX:EURUSD" or
        doc["timeframe"] != "M5" or doc["source_family"] != SOURCE_FAMILY):
        raise ValueError("wrong_cvd_source_family_or_symbol")
    prev = utc(doc["prior_close_utc"])
    close = utc(doc["event_close_utc"])
    if (ms(prev) % 300_000 or ms(close) % 300_000 or
        close - prev != timedelta(minutes=5)):
        raise ValueError("cvd_pair_not_two_consecutive_closed_m5")
    left = _decimal(doc["prior_cvd"])
    right = _decimal(doc["event_cvd"])
    delta = right - left
    side = "LONG" if delta > 0 else "SHORT" if delta < 0 else "FLAT"
    return side, close.strftime("%Y-%m-%dT%H:%M:%SZ"), format(delta, "f")


def event_from_raw(raw: bytes, received_at_utc: str, *, as_of: datetime) -> dict:
    """Build a V20.9 event locally. Receipt timestamp is SELF-REPORTED."""
    if not isinstance(as_of, datetime) or as_of.tzinfo is None:
        raise ValueError("aware_now_required")
    side, close, _ = classify_raw(raw)
    event_time = utc(close)
    received = utc(received_at_utc)
    if not event_time <= received <= as_of.astimezone(UTC):
        raise ValueError("future_or_backdated_local_receipt")
    if as_of.astimezone(UTC) - event_time > MAX_EVENT_AGE:
        raise ValueError("cannot_backfill_old_cvd_source")
    return {
        "schema":"remura-v209-local-cvd-observation-v1",
        "symbol":"FX:EURUSD",
        "event_close_utc":close,
        "received_at_utc":received_at_utc,
        "source_event_sha256":hashlib.sha256(raw).hexdigest(),
        "cvd_side":side,
    }


def freeze_raw(raw: bytes, received_at_utc: str, market: dict, *,
               as_of: datetime, nonce: str | None = None) -> tuple[dict,dict]:
    """PRE-OUTCOME local freezer; never publishes decisions or calls GitHub."""
    event = event_from_raw(raw, received_at_utc, as_of=as_of)
    side, close, delta = classify_raw(raw)
    ledger, _ = freeze_candidate(event, market, as_of=as_of, nonce=nonce)
    row = ledger["decisions"][0]
    if row["cvd_side"] != side or row["event_close_utc"] != close:
        raise ValueError("inconsistent_source_classification")
    row["source_raw_schema"] = RAW_SCHEMA
    row["source_direction_rule"] = RULE
    row["source_self_reported_cvd_difference"] = delta
    row["source_origin_is_authenticated"] = False
    # Re-hash AFTER adding all provenance fields. Public file remains opaque.
    return ledger, manifest_for(row)


def adjudicate_raw(ledger: dict, manifest: dict, raw: bytes,
                   market: dict, *, as_of: datetime, github_readonly: bool = False,
                   costs: dict | None = None, fetch_json=None) -> dict:
    """Re-derive raw direction; fail BEFORE GitHub calls if inconsistent.

    The legacy V21.0 side flag intentionally remains FALSE: independent
    TradingView authentication is not achieved by this deterministic rule.
    """
    side, close, delta = classify_raw(raw)
    row = _row(ledger)
    if (row.get("source_raw_schema") != RAW_SCHEMA or
        row.get("source_direction_rule") != RULE or
        row.get("source_self_reported_cvd_difference") != delta or
        row.get("source_origin_is_authenticated") is not False or
        row.get("cvd_side") != side or row.get("event_close_utc") != close):
        raise ValueError("locked_direction_differs_from_raw_cvd_pair")
    # This will re-verify SHA256 of raw, locked price-only OHLC, and causality.
    result = old_adjudicate(
        ledger, manifest, raw, market, as_of=as_of,
        github_readonly=github_readonly, costs=costs, fetch_json=fetch_json,
    )
    result.update({
        "cvd_direction_deterministically_recomputed_from_raw_pair":True,
        "cvd_pair_is_self_reported_proxy_not_executed_volume":True,
        "raw_source_original_bytes_digest_matched":True,
        "cvd_origin_independently_authenticated":False,
        "raw_first_seen_timestamp_independently_authenticated":False,
        "institutional_trading_flow_claimed":False,
        "scientific_alpha_established":False,
    })
    return result


def _read_raw(path: Path) -> bytes:
    with path.open("rb") as stream:
        content = stream.read(MAX_RAW_BYTES+1)
    if not content or len(content) > MAX_RAW_BYTES:
        raise ValueError("raw_source_missing_or_too_large")
    return content


def main() -> None:
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--raw-source",type=Path,
                    help="RAW NEW v211 format, never 12 old aggregate receipts")
    ap.add_argument("--received-at-utc",type=str,
                    help="Locally asserted actual reception time; NOT authenticated")
    ap.add_argument("--private-sqlite",type=Path,
                    help="Existing PRIVATE cTrader M15 DB, strict read-only")
    ap.add_argument("--private-dir",type=Path,
                    help="Private 0700 directory outside public Git checkout")
    ap.add_argument("--write-private",action="store_true",
                    help="Explicitly create two private files, no GitHub push")
    args=ap.parse_args()
    if not any((args.raw_source,args.received_at_utc,args.private_sqlite,
                args.private_dir,args.write_private)):
        print(json.dumps({
            "status":"NO_ORIGINAL_CVD_SOURCE_NO_DECISION",
            "signal_count":0,
            "trades_or_alerts_activated":False,
            "network_or_market_provider_calls":0,
        },sort_keys=True))
        return
    if not all((args.raw_source,args.received_at_utc,args.private_sqlite,args.private_dir)):
        ap.error("All four PRIVATE inputs are mandatory; no file written")
    try:
        source = args.raw_source.expanduser().resolve(strict=True)
        if source == REPOSITORY_ROOT or REPOSITORY_ROOT in source.parents:
            raise ValueError("source_must_remain_outside_public_repo")
        raw = _read_raw(source)
        prices = read_local_price_db(args.private_sqlite)
        ledger, manifest = freeze_raw(
            raw, args.received_at_utc, prices, as_of=datetime.now(UTC)
        )
        if args.write_private:
            status = store_private_pair(ledger,manifest,args.private_dir)
            status["cvd_direction_deterministically_derived_from_raw"] = True
            status["cvd_origin_independently_authenticated"] = False
        else:
            status = {
                "status":"LOCAL_CANDIDATE_NOT_SAVED",
                "files_written":0,
                "github_witness_verified":False,
                "cvd_direction_deterministically_derived_from_raw":True,
                "cvd_origin_independently_authenticated":False,
                "trades_or_alerts_activated":False,
            }
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError):
        ap.error("Reject: raw M5 CVD pair/causality/price invalid; sensitive detail withheld")
    print(json.dumps(status,ensure_ascii=False,indent=2,sort_keys=True))


if __name__=="__main__":
    main()
