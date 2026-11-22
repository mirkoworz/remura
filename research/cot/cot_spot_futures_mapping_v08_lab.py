#!/usr/bin/env python3
# REMURA COT v0.8 LAB — no implicit TFF futures -> spot Forex mapping.
"""Explicit, UNVERIFIED USD-leg direction sketches for review only.

A CFTC TFF market code never proves a spot ticker mapping by itself. In
particular, a USD-base Forex pair has opposite orientation from the
non-USD currency future quoted in USD. A cross needs 2 legs and a different
model. No market orders, forecasting, or scientific admission.
"""
from __future__ import annotations
import re

from cot_institutional_cohort_flow_v07_lab import compare_tff_asof
from cot_forward_only_v06_lab import ForwardOnlyCOT
from cot_revision_lineage_v01_lab import identify,RevisionError

SCHEMA="remura.cot.usd_fx_mapping_review.v08.lab"
HEX=re.compile(r"^[a-f0-9]{64}$")
CCY=re.compile(r"^[A-Z]{3}$")
PAIR=re.compile(r"^[A-Z]{6}$")
FIELDS=frozenset(("fx_symbol","cftc_code_claim","future_underlying_currency_claim",
                  "future_quote_currency_claim","mapping_artifact_sha256_claim",
                  "mapping_document_ref_claim","evidence_status"))
STATUS="UNVERIFIED_LOCAL_CLAIM"

class MappingError(ValueError):
    pass

def sketch_spot_mapping(store, *, proposal, report_dates, decision_utc):
    if not isinstance(store,ForwardOnlyCOT):
        raise MappingError("forward_only_synthetic_store_required")
    if type(proposal) is not dict or set(proposal)!=FIELDS:
        raise MappingError("mapping_claim_schema_invalid")
    pair=proposal["fx_symbol"]
    code=proposal["cftc_code_claim"]
    under=proposal["future_underlying_currency_claim"]
    quote=proposal["future_quote_currency_claim"]
    artifact=proposal["mapping_artifact_sha256_claim"]
    doc=proposal["mapping_document_ref_claim"]
    if (type(pair) is not str or PAIR.fullmatch(pair) is None or
            type(under) is not str or CCY.fullmatch(under) is None or
            type(quote) is not str or CCY.fullmatch(quote) is None or
            type(code) is not str):
        raise MappingError("invalid_currency_or_code_claim")
    identify("tff",code,"2026-11-03")  # Only valid CFTC TFF market code; NOT a verified mapping.
    if (type(artifact) is not str or HEX.fullmatch(artifact) is None or
            type(doc) is not str or not 4<=len(doc)<=120 or
            re.fullmatch(r"[a-zA-Z0-9_./:-]{4,120}",doc) is None or
            proposal["evidence_status"]!=STATUS):
        raise MappingError("unverifiable_or_unpinned_mapping_claim")
    base,spot_quote=pair[:3],pair[3:]
    if base==spot_quote:
        raise MappingError("same_currency_pair_not_forex")
    if (quote!="USD" or
            ((base=="USD")+(spot_quote=="USD"))!=1 or
            under not in (base,spot_quote) or under=="USD"):
        return {
            "schema":SCHEMA,"status":"UNKNOWN_UNSUPPORTED_OR_CROSS_MAPPING",
            "fx_symbol":pair,"claim_only":True,
            "assumed_orientation":None,"cohort_deltas":None,
            "cftc_code_to_currency_independently_proven":False,
            "execution_basis_proven":False,"scientific_admission":False,
            "signal_allowed":False,
        }
    # Deliberately do not assert that the code actually identifies 'under'.
    # A review-ready sign calculation is not a factual market symbol mapping.
    sign=1 if under==base else -1
    flow=compare_tff_asof(store,code=code,report_dates=report_dates,
                          decision_utc=decision_utc)
    if flow["status"]=="UNKNOWN_INCOMPLETE_ASOF":
        return {
            "schema":SCHEMA,"status":"UNKNOWN_COT_WEEK_AT_DECISION",
            "fx_symbol":pair,"claim_only":True,
            "missing_report_dates":flow["missing_report_dates"],
            "assumed_orientation":None,"cohort_deltas":None,
            "cftc_code_to_currency_independently_proven":False,
            "execution_basis_proven":False,"scientific_admission":False,
            "signal_allowed":False,
        }
    if flow["status"]!="LOCAL_TFF_COHORT_FLOW_DESCRIPTIVE_UNATTESTED":
        raise MappingError("unexpected_cot_flow_status")
    return {
        "schema":SCHEMA,
        "status":"UNATTESTED_USD_LEG_DIRECTION_SKETCH_NOT_SIGNAL",
        "fx_symbol":pair,
        "cftc_market_code_claim":code,
        "future_underlying_currency_claim":under,
        "future_quote_currency_claim":quote,
        "mapping_artifact_sha256_claim":artifact,
        "mapping_document_ref_claim":doc,
        "assumed_orientation":"SAME_SIGN_AS_NON_USD_FUTURE" if sign==1 else
                              "INVERTED_VERSUS_NON_USD_FUTURE",
        "cohort_deltas":{
            k:round(sign*flow["cohorts"][k]["latest_change_percentage_points"],6)
            for k in ("ASSET_MANAGER","LEVERAGED_FUNDS")
        },
        "delta_unit":"PERCENTAGE_POINTS_OPEN_INTEREST_CLAIM_ONLY",
        "cohort_category_is_not_named_institution":True,
        "cftc_code_to_currency_independently_proven":False,
        "futures_contract_specification_verified":False,
        "futures_publication_time_verified":False,
        "spot_feed_contract_verified":False,
        "independent_first_seen_verified":False,
        "basis_and_roll_adjustments_verified":False,
        "execution_basis_proven":False,
        "scientific_admission":False,
        "signal_allowed":False,
        "real_data_used":False,
        "oracle_queried":False,
        "provider_calls":0,
    }
