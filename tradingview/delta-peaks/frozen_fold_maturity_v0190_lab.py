#!/usr/bin/env python3
# REMURA TradingView v0.8.190 LAB — frozen-fold per-decision maturation plan.
"""Prospective *scheduling* only, never price outcomes or evidence admission.

Joins are delegated to v0.8.189. The purpose here is to forbid CVD/price
bars before the assigned holdout, prevent an outcome window crossing a fold,
and identify pending horizon maturities without imputing missing market bars.
Self-reported evaluation time is NOT a receipt or independent wall clock.
"""
from __future__ import annotations
from collections import Counter
from datetime import timedelta

from decision_evidence_junction_v0189_lab import inspect_join
from holdout_evidence_ledger_v0187_lab import AdmissionError, instant
from holdout_freeze_v0182_lab import H1_START,H2_START,H2_END,phase,guard

SCHEMA="remura.tv.frozen_fold_maturity.v0190.lab"
HORIZONS=(("PRIMARY_60M",60),("SECONDARY_240M",240),("SECONDARY_1440M",1440))
WINDOWS={
    "HOLDOUT_1":(H1_START,H2_START),
    "HOLDOUT_2":(H2_START,H2_END),
}
SOURCE_KINDS=("CVD_M5","PRICE_ONLY_M5")

def plan_maturities(decisions, evidence_rows, *, evaluation_utc):
    """No outcomes; no matching, raw data, trading, or online clock."""
    guard()
    evaluation=instant(evaluation_utc)
    if type(decisions) not in (list,tuple) or type(evidence_rows) not in (list,tuple):
        raise AdmissionError("bounded_lists_required")
    baseline=inspect_join(decisions,evidence_rows)
    lookup={row["evidence_id"]:row for row in evidence_rows}
    reports=[]
    for d,old in zip(decisions,baseline["decisions"]):
        decision=instant(d["decision_utc"])
        fold=phase(decision)
        blocks=set(old["blocking_reasons"])
        if fold in WINDOWS:
            start,end=WINDOWS[fold]
        else:
            start=end=None
        for kind in SOURCE_KINDS:
            ptr=d["evidence_ids"][kind]
            row=lookup.get(ptr) if ptr is not None else None
            if row is None or row["decision_id"]!=d["decision_id"] or row["kind"]!=kind:
                blocks.add(kind+"_FOLD_SOURCE_UNAVAILABLE")
                continue
            close=instant(row["observed_utc"]) if row["observed_utc"] else None
            if start is None or close is None or not start<=close<end:
                blocks.add(kind+"_BAR_OUTSIDE_DECISION_FOLD")
        horizons={}
        for name,minutes in HORIZONS:
            target=decision+timedelta(minutes=minutes)
            if start is None:
                state="NOT_IN_HOLDOUT"
            elif target>end:
                state="CROSSES_EXCLUSIVE_FOLD_END_NO_OUTCOME"
                blocks.add(name+"_CROSSES_FOLD_END")
            elif evaluation<target:
                state="PENDING_CLAIMED_EVALUATION_CLOCK"
            else:
                state="WINDOW_ELAPSED_CLAIM_ONLY_NO_OUTCOME"
            horizons[name]={
                "target_utc":target.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "state":state,
                "price_outcome":None,
                "cvd_outcome":None,
                "market_bars_complete":False,
                "maturity_clock_independently_verified":False,
            }
        reports.append({
            "decision_id":d["decision_id"],
            "fold":fold,
            "fold_start_utc":None if start is None else start.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "fold_end_exclusive_utc":None if end is None else end.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "horizons":horizons,
            "blocking_reasons":sorted(blocks),
            "status":"ABSTAIN_EVIDENCE_NOT_INDEPENDENTLY_VERIFIED",
            "historical_backfill_permitted":False,
            "fifo_pairing_not_changed":True,
            "outcomes_not_computed":True,
        })
    return {
        "schema":SCHEMA,
        "version":"0.8.190",
        "evaluation_clock_utc_claim":evaluation_utc,
        "status":"NO_GO_PROSPECTIVE_ALPHA",
        "decisions":reports,
        "total":len(reports),
        "fold_counts":dict(sorted(Counter(r["fold"] for r in reports).items())),
        "source_receipts_independently_verified":False,
        "evaluation_clock_independently_attested":False,
        "expected_market_bar_denominator_known":False,
        "holdout_signal_or_pnl":False,
        "frozen_v2_protocol_changed":False,
        "external_services_used":False,
        "live_capture_enabled":False,
    }
