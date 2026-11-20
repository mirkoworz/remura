#!/usr/bin/env python3
# REMURA v0.8.31 — 13/11/2026, ore 21:09 CET
# OFF-only rollback preflight: in-memory validation, no Cloudflare mutation.
"""Verify strict TEST Worker bindings before any future rollback to inert bootstrap.

Only an already-empty bootstrap or an isolated D1 TEST+limiter+OFF worker
may proceed. Unknown/secret/ON/mismatched bindings must block. Use with a
fresh read-only Cloudflare GET in a separately authorized future workflow.
"""
from __future__ import annotations

import re

EXPECTED_WORKER = "remura-tv-webhook-test"
UUID_RE = re.compile(r"^[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}$", re.I)


class RollbackUnsafe(ValueError):
    pass


def inspect_worker_bindings(payload: object, *, verified_test_uuid: str,
                            expected_namespace: str) -> str:
    if not (isinstance(verified_test_uuid, str) and
            UUID_RE.fullmatch(verified_test_uuid)):
        raise RollbackUnsafe("test_db_uuid_unverified")
    if not (isinstance(expected_namespace, str)
            and re.fullmatch(r"[1-9][0-9]{0,14}", expected_namespace)):
        raise RollbackUnsafe("namespace_unverified")
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise RollbackUnsafe("worker_response_unknown")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise RollbackUnsafe("settings_invalid")
    if "name" in result and result["name"] != EXPECTED_WORKER:
        raise RollbackUnsafe("wrong_worker")
    bindings = result.get("bindings")
    if not isinstance(bindings, list):
        raise RollbackUnsafe("bindings_unknown")
    if bindings == []:
        return "BOOTSTRAP_ALREADY_EMPTY"
    if len(bindings) != 3 or any(not isinstance(item, dict) for item in bindings):
        raise RollbackUnsafe("unexpected_binding_count")
    by_name = {item.get("name"): item for item in bindings}
    if len(by_name) != 3 or set(by_name) != {
        "TELEMETRY_DB", "INGEST_RATE_LIMITER", "INGEST_ENABLED"
    }:
        raise RollbackUnsafe("unexpected_binding_names")
    db = by_name["TELEMETRY_DB"]
    if db.get("type") != "d1" or db.get("id") != verified_test_uuid:
        raise RollbackUnsafe("db_mismatch")
    rl = by_name["INGEST_RATE_LIMITER"]
    if (rl.get("type") != "ratelimit" or
            rl.get("namespace_id") != expected_namespace or
            rl.get("simple") != {"limit": 20, "period": 60}):
        raise RollbackUnsafe("limiter_config_mismatch")
    flag = by_name["INGEST_ENABLED"]
    if flag.get("type") != "plain_text" or flag.get("text") != "false":
        raise RollbackUnsafe("ingest_not_off")
    return "TEST_GATEWAY_OFF_STRICT_NO_SECRET"


if __name__ == "__main__":
    raise SystemExit("Safety helper only. No direct deployment or live invocation.")
