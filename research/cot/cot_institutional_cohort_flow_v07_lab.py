#!/usr/bin/env python3
# REMURA Shark Science COT v0.7 LAB — TFF institutional cohort changes, as-of safe.
"""Descriptive, non-predictive futures positioning comparison.

Based ONLY on synthetic forward-only sidecar versions available at decision_utc.
TFF asset managers and leveraged funds are categories, NOT identified whales,
insiders, individual trades or a spot/FX instrument. CFTC reports are delayed,
local receipt clocks untrusted; no source publication proof, no trade signals.
"""
from __future__ import annotations
from datetime import date
from math import isfinite

from cot_forward_only_v06_lab import ForwardOnlyCOT
from cot_revision_lineage_v01_lab import RevisionError,identify,parsed_stamp

SCHEMA="remura.cot.tff_cohort_flow.v07.lab"
COHORTS=("ASSET_MANAGER","LEVERAGED_FUNDS")
MAX_WEEKS=3

def _pct(num,den):
    return round(100*(num/den),6)

def _flat(x):
    if x>0:return "INCREASE"
    if x<0:return "DECREASE"
    return "NO_CHANGE"

def compare_tff_asof(store, *, code, report_dates, decision_utc):
    """Returns UNKNOWN on ANY incomplete CFTC week; no percentage from partial data."""
    if not isinstance(store,ForwardOnlyCOT):
        raise RevisionError("synthetic_sidecar_required")
    decision=parsed_stamp(decision_utc)
    if type(code) is not str or identify("tff",code,"2026-11-03") is None:
        raise RevisionError("invalid_tff_contract")
    if type(report_dates) not in (list,tuple) or len(report_dates) not in (2,3):
        raise RevisionError("two_or_three_weeks_required")
    ds=[]
    for raw in report_dates:
        report=identify("tff",code,raw)
        if report.isoweekday()!=2 or report>decision.date():
            raise RevisionError("non_tuesday_or_future_report")
        ds.append(report)
    if any((b-a).days!=7 for a,b in zip(ds,ds[1:])):
        raise RevisionError("weeks_must_be_consecutive_tuesday")
    ids=tuple(x.isoformat() for x in ds)
    observed=[]
    missing=[]
    for report_date in ids:
        x=store.as_of(dataset="tff",code=code,
                      report_date=report_date,decision_utc=decision_utc)
        if (x["status"]!="FORWARD_ONLY_LOCAL_VERSION_UNATTESTED"
                or x.get("positions") is None):
            missing.append(report_date)
        else:
            observed.append((report_date,x))
    base={
        "schema":SCHEMA,
        "status":"UNKNOWN_INCOMPLETE_ASOF" if missing
                 else "LOCAL_TFF_COHORT_FLOW_DESCRIPTIVE_UNATTESTED",
        "dataset":"tff",
        "cftc_market_code":code,
        "weekly_tuesday_reports":list(ids),
        "decision_utc":decision_utc,
        "missing_report_dates":missing,
        "calculated_weeks":0 if missing else len(observed),
        "tff_asset_manager_category_only":True,
        "tff_leveraged_funds_category_only":True,
        "position_groupings_are_not_individual_institutions":True,
        "oi_normalized_shares_not_probabilities":True,
        "source_publication_independently_verified":False,
        "local_first_seen_independently_attested":False,
        "spot_futures_mapping_verified":False,
        "prospective_market_evidence_accepted":False,
        "price_outcome_evaluated":False,
        "institutional_predictive_edge_proven":False,
        "trading_signals_generated":False,
        "live_oracle_read":False,
        "provider_calls":0,
        "actual_trading_enabled":False,
        "cohorts":None,
        "open_interest_change_pct":None,
        "change_agreement":None,
    }
    if missing:return base
    measures={name:[] for name in COHORTS}
    open_interests=[]
    for _,x in observed:
        a=x["positions"]
        if type(a) is not list or len(a)!=5 or any(
                type(v) not in (int,float) or not isfinite(v) for v in a):
            raise RevisionError("asof_tff_positions_invalid")
        oi,am_long,am_short,lev_long,lev_short=a
        if oi<=0 or min(a)<0:
            raise RevisionError("invalid_oi_or_positions")
        open_interests.append(oi)
        measures["ASSET_MANAGER"].append(_pct(am_long-am_short,oi))
        measures["LEVERAGED_FUNDS"].append(_pct(lev_long-lev_short,oi))
    result={}
    deltas={}
    for name,shares in measures.items():
        weekly=[round(b-a,6) for a,b in zip(shares,shares[1:])]
        deltas[name]=weekly[-1]
        result[name]={
            "net_to_open_interest_percent_by_week":shares,
            "week_over_week_percentage_point_change":weekly,
            "latest_change_percentage_points":weekly[-1],
            "latest_change_class":_flat(weekly[-1]),
            "weekly_acceleration_percentage_points":
                round(weekly[-1]-weekly[-2],6) if len(weekly)==2 else None,
        }
    direction=[_flat(x) for x in deltas.values()]
    agreement=("UNCHANGED_OR_MIXED_FLAT" if "NO_CHANGE" in direction
               else "CO_MOVING" if len(set(direction))==1 else "DIVERGENT")
    base.update({
        "cohorts":result,
        "open_interest_change_pct":round(100*(open_interests[-1]-open_interests[-2])/
                                           open_interests[-2],6),
        "change_agreement":agreement,
    })
    return base
