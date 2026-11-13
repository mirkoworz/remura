#!/usr/bin/env python3
"""REMURA C4b(h): pure, offline backward-compatibility preview for /resources.

NEVER connected to the running HTTP server. Inputs are precomputed fictional
data, not file paths. This module does no IO, no sampling, no background work,
and cannot enable research or certify capacity. C4b(g) reviews the envelope.
For a real release: separate authorization, safe default-off flag, isolation,
timing evidence, backup/rollback and nine-page banner audit are mandatory.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import math
from track_c_c4bg_resource_transport_contract import (
    MODE as REVIEW_MODE, SCHEMA as TRANSPORT_SCHEMA,
    SOURCE as CORE_SCHEMA, review,
)

MODE = "OFFLINE_C4BH_LEGACY_RESOURCE_COMPATIBILITY_ONLY"
FIELDS = frozenset((
    "schema", "sampledAt", "memory", "cpu", "disk", "network",
    "uptimeSeconds", "webApi", "oracle",
))
SUBFIELDS = {
    "memory": frozenset(("total", "used", "swapTotal", "swapUsed")),
    "cpu": frozenset(("logical", "load1")),
    "disk": frozenset(("total", "used")),
    "network": frozenset(("rxSinceInterfaceStart", "txSinceInterfaceStart")),
    "webApi": frozenset(("allGet", "privateGet")),
    "oracle": frozenset(("bill", "limits", "networkMonthly", "externalApiCalls")),
}
NUMERIC_LIMIT = 2**63 - 1
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"


def _time(value):
    if type(value) is not str or not 20 <= len(value) <= 35 or not (
            value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("strict_utc_time_required")
    try:
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("malformed_utc_time") from exc
    if value.utcoffset() != timedelta(0):
        raise ValueError("strict_utc_time_required")
    return value


def _primitive(value):
    """No arbitrary objects, paths, nested custom containers or huge payloads."""
    if value is None:
        return
    if type(value) is str and len(value) <= 128:
        return
    if type(value) is bool:
        return
    if type(value) is int and 0 <= value <= NUMERIC_LIMIT:
        return
    if type(value) is float and math.isfinite(value) and 0 <= value <= NUMERIC_LIMIT:
        return
    raise ValueError("unsafe_resource_scalar")


def _baseline(snapshot):
    if type(snapshot) is not dict or set(snapshot) != FIELDS:
        raise ValueError("legacy_resource_shape_changed")
    if snapshot["schema"] != CORE_SCHEMA:
        raise ValueError("legacy_resource_version_changed")
    _time(snapshot["sampledAt"])
    for key, expected in SUBFIELDS.items():
        record = snapshot[key]
        if type(record) is not dict or set(record) != expected:
            raise ValueError("unexpected_nested_resource_fields")
        for value in record.values():
            _primitive(value)
    _primitive(snapshot["uptimeSeconds"])
    if (snapshot["oracle"]["bill"] != "unverified" or
            snapshot["oracle"]["limits"] != "unverified" or
            snapshot["oracle"]["networkMonthly"] is not None or
            snapshot["oracle"]["externalApiCalls"] is not None):
        raise ValueError("billing_proof_not_available")
    for key in ("allGet", "privateGet"):
        if type(snapshot["webApi"][key]) is not int:
            raise ValueError("strict_existing_request_counts")
    return deepcopy(snapshot)


def preview(core_snapshot, *, enabled=False, inventory_report=None,
            observed_at_utc=None, mode=None):
    """Return identical legacy response when disabled; preview-only otherwise.

    enabled=True means OFFLINE sample, NEVER a production flag; this function
    cannot perform inventory or make any request. Invalid hypothetical storage
    never changes the original resource fields or produces an operational GO.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_h_mode_required")
    if type(enabled) is not bool:
        raise ValueError("explicit_boolean_flag_required")
    baseline = _baseline(core_snapshot)
    if not enabled:
        # Byte-for-byte equal JSON shape/values, independent of provided data.
        return baseline
    if observed_at_utc is None:
        raise ValueError("explicit_review_clock_required")
    _time(observed_at_utc)
    payload = None
    if inventory_report is not None:
        payload = {
            "schema": TRANSPORT_SCHEMA,
            "resourceSchema": CORE_SCHEMA,
            "sampledAtUtc": baseline["sampledAt"],
            "inventory": inventory_report,
        }
    validated = review(payload, observed_at_utc=observed_at_utc, mode=REVIEW_MODE)
    if validated["operationalDecision"] != NO_GO or validated["remoteEndpointCurrentlyImplemented"]:
        raise ValueError("research_cannot_advance_by_transport")
    # A hypothetical, optional, sanitized field for the future private API.
    baseline["storageInventory"] = validated
    return baseline
