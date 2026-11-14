#!/usr/bin/env python3
# REMURA v0.8.53 LAB — 14/11/2026 11:39 CET
"""Proposed FX-only configuration envelope. OFFLINE; not the deployed protocol.
The nested snapshot retains the strict v1 event schema. Configuration is a
sender declaration, not proof of actual alert settings or market provenance.
Never expose this contract on the current gateway until a separate review.
"""
import json
from fx_pilot_config_v1 import REFERENCE, compare_v1_fields
from validate_telemetry_v1 import validate_payload, MAX_BYTES

SCHEMA = "remura.tv.flow.configured.preview.v1"
M5 = 300_000


def validate_envelope(envelope, *, received_ms):
    if not isinstance(envelope, dict) or set(envelope) != {"schema","snapshot","configuration"}:
        raise ValueError("invalid_envelope_fields")
    if envelope["schema"] != SCHEMA:
        raise ValueError("invalid_envelope_schema")
    if type(received_ms) is not int:
        raise ValueError("receiver_timestamp_required")
    encoded = json.dumps(envelope, sort_keys=True, separators=(",",":"), allow_nan=False)
    if len(encoded.encode("utf-8")) > MAX_BYTES:
        raise ValueError("envelope_too_large")
    snapshot = envelope["snapshot"]
    check = validate_payload(snapshot, received_ms=received_ms)
    if snapshot["feed"] != "FXCM" or snapshot["bar_close_ms"] % M5 or (
        snapshot["bar_close_ms"]-snapshot["bar_open_ms"] != M5):
        raise ValueError("unexpected_feed_or_bar")
    config = compare_v1_fields(snapshot,envelope["configuration"])
    if not config["reference_match"] or not config["v1_fields_match"]:
        raise ValueError("configuration_mismatch")
    if not check["timely_for_prospective"]:
        raise ValueError("not_timely")
    if any(t is not None and t > snapshot["bar_close_ms"] for t in snapshot["level_origin_ms"].values()):
        raise ValueError("future_level")
    return {
        "schema":SCHEMA,
        "status":"CONFIG_DECLARATION_MATCH_ONLY",
        "event_key":check["event_key"],
        "declared_config_sha256":config["declared_config_sha256"],
        "received_at_ms":received_ms,
        "bar_close_ms":snapshot["bar_close_ms"],
        "lag_ms":check["lag_ms"],
        "configuration_fields":len(REFERENCE),
        "effective_alert_inputs_attested":False,
        "scientific_admission":False,
        "orders_enabled":False,
    }
