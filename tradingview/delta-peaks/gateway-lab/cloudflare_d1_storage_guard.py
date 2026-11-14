# REMURA D1 STORAGE GUARD v0.1 — aggiornamento 13/11/2026, ore 06:44 CET
# Solo GET metadata Cloudflare D1 TEST, mai DB prospettico; nessun SQL o write.
"""Check actual free-tier storage for the isolated EU TEST D1 via an account D1 Read token.

Requires the existing REMURA_CF_D1_READ_TOKEN and REMURA_CF_ACCOUNT_ID
GitHub Secrets. The main D1 is never queried or inspected.
"""
from __future__ import annotations

import os
import sys
from urllib.parse import quote

from cloudflare_d1_readonly_audit import (
    AuditError, EXPECTED_NAME, EXPECTED_JURISDICTION,
    api_request, find_test_database, require_account_id, require_account_token,
    verify_account_token,
)

# Official Cloudflare Workers Free D1 limits; not an account-usage counter.
DB_FREE_LIMIT_BYTES = 500_000_000
WARN_THRESHOLD_PERCENT = 70
CRITICAL_THRESHOLD_PERCENT = 90


def inspect_database_metadata(payload: object, uuid: str) -> int:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("d1_storage_api_not_success")
    item = payload.get("result")
    if not isinstance(item, dict):
        raise AuditError("d1_storage_metadata_missing")
    if (item.get("name") != EXPECTED_NAME
            or item.get("jurisdiction") != EXPECTED_JURISDICTION
            or item.get("uuid") != uuid):
        raise AuditError("d1_storage_identity_mismatch")
    size = item.get("file_size")
    if type(size) is not int or size < 0:
        raise AuditError("d1_storage_size_missing_or_invalid")
    return size


def assess_storage(size: int) -> str:
    if type(size) is not int or size < 0:
        raise AuditError("invalid_storage_size")
    if size * 100 >= DB_FREE_LIMIT_BYTES * CRITICAL_THRESHOLD_PERCENT:
        return "CRITICAL"
    if size * 100 >= DB_FREE_LIMIT_BYTES * WARN_THRESHOLD_PERCENT:
        return "WARNING"
    return "OK"


def fetch_test_storage(account_id: str, token: str) -> tuple[int, str]:
    account_id = require_account_id(account_id)
    token = require_account_token(token)
    account = quote(account_id, safe="")
    verified = api_request("GET", f"/accounts/{account}/tokens/verify", token)
    verify_account_token(verified)
    base = f"/accounts/{account}/d1/database"
    listed = api_request("GET", base + "?name=" + EXPECTED_NAME, token)
    uuid = find_test_database(listed)
    metadata = api_request("GET", base + "/" + quote(uuid, safe=""), token)
    size = inspect_database_metadata(metadata, uuid)
    return size, assess_storage(size)


def main() -> int:
    try:
        size, status = fetch_test_storage(
            os.getenv("REMURA_CF_ACCOUNT_ID", ""),
            os.getenv("REMURA_CF_D1_READ_TOKEN", ""),
        )
    except AuditError as error:
        print("REMURA_D1_TEST_STORAGE=UNKNOWN:" + str(error))
        return 1
    print("REMURA_D1_TEST_STORAGE=" + status)
    print("REMURA_D1_TEST_STORAGE_BYTES=" + str(size))
    print("REMURA_D1_TEST_STORAGE_LIMIT_BYTES=" + str(DB_FREE_LIMIT_BYTES))
    print("REMURA_D1_TEST_STORAGE_PERCENT=" +
          format(100 * size / DB_FREE_LIMIT_BYTES, ".4f"))
    print("REMURA_D1_TEST_ONLY=TRUE; READ_ONLY=TRUE; ACCOUNT_DAILY_QUOTAS=NOT_MEASURED")
    return 2 if status == "CRITICAL" else 0


if __name__ == "__main__":
    sys.exit(main())
