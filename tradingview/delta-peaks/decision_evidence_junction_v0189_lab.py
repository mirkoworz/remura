#!/usr/bin/env python3
# REMURA TradingView v0.8.189 LAB — per-decision identity and temporal join.
"""Offline, fail-closed evidence JUNCTION. No CVD acquisition or trading action.

IDs and clocks here are caller claims, not verified witness receipts.
No positional join, inferred futures/spot mapping, FIFO replacement, backfill,
performance measurement, or modification of prospective V2.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime
import re

from holdout_freeze_v0182_lab import guard, phase
from holdout_evidence_ledger_v0187_lab import AdmissionError, instant

SCHEMA = "remura.tv.per_decision_evidence_junction.v0189.lab"
KINDS = ("CVD_M5", "PRICE_ONLY_M5", "RETAIL", "COT_TFF")
ID = re.compile(r"^[A-Z0-9_.:-]{1,80}$")
HASH = re.compile(r"^[0-9a-f]{64}$")
TICKER = re.compile(r"^[A-Z0-9_.:-]{1,40}$")
INST_KEYS = frozenset(("market", "provider", "ticker", "product", "contract"))
DEC_KEYS = frozenset(("decision_id", "decision_utc", "instrument", "evidence_ids"))
ROW_KEYS = frozenset((
    "evidence_id", "decision_id", "kind", "instrument", "observed_utc",
    "received_utc", "published_utc", "source_sha256",
))
UNTRUSTED = "CLAIM_ONLY_NOT_FIRST_SEEN"
RESEARCH_ONLY = "ABSTAIN_NO_ATTESTED_PER_DECISION_PROOF"

def _id(value):
    return type(value) is str and ID.fullmatch(value) is not None

def _inst(value):
    return (type(value) is dict and set(value) == INST_KEYS
            and all(type(value[k]) is str and TICKER.fullmatch(value[k])
                    for k in ("market", "provider", "ticker"))
            and value["product"] in ("SPOT", "FUTURE", "CFD", "INDEX")
            and type(value["contract"]) is str
            and ((value["product"] == "FUTURE" and
                  TICKER.fullmatch(value["contract"]) is not None)
                 or (value["product"] != "FUTURE" and value["contract"] == "")))

def _utc(value):
    if value is None:
        return None
    return instant(value)

def _claim_order(source, decision, value):
    if source is None or source > decision:
        value.add("RECEIPT_LATE_OR_UNKNOWN_AT_DECISION")

def _review_one(decision, lookup):
    if type(decision) is not dict or set(decision) != DEC_KEYS:
        raise AdmissionError("invalid_decision_schema")
    if not _id(decision["decision_id"]) or not _inst(decision["instrument"]):
        raise AdmissionError("invalid_decision_identity")
    at = instant(decision["decision_utc"])
    fold = phase(at)
    ids = decision["evidence_ids"]
    if type(ids) is not dict or set(ids) != set(KINDS):
        raise AdmissionError("missing_explicit_four_source_slots")
    if any(ref is not None and not _id(ref) for ref in ids.values()):
        raise AdmissionError("invalid_evidence_pointer")
    refs = [ref for ref in ids.values() if ref is not None]
    if len(refs) != len(set(refs)):
        raise AdmissionError("same_evidence_used_for_multiple_source_kinds")
    blocks = set()
    if fold not in ("HOLDOUT_1", "HOLDOUT_2"):
        blocks.add("OUTSIDE_FROZEN_HOLDOUT")
    links = {}
    selected = {}
    for kind in KINDS:
        ref = ids[kind]
        if ref is None:
            blocks.add(kind + "_MISSING_NOT_ZERO")
            links[kind] = "UNKNOWN"
            continue
        row = lookup.get(ref)
        if row is None:
            blocks.add(kind + "_POINTER_NOT_FOUND")
            links[kind] = "UNRESOLVED"
            continue
        if row["decision_id"] != decision["decision_id"]:
            blocks.add(kind + "_CROSS_DECISION_LINK")
            links[kind] = "REJECTED"
            continue
        if row["kind"] != kind:
            blocks.add(kind + "_WRONG_EVIDENCE_KIND")
            links[kind] = "REJECTED"
            continue
        selected[kind] = row
        links[kind] = UNTRUSTED
        received = _utc(row["received_utc"])
        observed = _utc(row["observed_utc"])
        _claim_order(received, at, blocks)
        if observed is None or observed > at:
            blocks.add(kind + "_OBSERVATION_FUTURE_OR_UNKNOWN")
        if received is not None and observed is not None and received < observed:
            blocks.add(kind + "_RECEIPT_BEFORE_OBSERVATION")
        if kind == "COT_TFF":
            if row["instrument"]["product"] != "FUTURE":
                blocks.add("COT_INSTRUMENT_NOT_FUTURE")
            # Futures metadata is not a verified spot/FX mapping.
            blocks.add("COT_FUTURES_SPOT_MAPPING_UNVERIFIED")
            published = _utc(row["published_utc"])
            if (published is None or observed is None or received is None
                    or not observed <= published <= received <= at):
                blocks.add("COT_PUBLICATION_CHAIN_LATE_OR_UNKNOWN")
        else:
            if row["instrument"] != decision["instrument"]:
                blocks.add(kind + "_EXACT_INSTRUMENT_MISMATCH")
            if row["published_utc"] is not None:
                blocks.add(kind + "_UNEXPECTED_PUBLICATION_CLAIM")
        if kind in ("CVD_M5", "PRICE_ONLY_M5"):
            if observed is None or int(observed.timestamp()) % 300 != 0:
                blocks.add(kind + "_BAR_NOT_M5_ALIGNED")
            if kind == "CVD_M5" and observed is not None and received is not None:
                seconds = (received - observed).total_seconds()
                if seconds < 0 or seconds > 120 or seconds >= 300:
                    blocks.add("CVD_M5_RECEIPT_V2_LATE")
    if "CVD_M5" in selected and "PRICE_ONLY_M5" in selected:
        if selected["CVD_M5"]["observed_utc"] != selected["PRICE_ONLY_M5"]["observed_utc"]:
            blocks.add("PRICE_COMPARATOR_BAR_NOT_IDENTICAL")
    blocks.add("ALL_SOURCE_TIMESTAMPS_ONLY_SELF_REPORTED")
    blocks.add("INDEPENDENT_SOURCE_RECEIPTS_NOT_VERIFIED")
    blocks.add("PRICE_ONLY_VS_CVD_OUTCOMES_NOT_CALCULATED")
    return {
        "decision_id": decision["decision_id"], "decision_utc": decision["decision_utc"],
        "fold": fold, "links": links, "blocking_reasons": sorted(blocks),
        "status": RESEARCH_ONLY, "no_market_missingness_imputed": True,
        "first_seen_independently_proven": False, "no_signals": True,
        "comparator_not_an_outcome": True,
    }

def inspect_join(decisions, evidence_rows):
    guard()  # frozen V2, fail if preregistered protocol changed
    if (type(decisions) not in (list, tuple) or
        type(evidence_rows) not in (list, tuple) or
        len(decisions) > 2000 or len(evidence_rows) > 8000):
        raise AdmissionError("bounded_decision_rows_required")
    lookup = {}
    for row in evidence_rows:
        if type(row) is not dict or set(row) != ROW_KEYS:
            raise AdmissionError("invalid_evidence_schema")
        if not _id(row["evidence_id"]) or not _id(row["decision_id"]):
            raise AdmissionError("invalid_evidence_id")
        if row["kind"] not in KINDS or not _inst(row["instrument"]):
            raise AdmissionError("invalid_evidence_source_identity")
        if type(row["source_sha256"]) is not str or not HASH.fullmatch(row["source_sha256"]):
            raise AdmissionError("invalid_source_hash")
        _utc(row["observed_utc"])
        _utc(row["received_utc"])
        _utc(row["published_utc"])
        if row["evidence_id"] in lookup:
            raise AdmissionError("duplicate_evidence_id_no_repair")
        lookup[row["evidence_id"]] = row
    decisions_seen = set()
    used = set()
    reports = []
    for decision in decisions:
        report = _review_one(decision, lookup)
        if report["decision_id"] in decisions_seen:
            raise AdmissionError("duplicate_decision_id_no_fifo_repair")
        decisions_seen.add(report["decision_id"])
        used.update(x for x in decision["evidence_ids"].values() if x is not None)
        reports.append(report)
    orphan = sorted(set(lookup) - used)
    duplicate_claim = sum(len(x["blocking_reasons"]) for x in reports)
    return {
        "schema": SCHEMA, "version": "0.8.189",
        "status": "ABSTAIN_RESEARCH_ONLY",
        "decisions": reports, "decision_count": len(reports),
        "input_evidence_count": len(evidence_rows),
        "unreferenced_evidence_ids": orphan,
        "blocking_reasons_by_type": dict(sorted(Counter(
            r for report in reports for r in report["blocking_reasons"]
        ).items())),
        "source_join_ambiguous": bool(orphan),
        "no_live_feed_or_api": True, "real_holdout_evidence_inferred": False,
        "protocol_v2_changed": False, "backfill_performed": False,
        "price_outcomes_computed": False, "institutional_edge_proven": False,
        "orders_enabled": False, "aggregate_blocker_instances": duplicate_claim,
    }
