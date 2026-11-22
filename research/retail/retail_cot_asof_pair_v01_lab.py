# REMURA retail x CFTC decision pairing v0.1 LAB — 22 Nov 2026
"""Synthetic-only, source-specific as-of gate. No real providers or trading.

Myfxbook RETAIL != CFTC futures/institutions. A declared instrument mapping
is merely a LAB fixture assertion, never external mapping verification.
A local receipt and SHA-256 do NOT prove independent first-seen.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
import re

STAMP = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ$")
KINDS = frozenset(("MYFXBOOK_RETAIL", "CFTC_FUTURES"))
MAX_PAYLOAD = 16384


class GateError(ValueError):
    pass


def strict_utc(value):
    if type(value) is not str or not STAMP.fullmatch(value):
        raise GateError("invalid_utc_stamp")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise GateError("invalid_utc_stamp") from exc
    if stamp.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise GateError("invalid_utc_stamp")
    return stamp


@dataclass(frozen=True)
class FrozenSample:
    provider: str
    instrument: str
    receipt_utc: str
    observation_utc: str | None
    content_json: str
    content_sha256: str
    source_id: str
    version: int


def make_fixture_sample(*, provider, instrument, receipt_utc, payload,
                        source_id, observation_utc=None, version=1):
    if provider not in KINDS or type(provider) is not str:
        raise GateError("unsupported_provider")
    if type(instrument) is not str or not 1 <= len(instrument) <= 64:
        raise GateError("invalid_instrument")
    if type(source_id) is not str or not 1 <= len(source_id) <= 80:
        raise GateError("invalid_capture_id")
    strict_utc(receipt_utc)
    if observation_utc is not None:
        strict_utc(observation_utc)
    if type(version) is not int or version < 1:
        raise GateError("invalid_version")
    if type(payload) is not dict or not payload:
        raise GateError("invalid_payload")
    try:
        content = json.dumps(payload, sort_keys=True, separators=(",", ":"),
                             ensure_ascii=True, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise GateError("invalid_payload") from exc
    if len(content.encode("ascii")) > MAX_PAYLOAD:
        raise GateError("payload_too_large")
    return FrozenSample(provider, instrument, receipt_utc, observation_utc,
                        content, sha256(content.encode("ascii")).hexdigest(),
                        source_id, version)


def select_asof(samples, *, provider, instrument, decision_utc):
    """Return only the latest available, intact record; quarantine conflicts."""
    decision = strict_utc(decision_utc)
    if type(samples) not in (tuple, list) or len(samples) > 3000:
        raise GateError("invalid_batch")
    eligible = []
    for sample in samples:
        if type(sample) is not FrozenSample:
            raise GateError("unexpected_sample_type")
        # Never implicitly replace a source with another source's observations.
        if sample.provider != provider or sample.instrument != instrument:
            continue
        received = strict_utc(sample.receipt_utc)
        if received > decision:
            continue
        if (sample.observation_utc is not None and
                strict_utc(sample.observation_utc) > received):
            return "CLOCK_CONFLICT", None
        if sha256(sample.content_json.encode("ascii")).hexdigest() != sample.content_sha256:
            return "INTEGRITY_ERROR", None
        eligible.append(sample)
    if not eligible:
        return "UNKNOWN_NOT_AVAILABLE", None

    latest = max(s.receipt_utc for s in eligible)
    group = [s for s in eligible if s.receipt_utc == latest]
    # Any two different payloads at the same local first-seen are ambiguous.
    if len({s.content_sha256 for s in group}) != 1:
        return "SOURCE_CONFLICT", None
    # A source version number must not be silently promoted over a later receipt.
    best = max(group, key=lambda s: s.version)
    if any(s.version > best.version for s in eligible):
        return "VERSION_ORDER_CONFLICT", None
    if any(s.version == best.version and s.content_sha256 != best.content_sha256
           for s in eligible):
        return "VERSION_ORDER_CONFLICT", None
    return "LOCAL_OBSERVED_UNATTESTED", best


def pair_for_decision(*, decision_id, decision_utc, retail_samples, cot_samples,
                      retail_symbol, cot_futures_code, declared_mapping):
    """A declared LAB mapping allows a provisional pair, NOT verified alpha."""
    strict_utc(decision_utc)
    if type(decision_id) is not str or not 1 <= len(decision_id) <= 80:
        raise GateError("decision_identity_required")
    if not declared_mapping or type(declared_mapping) is not str:
        return {"status": "NON_COMPARABLE", "retail": None, "cot": None,
                "reason": "missing_explicit_mapping"}
    if not retail_symbol or not cot_futures_code:
        return {"status": "NON_COMPARABLE", "retail": None, "cot": None,
                "reason": "missing_instrument_identity"}

    left_state, left = select_asof(
        retail_samples, provider="MYFXBOOK_RETAIL",
        instrument=retail_symbol, decision_utc=decision_utc)
    right_state, right = select_asof(
        cot_samples, provider="CFTC_FUTURES",
        instrument=cot_futures_code, decision_utc=decision_utc)

    for state in ("INTEGRITY_ERROR", "CLOCK_CONFLICT",
                  "SOURCE_CONFLICT", "VERSION_ORDER_CONFLICT"):
        if state in (left_state, right_state):
            return {"status": "QUARANTINE", "reason": state,
                    "retail": None, "cot": None}
    if left is None or right is None:
        return {"status": "UNKNOWN_NOT_AVAILABLE",
                "reason": "missing_prospective_source",
                "retail_state": left_state, "cot_state": right_state,
                "retail": None, "cot": None}

    return {
        "status": "LOCAL_PAIR_UNATTESTED_FIXTURE_ONLY",
        "decision_id": decision_id,
        "decision_utc": decision_utc,
        "mapping_claim": declared_mapping,
        "mapping_independently_verified": False,
        "external_first_seen_verified": False,
        "institutional_edge_established": False,
        "retail": {"provider": left.provider, "receipt_utc": left.receipt_utc,
                   "version": left.version, "sha256": left.content_sha256,
                   "payload": json.loads(left.content_json)},
        "cot": {"provider": right.provider, "receipt_utc": right.receipt_utc,
                "version": right.version, "sha256": right.content_sha256,
                "payload": json.loads(right.content_json)},
    }
