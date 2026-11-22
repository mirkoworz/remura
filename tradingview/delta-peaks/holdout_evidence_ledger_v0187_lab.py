# REMURA TradingView v0.8.187 LAB - 22 Nov 2026 Europe/Rome.
"""OFFLINE-only prospective evidence inventory; no provider/TradingView capture.

Frozen protocol V2 is read and pinned, never edited. A claimed receipt, SHA,
witness reference or positive test is NEVER sufficient proof of a true
independently anchored first-seen. No backfill, price/CVD outcome analysis,
per-trade alpha, tuning, deployment, Oracle, provider calls or Secrets.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import re

from holdout_freeze_v0182_lab import guard, phase

ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
HEX = re.compile(r"^[a-f0-9]{64}$")
ID = re.compile(r"^[A-Z0-9_.:-]{1,80}$")
FIELDS=frozenset(("decision_id","bar_close_utc","receipt_utc",
    "source","timeframe","source_sha256","price_only_comparator_id",
    "external_witness_reference"))
SCHEMA="remura.tv.holdout_evidence_ledger.v0187.lab"

class AdmissionError(ValueError):
    pass

def instant(value):
    if type(value) is not str or not ISO.fullmatch(value):
        raise AdmissionError("noncanonical_utc_timestamp")
    try:
        stamp=datetime.fromisoformat(value.replace("Z","+00:00"))
    except ValueError as exc:
        raise AdmissionError("noncanonical_utc_timestamp") from exc
    if stamp.strftime("%Y-%m-%dT%H:%M:%SZ")!=value:
        raise AdmissionError("noncanonical_utc_timestamp")
    return stamp

def classify(entry):
    if type(entry) is not dict or set(entry)!=FIELDS:
        return "INVALID_RECORD"
    if type(entry["decision_id"]) is not str or not ID.fullmatch(entry["decision_id"]):
        return "INVALID_RECORD"
    if type(entry["price_only_comparator_id"]) is not str or not ID.fullmatch(entry["price_only_comparator_id"]):
        return "MISSING_PRICE_ONLY_COMPARATOR"
    try:
        close=instant(entry["bar_close_utc"])
    except AdmissionError:
        return "INVALID_RECORD"
    if phase(close) not in ("HOLDOUT_1","HOLDOUT_2"):
        return "OUTSIDE_HOLDOUT"
    if (close.minute%5!=0 or close.second!=0 or
            entry["source"]!="TRADINGVIEW_CVD" or entry["timeframe"]!="M5"):
        return "INCOMPARABLE_SOURCE_OR_BAR"
    receipt=entry["receipt_utc"]
    if receipt is None: return "UNKNOWN_RECEIPT"
    try:
        seen=instant(receipt)
    except AdmissionError:
        return "INVALID_RECORD"
    delta=(seen-close).total_seconds()
    if delta<0: return "CLOCK_CONFLICT"
    if delta>120 or delta>=300: return "LATE_UNADMITTED"
    digest=entry["source_sha256"]
    if type(digest) is not str or not HEX.fullmatch(digest):
        return "NO_CONTENT_IDENTITY"
    witness=entry["external_witness_reference"]
    if witness is None: return "NO_INDEPENDENT_WITNESS"
    if type(witness) is not str or not 1<=len(witness)<=180:
        return "UNVERIFIED_WITNESS_CLAIM"
    # A reference is a claim; this module has no access to its independent verifier.
    return "ON_TIME_CLAIM_NOT_INDEPENDENTLY_VERIFIED"

def review(entries, *, protocol_path=None):
    """Returns aggregate, bounded, per-fold accounting; no user IDs exposed."""
    if type(entries) not in (list,tuple) or len(entries)>5000:
        raise AdmissionError("invalid_or_oversized_batch")
    # Reject protocol drift before inspecting individual candidate metadata.
    if protocol_path is None:
        protocol=guard()
    else:
        protocol=guard(protocol_path)
    if protocol["protocol"]!="CVD_PROSPECTIVE_V2_PINNED":
        raise AdmissionError("protocol_not_pinned")
    labels=Counter()
    folds=Counter()
    identities=set()
    conflicts=set()
    results=[]
    for item in entries:
        label=classify(item)
        fold="INVALID"
        if type(item) is dict and type(item.get("bar_close_utc")) is str:
            try:
                fold=phase(instant(item["bar_close_utc"]))
            except AdmissionError:
                pass
        identity=None
        if type(item) is dict and type(item.get("decision_id")) is str:
            identity=item["decision_id"]
        if identity is not None:
            if identity in identities: conflicts.add(identity)
            identities.add(identity)
        results.append((identity,label,fold))
    for identity,label,fold in results:
        # Duplicates are never FIFO-repaired or replaced by later payloads.
        if identity in conflicts: label="DUPLICATE_DECISION_QUARANTINE"
        labels[label]+=1
        folds[fold]+=1
    return {
        "schema":SCHEMA,
        "protocol":"V2_PINNED_UNMODIFIED",
        "status":"NO_GO_REAL_HOLDOUT_ADMISSION",
        "submitted_records":len(entries),
        "record_classes":dict(sorted(labels.items())),
        "record_fold_counts":dict(sorted(folds.items())),
        "submitted_records_are_not_required_market_hours":True,
        "real_cvds_authenticated":False,
        "independent_time_anchor_verified":False,
        "m5_market_coverage_verified":False,
        "scientific_admission":False,
        "holdout_outcomes_measured":False,
        "statistical_alpha_proven":False,
        "no_backfill":True,
        "no_protocol_changes":True,
        "provider_calls":0,
        "live_deployment":False,
    }
