#!/usr/bin/env python3
# REMURA Retail provenance v0.6 LAB — future receipt ledger, offline only.
"""Capture *claims* about future data availability without inventing first-seen.

Immutable-by-convention hash links detect accidental modification of a supplied
ledger, not adversarial rewriting unless the head is pinned independently.
No cryptographic signature or witness is verified. Even externally attributed
times remain untrusted, and no receipt can grant admission to a live strategy.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha256
import json
import re

SCHEMA = "remura.retail.provenance_receipts.v06.lab"
ISO = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
HEX = re.compile(r"^[0-9a-f]{64}$")
COMMIT = re.compile(r"^[0-9a-f]{40}$")
IDENT = re.compile(r"^[A-Za-z0-9_.:/-]{1,120}$")
# Origin and authority are classifications claimed by the record creator.
KINDS = {
    "COLLECTOR_API_RETURN": "LOCAL_COLLECTOR",
    "SNAPSHOT_WRITTEN": "LOCAL_COLLECTOR",
    "GIT_CONTENT_COMMIT": "GIT_CONTENT",
    "GITHUB_ACTIONS_EVENT": "GITHUB_REPORTED",
    "PAGES_DEPLOYMENT_COMPLETED": "GITHUB_REPORTED",
    "PROVIDER_PUBLICATION": "PROVIDER_REPORTED",
    "INDEPENDENT_RECEIPT": "WITNESS_REPORTED",
}
EVENT_KEYS = frozenset((
    "event_id", "kind", "authority", "event_at_utc",
    "recorded_at_utc", "reference", "response_sha256",
))
RECORD_KEYS = frozenset(("prev_sha256", "event", "record_sha256"))
GENESIS = "0" * 64

class ReceiptError(ValueError):
    pass

def utc(value):
    if type(value) is not str or not ISO.fullmatch(value):
        raise ReceiptError("noncanonical_utc")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ReceiptError("invalid_utc") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ReceiptError("noncanonical_utc")
    return parsed

def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")

def _validate_event(event):
    if type(event) is not dict or set(event) != EVENT_KEYS:
        raise ReceiptError("event_schema_invalid")
    if type(event["kind"]) is not str or event["kind"] not in KINDS:
        raise ReceiptError("unknown_event_kind")
    if event["authority"] != KINDS[event["kind"]]:
        raise ReceiptError("event_authority_mismatch")
    for key in ("event_id", "reference"):
        if type(event[key]) is not str or not IDENT.fullmatch(event[key]):
            raise ReceiptError("invalid_event_reference")
    if type(event["response_sha256"]) is not str or not HEX.fullmatch(event["response_sha256"]):
        raise ReceiptError("invalid_response_digest")
    happened, recorded = utc(event["event_at_utc"]), utc(event["recorded_at_utc"])
    # Do not impose cross-system clock causality; a provider clock is not trusted.
    return happened, recorded

def start(*, content_commit, content_sha256):
    if type(content_commit) is not str or not COMMIT.fullmatch(content_commit):
        raise ReceiptError("invalid_content_commit")
    if type(content_sha256) is not str or not HEX.fullmatch(content_sha256):
        raise ReceiptError("invalid_content_sha256")
    return {
        "schema": SCHEMA, "content_commit": content_commit,
        "content_sha256": content_sha256, "events": [],
        "head_sha256": GENESIS,
    }

def _record_hash(prev, event):
    return sha256(canonical({"prev_sha256": prev, "event": event})).hexdigest()

def audit(ledger):
    if type(ledger) is not dict or set(ledger) != {
        "schema", "content_commit", "content_sha256", "events", "head_sha256"
    } or ledger["schema"] != SCHEMA:
        raise ReceiptError("ledger_schema_invalid")
    if type(ledger["content_commit"]) is not str or not COMMIT.fullmatch(ledger["content_commit"]):
        raise ReceiptError("invalid_content_commit")
    if type(ledger["content_sha256"]) is not str or not HEX.fullmatch(ledger["content_sha256"]):
        raise ReceiptError("invalid_content_sha256")
    if type(ledger["events"]) is not list or len(ledger["events"]) > 1000:
        raise ReceiptError("ledger_not_bounded")
    prev, seen, last_ingested = GENESIS, set(), None
    for item in ledger["events"]:
        if type(item) is not dict or set(item) != RECORD_KEYS:
            raise ReceiptError("record_schema_invalid")
        event = item["event"]
        _, ingested = _validate_event(event)
        if event["event_id"] in seen:
            raise ReceiptError("duplicate_event_id")
        if last_ingested is not None and ingested < last_ingested:
            raise ReceiptError("retroactive_recording_order")
        seen.add(event["event_id"])
        if item["prev_sha256"] != prev:
            raise ReceiptError("broken_previous_link")
        digest = _record_hash(prev, event)
        if item["record_sha256"] != digest:
            raise ReceiptError("record_hash_mismatch")
        prev, last_ingested = digest, ingested
    if ledger["head_sha256"] != prev:
        raise ReceiptError("ledger_head_mismatch")
    return {"records": len(seen), "head_sha256": prev,
            "hash_chain_externally_pinned": False,
            "external_receipt_signatures_verified": False,
            "event_clocks_independently_proven": False}

def append(ledger, event):
    audit(ledger)
    _validate_event(event)
    previous = ledger["head_sha256"]
    item = {"prev_sha256": previous, "event": dict(event),
            "record_sha256": _record_hash(previous, event)}
    result = {**ledger, "events": ledger["events"] + [item],
              "head_sha256": item["record_sha256"]}
    audit(result)
    return result

def assess_at_decision(ledger, decision_utc):
    """All evidence is insufficient without a real independently verified witness."""
    audit(ledger)
    decision = utc(decision_utc)
    kinds = {x["event"]["kind"] for x in ledger["events"]}
    witness = [x["event"] for x in ledger["events"]
               if x["event"]["kind"] == "INDEPENDENT_RECEIPT"]
    late_claims = sorted(x["event_id"] for x in witness
                         if utc(x["event_at_utc"]) > decision
                         or utc(x["recorded_at_utc"]) > decision)
    no_receipt = not witness
    blocks = []
    if "COLLECTOR_API_RETURN" not in kinds:
        blocks.append("COLLECTOR_RETURN_NOT_RECORDED")
    if "GIT_CONTENT_COMMIT" not in kinds:
        blocks.append("COMMIT_TIME_NOT_RECORDED")
    if "PROVIDER_PUBLICATION" not in kinds:
        blocks.append("PROVIDER_PUBLICATION_UNKNOWN")
    if no_receipt:
        blocks.append("INDEPENDENT_FIRST_SEEN_UNKNOWN")
    if late_claims:
        blocks.append("WITNESS_CLAIM_AFTER_DECISION")
    blocks.append("RECEIPT_AUTHENTICITY_NOT_VERIFIED_OFFLINE")
    blocks.append("CHAIN_HEAD_NOT_EXTERNALLY_PINNED")
    return {
        "schema": SCHEMA, "decision_utc": decision_utc,
        "record_count": len(ledger["events"]),
        "ledger_head_sha256": ledger["head_sha256"],
        "witness_claim_count": len(witness),
        "post_decision_witness_claim_ids": late_claims,
        "provider_publication_time": "UNKNOWN" if "PROVIDER_PUBLICATION" not in kinds
                                     else "CLAIM_ONLY_UNATTESTED",
        "public_page_availability": "UNKNOWN" if "PAGES_DEPLOYMENT_COMPLETED" not in kinds
                                     else "GITHUB_REPORTED_UNATTESTED",
        "independent_first_seen": "UNKNOWN" if no_receipt else "CLAIM_ONLY_UNATTESTED",
        "status": "NO_GO_SCIENTIFIC_ADMISSION",
        "blocking_reasons": sorted(blocks),
        "external_calls": 0,
        "auto_backfill": False,
        "external_witness_installed": False,
        "cryptographic_attestation_verified": False,
        "decision_admission_allowed": False,
    }
