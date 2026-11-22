# REMURA TradingView v0.8.188 LAB — 22 Nov 2026 Europe/Rome.
"""Cross-source scientific admission firewall, OFFLINE and research only.

This examines whether a single prospective TradingView decision *could*
be considered; it never produces buy/sell alerts, scores, PnL, alpha claims,
or deployment actions. Self-supplied 'verified' booleans / URLs / Git hashes
cannot constitute independent timestamp, market mapping or coverage proofs.
Missing data is UNKNOWN, not a flat market or a bearish/bullish signal.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import re

from holdout_evidence_ledger_v0187_lab import classify, AdmissionError, instant
from holdout_freeze_v0182_lab import guard, phase

IDENT = re.compile(r"^[A-Z0-9_.:-]{1,80}$")
SCHEMA="remura.tv.scientific_admission_firewall.v0188.lab"
ALLOWED_SOURCE_STATES=frozenset((
    "UNKNOWN_NOT_AVAILABLE","UNKNOWN","REPOSITORY_REPLAY_UNATTESTED",
    "LOCAL_OBSERVED_UNATTESTED","LOCAL_VERSION_UNATTESTED",
    "LOCAL_PAIR_UNATTESTED_FIXTURE_ONLY","EXTERNAL_PLATFORM_RUN_ASSOCIATION_UNATTESTED_OFFLINE",
))

def _source(value):
    if value is None:
        return "UNKNOWN"
    if type(value) is not dict or type(value.get("status")) is not str:
        return "INVALID"
    return value["status"] if value["status"] in ALLOWED_SOURCE_STATES else "INVALID"

def review_decision(*, decision_id, decision_utc, cvd_candidate=None,
                    retail_evidence=None, cot_evidence=None,
                    mapping_claim=None, required_m5_bars=None,
                    observed_m5_bars=None):
    # The protocol's original blob hash must still match preregistered V2.
    guard()
    if type(decision_id) is not str or not IDENT.fullmatch(decision_id):
        raise AdmissionError("missing_or_invalid_decision_id")
    at=instant(decision_utc)
    fold=phase(at)
    blocks=set()
    if fold not in ("HOLDOUT_1","HOLDOUT_2"):
        blocks.add("OUTSIDE_PREREGISTERED_HOLDOUT")
    if type(cvd_candidate) is not dict:
        blocks.add("M5_CVD_NOT_PRESENT")
        cvd_class="UNKNOWN"
    else:
        cvd_class=classify(cvd_candidate)
        if cvd_candidate.get("decision_id")!=decision_id:
            blocks.add("DECISION_LINK_NOT_EXACT")
        try:
            closed=instant(cvd_candidate.get("bar_close_utc"))
            received=instant(cvd_candidate.get("receipt_utc"))
        except AdmissionError:
            closed=received=None
        if closed is None or closed>at:
            blocks.add("CVD_BAR_NOT_CLOSED_BY_DECISION")
        if received is None or received>at:
            blocks.add("CVD_RECEIPT_NOT_AVAILABLE_BY_DECISION")
        if cvd_class!="ON_TIME_CLAIM_NOT_INDEPENDENTLY_VERIFIED":
            blocks.add("M5_CVD_NOT_ON_TIME_COMPARABLE")
        else:
            blocks.add("M5_CVD_TIME_INDEPENDENTLY_UNVERIFIED")
    left=_source(retail_evidence)
    right=_source(cot_evidence)
    if left in ("UNKNOWN","UNKNOWN_NOT_AVAILABLE"):
        blocks.add("RETAIL_HISTORICAL_VALUE_MISSING")
    elif left=="INVALID":
        blocks.add("RETAIL_EVIDENCE_INVALID_OR_UNSUPPORTED")
    else:
        blocks.add("RETAIL_SOURCE_RECEIPT_NOT_INDEPENDENTLY_VERIFIED")
    if right in ("UNKNOWN","UNKNOWN_NOT_AVAILABLE"):
        blocks.add("COT_HISTORICAL_REVISION_MISSING")
    elif right=="INVALID":
        blocks.add("COT_EVIDENCE_INVALID_OR_UNSUPPORTED")
    else:
        blocks.add("COT_SOURCE_RECEIPT_NOT_INDEPENDENTLY_VERIFIED")

    if mapping_claim is None or mapping_claim=="":
        blocks.add("SPOT_FUTURES_MAPPING_MISSING")
    elif type(mapping_claim) is not str or len(mapping_claim)>160:
        blocks.add("SPOT_FUTURES_MAPPING_INVALID")
    else:
        # A declared mapping name is not an independently inspected mapping.
        blocks.add("SPOT_FUTURES_MAPPING_UNVERIFIED")

    if (type(required_m5_bars) is not int or required_m5_bars<1 or
        type(observed_m5_bars) is not int or
        observed_m5_bars<0 or observed_m5_bars>required_m5_bars):
        blocks.add("M5_REQUIRED_COVERAGE_UNKNOWN")
    elif observed_m5_bars<required_m5_bars:
        blocks.add("M5_MISSINGNESS_PRESENT")
        blocks.add("M5_REQUIRED_COVERAGE_UNATTESTED")
    else:
        blocks.add("M5_REQUIRED_COVERAGE_UNATTESTED")
    # Coverage counts are claims, not independent market-hours evidence.
    return {
        "schema":SCHEMA,"version":"0.8.188",
        "decision_id":decision_id,"decision_utc":decision_utc,
        "fold":fold,"cvd_candidate_class":cvd_class,
        "retail_state":left,"cot_state":right,
        "status":"ABSTAIN_NO_PROSPECTIVE_SCIENTIFIC_ADMISSION",
        "blocking_reasons":sorted(blocks),
        "missingness_is_not_a_market_outcome":True,
        "external_first_seen_attested":False,
        "cross_market_mapping_independently_verified":False,
        "frozen_v2_protocol_modified":False,
        "backfill_or_fold_reassignment":False,
        "price_outcomes_calculated":False,
        "trade_signal_enabled":False,
        "risk_appetite_interpreted":False,
        "institutional_edge_proven":False,
        "live_oracle_cloudflare_calls":0,
    }

def audit_batch(decisions):
    if type(decisions) not in (tuple,list) or len(decisions)>5000:
        raise AdmissionError("batch_not_bounded")
    ids=set()
    reasons=Counter()
    folds=Counter()
    for params in decisions:
        if type(params) is not dict:
            raise AdmissionError("batch_invalid")
        record=review_decision(**params)
        if record["decision_id"] in ids:
            raise AdmissionError("duplicate_decision_do_not_fifo_repair")
        ids.add(record["decision_id"])
        folds[record["fold"]]+=1
        reasons.update(record["blocking_reasons"])
    return {
        "schema":SCHEMA,"decisions":len(decisions),
        "reviewed_fold_counts":dict(sorted(folds.items())),
        "blocking_reason_counts":dict(sorted(reasons.items())),
        "status":"ABSTAIN_ALL_NOT_SCIENTIFICALLY_ATTESTED",
        "counts_are_submitted_decisions_not_expected_market_bars":True,
        "price_outcomes_calculated":False,
        "trade_signals":0,
        "scientific_edge_proven":False,
    }
