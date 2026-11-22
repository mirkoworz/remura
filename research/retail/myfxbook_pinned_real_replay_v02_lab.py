#!/usr/bin/env python3
# REMURA retail real-file as-of replay v0.2 LAB - 22 Nov 2026 Europe/Rome.
"""Read only a pinned, actual repository Myfxbook archive. NEVER infer
external first-seen or ability to trade when t <= decision. No APIs, secrets,
COT mapping, Oracle, or signal generation. This is a narrow *new* empirical
replay, NOT a rerun of the broad 34-file history audit.
"""
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha1, sha256
from pathlib import Path
import json
import math
import re

SCHEMA = "remura.retail.pinned_real_replay.v02.lab"
SOURCE = "Myfxbook Community Outlook"
PINNED_SYMBOL = "EURUSD"
PINNED_BLOB_SHA1 = "8e0ca3c9bae596c0d5145d1e9e6994cf6a39e5a9"
PINNED_LATEST_SHA1 = "c2c4dfc6546fa26e315400995132fc60170cede1"
UTC_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
FIELDS = ("t","lPct","sPct","lLots","sLots","lPos","sPos","avgL","avgS")
ROOT = Path(__file__).resolve().parents[2] / "data" / "myfxbook"

class ReplayError(ValueError):
    pass

def utc(value):
    if type(value) is not str or not UTC_RE.fullmatch(value):
        raise ReplayError("timestamp_not_canonical_utc")
    try:
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise ReplayError("timestamp_not_canonical_utc") from exc
    if stamp.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ReplayError("timestamp_not_canonical_utc")
    return stamp

def unique(pairs):
    result={}
    for k,v in pairs:
        if k in result: raise ReplayError("duplicate_json_field")
        result[k]=v
    return result

def pinned_json(path, expected_sha, max_bytes):
    if not isinstance(path,Path) or path.is_symlink() or not path.is_file():
        raise ReplayError("archive_unavailable")
    if path.stat().st_size>max_bytes:
        raise ReplayError("archive_oversized")
    payload=path.read_bytes()
    sha=sha1(b"blob "+str(len(payload)).encode("ascii")+b"\0"+payload).hexdigest()
    if sha != expected_sha:
        raise ReplayError("pinned_git_blob_changed")
    try:
        return json.loads(payload.decode("utf-8"),object_pairs_hook=unique),sha256(payload).hexdigest()
    except (UnicodeError,ValueError) as exc:
        raise ReplayError("invalid_json_archive") from exc

def valid_row(row):
    if type(row) is not dict or set(row)!=set(FIELDS):
        raise ReplayError("invalid_myfxbook_row_schema")
    t=utc(row["t"])
    for field in FIELDS[1:]:
        n=row[field]
        if n is None and field in ("avgL","avgS"):
            continue
        if type(n) not in (int,float) or not math.isfinite(n) or n<0 or n>1e12:
            raise ReplayError("invalid_numeric_value")
    if row["lPct"]>100 or row["sPct"]>100:
        raise ReplayError("invalid_percentage")
    return t

def replay(*, decision_utc, archive_root=ROOT):
    at=utc(decision_utc)
    if not isinstance(archive_root,Path) or archive_root.is_symlink():
        raise ReplayError("invalid_root")
    history, file_sha256 = pinned_json(
        archive_root/"history"/"EURUSD.json",PINNED_BLOB_SHA1,100_000)
    latest, latest_sha256 = pinned_json(
        archive_root/"latest.json",PINNED_LATEST_SHA1,500_000)
    if type(history) is not dict or set(history)!={"symbol","source","sampling","records"}:
        raise ReplayError("invalid_history_schema")
    if history["symbol"] != PINNED_SYMBOL or history["source"]!=SOURCE:
        raise ReplayError("source_or_symbol_mismatch")
    if history["sampling"] != "observed at recorded timestamps (not guaranteed 20m)":
        raise ReplayError("sampling_unsupported")
    rows=history["records"]
    if type(rows) is not list or not 1<=len(rows)<=3000:
        raise ReplayError("bounded_series_missing")
    if type(latest) is not dict or set(latest)!={"status","source","updatedAt","symbols"}:
        raise ReplayError("latest_invalid")
    if latest["status"]!="ok" or latest["source"]!=SOURCE or type(latest["symbols"]) is not dict:
        raise ReplayError("latest_invalid")
    latest_at=utc(latest["updatedAt"])
    latest_row=latest["symbols"].get(PINNED_SYMBOL)
    if latest_row is None or valid_row(latest_row)!=latest_at:
        raise ReplayError("latest_eurusd_invalid")
    last=None
    chosen=None
    for row in rows:
        t=valid_row(row)
        if last is not None and t<=last:
            raise ReplayError("nonmonotonic_history")
        if t>latest_at:
            raise ReplayError("history_after_latest")
        if t<=at:
            chosen=dict(row)
        last=t
    if last != latest_at or rows[-1] != latest_row:
        raise ReplayError("pinned_latest_history_mismatch")
    return {
        "schema":SCHEMA,
        "status":"REPOSITORY_REPLAY_UNATTESTED" if chosen else "UNKNOWN_NO_PRIOR_REPOSITORY_RECORD",
        "decision_utc":decision_utc,
        "symbol":PINNED_SYMBOL,
        "record":chosen,  # Real published repository data, no live provider call
        "archive_git_blob_sha1":PINNED_BLOB_SHA1,
        "archive_file_sha256":file_sha256,
        "latest_file_sha256":latest_sha256,
        "snapshot_latest_utc":latest["updatedAt"],
        "recorded_time_is_independent_first_seen":False,
        "provider_publication_time_verified":False,
        "source_available_at_decision_verified":False,
        "spot_futures_mapping_verified":False,
        "institutional_exposure_established":False,
        "tradingview_holdout_scientific_admission":False,
        "alpha_established":False,
        "external_calls":0,
        "data_mutated":False,
    }
