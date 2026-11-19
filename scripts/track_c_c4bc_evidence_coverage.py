#!/usr/bin/env python3
"""Track C4b(c): OFFLINE evidence coverage; no new collection or LIVE access.

Input is a strictly redacted *untrusted* list of provenance metadata, NOT
resource measurements and never an authenticated receipt. This adapter cannot
turn a claimed external export, a green Action, or a synthetic test into a GO
decision. It does not read paths, HTTP, provider, environment, or secrets.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re

MODE = "OFFLINE_C4BC_REDACTED_EVIDENCE_COVERAGE_ONLY"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
MAX_RECORDS = 24
ID = re.compile(r"[A-Z][A-Z0-9_]{2,63}\Z")
# Gate-specific age is a requirement for later human review, NOT attestation.
GATES = {
    "VPS_RESOURCES": ("READONLY_RUNTIME_SNAPSHOT", timedelta(minutes=10)),
    "SQLITE_WAL_INVENTORY": ("READONLY_SQLITE_SIZE_INVENTORY", timedelta(minutes=10)),
    "OFFHOST_RESTORE": ("OFFHOST_RESTORE_ATTESTATION", timedelta(days=7)),
    "OCI_PLAN_BILLING": ("OCI_CONSOLE_PLAN_AND_COSTS", timedelta(days=1)),
    "GITHUB_USAGE": ("GITHUB_BILLING_AND_STORAGE", timedelta(days=1)),
    "FIRESTORE_USAGE": ("FIRESTORE_BILLING_AND_STORAGE", timedelta(days=1)),
    "RESEARCH_OS_ISOLATION": ("INDEPENDENT_VM_ISOLATION_REPORT", timedelta(days=7)),
    "PROVIDER_FIRST_SEEN": ("ORIGINAL_SOURCE_RECEIPT_AUDIT", timedelta(days=1)),
}
# These provenance classes never authenticate their own claims.
CLASSES = frozenset(("HISTORICAL_DOCUMENT", "SYNTHETIC_LAB",
                    "REDACTED_EXTERNAL_UNATTESTED"))
KEYS = frozenset(("gate", "sourceType", "evidenceClass", "capturedAtUtc",
                  "evidenceId"))
UTC = timezone.utc


def _utc(text):
    if type(text) is not str or not 20 <= len(text) <= 35:
        raise ValueError("strict_utc_timestamp_required")
    if not (text.endswith("Z") or text.endswith("+00:00")):
        raise ValueError("utc_only_timestamp_required")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_timestamp") from exc
    if parsed.utcoffset() != timedelta(0):
        raise ValueError("utc_only_timestamp_required")
    return parsed.astimezone(UTC)


def _check_record(obj, now):
    if type(obj) is not dict or set(obj) != KEYS:
        raise ValueError("strict_metadata_only")
    gate, source = obj["gate"], obj["sourceType"]
    if (type(gate) is not str or gate not in GATES or
            type(source) is not str or source != GATES[gate][0] or
            type(obj["evidenceClass"]) is not str or
            obj["evidenceClass"] not in CLASSES or
            type(obj["evidenceId"]) is not str or
            not ID.fullmatch(obj["evidenceId"])):
        raise ValueError("unrecognized_provenance_contract")
    timestamp = _utc(obj["capturedAtUtc"])
    if timestamp > now:
        raise ValueError("future_evidence_not_proof")
    return gate, obj["evidenceClass"], now - timestamp


def coverage(records, *, evaluated_at_utc, mode=None):
    """Sanitized deterministic coverage matrix; never gives operational GO.

    Duplicate or invalid entries taint their gate. A 'fresh' submitted export
    remains UNATTESTED because its identity/signature cannot be verified here.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_c4bc_mode_required")
    now = _utc(evaluated_at_utc)
    if type(records) not in (list, tuple) or len(records) > MAX_RECORDS:
        raise ValueError("bounded_redacted_records_required")
    indexed = {key: [] for key in GATES}
    invalid = 0
    for rec in records:
        try:
            gate, provenance, age = _check_record(rec, now)
            indexed[gate].append((provenance, age))
        except (ValueError, TypeError, KeyError, OverflowError):
            invalid += 1
    states = {}
    for gate, (source_type, ttl) in GATES.items():
        items = indexed[gate]
        if not items:
            state = "MISSING"
        elif len(items) != 1:
            state = "CONFLICT_DUPLICATE_NOT_ATTESTED"
        elif items[0][0] == "SYNTHETIC_LAB":
            state = "LAB_ONLY_NOT_OPERATIONAL_PROOF"
        elif items[0][0] == "HISTORICAL_DOCUMENT" or items[0][1] > ttl:
            state = "HISTORICAL_OR_STALE"
        else:
            state = "SUBMITTED_EXTERNAL_NOT_INDEPENDENTLY_ATTESTED"
        states[gate] = state
    # Do not pretend the supplied record covers data scope, API quotas,
    # original timestamps, OS limits, or off-host restore verification.
    blockers = tuple(k for k in GATES if states[k] !=
                     "SUBMITTED_EXTERNAL_NOT_INDEPENDENTLY_ATTESTED")
    return {
        "schema": "remura-track-c4bc-evidence-coverage-v1",
        "gateStates": states,
        "missingOrStaleOrLabGates": blockers,
        "invalidRecords": invalid,
        "submittedForHumanReview": sum(
            v == "SUBMITTED_EXTERNAL_NOT_INDEPENDENTLY_ATTESTED"
            for v in states.values()),
        "requiredGateCount": len(GATES),
        "allEvidenceIndependentlyAuthenticated": False,
        "realVpsResourceHeadroomVerified": False,
        "realSqliteWalSizesVerified": False,
        "offhostRestoreVerified": False,
        "cloudBillingVerified": False,
        "institutionalFirstSeenVerified": False,
        "liveResearchKillSwitchVerified": False,
        "operationalDecision": NO_GO,
        "newVpsRequests": 0,
        "newProviderCalls": 0,
    }
