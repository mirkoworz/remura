# REMURA D1 ACCOUNT STORAGE GUARD v0.8.14 — 13/11/2026, ore 11:56 CET
# GET-only, account D1 Read; non legge tabelle, non modifica database o Worker.
"""Inventory account D1 file sizes. Partial, missing or conflicting metadata is UNKNOWN.

Cloudflare file_size is a metadata snapshot, not an exact billing counter.
The first-page bound is intentional: an account outside Free-sized inventory
must never be misreported as fully audited.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import quote

from cloudflare_d1_readonly_audit import (
    AuditError, EXPECTED_NAME, EXPECTED_JURISDICTION, UUID_RE,
    api_request, require_account_id, require_account_token, verify_account_token,
)

MAIN_DB_NAME = "remura-tv-lab"
FREE_ACCOUNT_BYTES = 5_000_000_000
FREE_SINGLE_DB_BYTES = 500_000_000
FREE_DATABASE_COUNT = 10
WARNING_PERCENT = 70
CRITICAL_PERCENT = 90
MAX_LIST_ITEMS = 100


def parse_inventory(payload: object) -> list[tuple[str, str, str | None]]:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("d1_inventory_unavailable")
    rows, info = payload.get("result"), payload.get("result_info")
    if not isinstance(rows, list) or not isinstance(info, dict):
        raise AuditError("d1_inventory_pagination_unknown")
    if not all(type(info.get(k)) is int for k in
               ("page", "per_page", "count", "total_count")):
        raise AuditError("d1_inventory_pagination_invalid")
    if (info["page"] != 1 or not 10 <= info["per_page"] <= 10_000
            or not 0 < len(rows) <= MAX_LIST_ITEMS
            or info["count"] != len(rows)
            or info["total_count"] != len(rows)):
        raise AuditError("d1_inventory_incomplete_or_outside_free")
    seen_names, seen_uuids = set(), set()
    parsed = []
    for row in rows:
        if not isinstance(row, dict):
            raise AuditError("d1_inventory_invalid_row")
        name, uid, jurisdiction = row.get("name"), row.get("uuid"), row.get("jurisdiction")
        if (not isinstance(name, str) or not name
                or not isinstance(uid, str) or not UUID_RE.fullmatch(uid)
                or name in seen_names or uid in seen_uuids):
            raise AuditError("d1_inventory_invalid_identity")
        if name in (MAIN_DB_NAME, EXPECTED_NAME) and jurisdiction != EXPECTED_JURISDICTION:
            raise AuditError("remura_database_jurisdiction_mismatch")
        seen_names.add(name)
        seen_uuids.add(uid)
        parsed.append((name, uid, jurisdiction))
    if not {MAIN_DB_NAME, EXPECTED_NAME}.issubset(seen_names):
        raise AuditError("remura_databases_not_both_present")
    return parsed


def read_db_size(payload: object, name: str, uid: str, jurisdiction: str | None) -> int:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("d1_account_metadata_unavailable")
    item = payload.get("result")
    if not isinstance(item, dict) or any(
        item.get(k) != v for k, v in
        (("name", name), ("uuid", uid), ("jurisdiction", jurisdiction))
    ):
        raise AuditError("d1_account_metadata_identity_mismatch")
    size = item.get("file_size")
    if type(size) is not int or size < 0:
        raise AuditError("d1_account_file_size_unknown")
    return size


def assessment(database_count: int, total_bytes: int, largest_bytes: int) -> str:
    if any(type(v) is not int or v < 0 for v in
           (database_count, total_bytes, largest_bytes)) or database_count < 1:
        raise AuditError("d1_account_invalid_metrics")
    metrics = (
        (database_count, FREE_DATABASE_COUNT),
        (total_bytes, FREE_ACCOUNT_BYTES),
        (largest_bytes, FREE_SINGLE_DB_BYTES),
    )
    if any(value * 100 >= limit * CRITICAL_PERCENT for value, limit in metrics):
        return "CRITICAL"
    if any(value * 100 >= limit * WARNING_PERCENT for value, limit in metrics):
        return "WARNING"
    return "OK"


def fetch_account_storage(account_id: str, token: str) -> dict:
    account = quote(require_account_id(account_id), safe="")
    token = require_account_token(token)
    verify_account_token(api_request("GET", f"/accounts/{account}/tokens/verify", token))
    base = f"/accounts/{account}/d1/database"
    inventory = parse_inventory(api_request(
        "GET", base + "?page=1&per_page=100", token))
    sizes = []
    for name, uid, jurisdiction in inventory:
        meta = api_request("GET", base + "/" + quote(uid, safe=""), token)
        sizes.append(read_db_size(meta, name, uid, jurisdiction))
    total, maximum = sum(sizes), max(sizes)
    return {"count": len(inventory), "bytes": total, "largest": maximum,
            "status": assessment(len(inventory), total, maximum)}


def main() -> int:
    try:
        stats = fetch_account_storage(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
        )
    except AuditError as exc:
        print("REMURA_D1_ACCOUNT_STORAGE=UNKNOWN:" + str(exc))
        return 1
    print("REMURA_D1_ACCOUNT_STORAGE=" + stats["status"])
    print("D1_ACCOUNT_DATABASE_COUNT=" + str(stats["count"]))
    print("D1_ACCOUNT_STORAGE_BYTES=" + str(stats["bytes"]))
    print("D1_ACCOUNT_LARGEST_DB_BYTES=" + str(stats["largest"]))
    print("D1_ACCOUNT_FREE_STORAGE_LIMIT_BYTES=" + str(FREE_ACCOUNT_BYTES))
    print("D1_ACCOUNT_FREE_SINGLE_DB_LIMIT_BYTES=" + str(FREE_SINGLE_DB_BYTES))
    print("D1_ACCOUNT_FREE_DB_COUNT_LIMIT=" + str(FREE_DATABASE_COUNT))
    print("D1_ACCOUNT_SOURCE=GET_METADATA_ONLY; NOT_EXACT_BILLING")
    return 2 if stats["status"] == "CRITICAL" else 0


if __name__ == "__main__":
    sys.exit(main())
