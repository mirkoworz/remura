#!/usr/bin/env python3
# REMURA v0.8.16 — 13/11/2026, ore 13:08 CET
# READ-ONLY D1 PROSPECTIVE PREP: LIVE NOT INVOKED; no tokens/logs/SQL writes.
"""Bounded read-only D1 fetch and REMURA preview. No automatic live invocation.

This module deliberately has NO __main__ entrypoint and is NOT included
in any cloud/GitHub job with Cloudflare secrets. It is only exercised
with mocks. A separate explicit live authorization is required.
"""
from __future__ import annotations

import sys
from pathlib import Path
from urllib.parse import quote

from cloudflare_d1_readonly_audit import (
    AuditError, EXPECTED_JURISDICTION, api_request, require_account_id,
    require_account_token, verify_account_token, UUID_RE,
)

# Add only the local, checked-in parent directory, never user-provided paths.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from remura_tv_bridge_preview_v1 import (  # noqa: E402
    EXPECTED_COLUMNS, MAX_EXPORT_ROWS, preview_export,
)

MAIN_NAME = "remura-tv-lab"
MAX_FETCH = 100
# LIMIT + 1 sentinel prevents a partial page from pretending complete coverage.
READ_SQL = (
    "SELECT event_key, received_at_ms, bar_close_ms, symbol, timeframe, "
    "event_type, version, is_timely, raw_json FROM tv_flow_events "
    "WHERE received_at_ms >= ? AND received_at_ms <= ? "
    "ORDER BY received_at_ms ASC, event_key ASC LIMIT ?"
)


def assert_read_query(sql: str) -> None:
    if sql != READ_SQL or any(
        forbidden in sql.upper() for forbidden in (
            "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH",
            "PRAGMA", "REPLACE", ";", "--", "/*",
        )
    ):
        raise AuditError("query_not_allowlisted")


def find_main_database(payload: object) -> str:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("d1_list_unknown")
    rows = payload.get("result")
    if not isinstance(rows, list):
        raise AuditError("d1_list_invalid")
    matches = [
        r for r in rows if isinstance(r, dict) and r.get("name") == MAIN_NAME
    ]
    if len(matches) != 1 or matches[0].get("jurisdiction") != EXPECTED_JURISDICTION:
        raise AuditError("d1_main_identity_or_jurisdiction_mismatch")
    uuid = matches[0].get("uuid")
    if not isinstance(uuid, str) or not UUID_RE.fullmatch(uuid):
        raise AuditError("d1_main_uuid_invalid")
    return uuid


def parse_select_response(response: object, requested_limit: int) -> list[dict]:
    if type(requested_limit) is not int or not 1 <= requested_limit <= MAX_FETCH:
        raise AuditError("invalid_read_limit")
    if not isinstance(response, dict) or response.get("success") is not True:
        raise AuditError("d1_response_unknown")
    batches = response.get("result")
    if not isinstance(batches, list) or len(batches) != 1:
        raise AuditError("d1_result_batches_invalid")
    batch = batches[0]
    if not isinstance(batch, dict) or batch.get("success") is not True:
        raise AuditError("d1_query_failed")
    records = batch.get("results")
    if not isinstance(records, list):
        raise AuditError("d1_results_invalid")
    if len(records) > requested_limit:
        raise AuditError("d1_response_truncated_not_complete")
    for rec in records:
        if not isinstance(rec, dict) or set(rec) != EXPECTED_COLUMNS:
            raise AuditError("d1_row_columns_invalid")
    return records


def fetch_preview_readonly(account_id: str, token: str, *,
                           start_ms: int, end_ms: int, limit: int = 50,
                           explicit_live_approval: bool = False) -> dict:
    # This guard precedes even account/token verification: no accidental network.
    if explicit_live_approval is not True:
        raise AuditError("live_read_not_authorized")
    if (type(start_ms) is not int or type(end_ms) is not int or
            start_ms <= 1_000_000_000_000 or end_ms <= start_ms or
            end_ms - start_ms > 86_400_000 or
            type(limit) is not int or not 1 <= limit <= MAX_FETCH):
        raise AuditError("query_window_or_limit_invalid")
    assert_read_query(READ_SQL)
    account = quote(require_account_id(account_id), safe="")
    token = require_account_token(token)
    verify_account_token(api_request(
        "GET", f"/accounts/{account}/tokens/verify", token))
    base = f"/accounts/{account}/d1/database"
    uuid = find_main_database(api_request("GET", base + "?name=" + MAIN_NAME, token))
    results = api_request("POST", base + "/" + quote(uuid, safe="") + "/query",
                          token, {"sql": READ_SQL,
                                  "params": [start_ms, end_ms, limit + 1]})
    rows = parse_select_response(results, limit)
    # Full source data remains private; output must be intentionally redacted.
    preview = preview_export(rows)
    if preview["counts"].get("REJECTED_INVALID", 0) or preview[
        "counts"].get("CONFLICTING_DUPLICATE_QUARANTINED", 0):
        raise AuditError("d1_preview_contains_invalid_or_conflicting_events")
    return preview
