# REMURA Cloudflare D1 READ-ONLY Audit v0.1 — aggiornamento 12/11/2026 ore 17:46 CET
# Nessuna operazione SQL di scrittura. Destinazione fissa: remura-tv-lab-test.
# Eseguire SOLO con token Account > D1 > Read; mai usare Global API Key.
"""Minimal Cloudflare D1 REST read-only audit of REMURA synthetic LAB event."""
from __future__ import annotations

import json
import os
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

API_ORIGIN = "https://api.cloudflare.com/client/v4"
EXPECTED_NAME = "remura-tv-lab-test"
EXPECTED_JURISDICTION = "eu"
TEST_KEY = "REMURA_SYNTHETIC_WRITE_20261112"
SQL = (
    "SELECT event_key, symbol, version, is_timely "
    "FROM tv_flow_events WHERE event_key = ? LIMIT 2"
)
ACCOUNT_RE = re.compile(r"^[a-fA-F0-9]{32}$")
UUID_RE = re.compile(r"^[a-fA-F0-9-]{36}$")


class AuditError(Exception):
    """Expected non-sensitive audit failure."""


def require_account_id(account_id: str) -> str:
    if not ACCOUNT_RE.fullmatch(account_id):
        raise AuditError("account_id_missing_or_invalid")
    return account_id


def decode_envelope(payload: object) -> dict:
    if not isinstance(payload, dict) or payload.get("success") is not True:
        raise AuditError("cloudflare_api_not_successful")
    return payload


def find_test_database(payload: object) -> str:
    envelope = decode_envelope(payload)
    rows = envelope.get("result")
    if not isinstance(rows, list):
        raise AuditError("unexpected_database_list")
    matches = [item for item in rows if isinstance(item, dict)
               and item.get("name") == EXPECTED_NAME]
    if len(matches) != 1:
        raise AuditError("expected_exactly_one_test_database")
    match = matches[0]
    if match.get("jurisdiction") != EXPECTED_JURISDICTION:
        raise AuditError("test_database_jurisdiction_not_eu")
    uid = match.get("uuid")
    if not isinstance(uid, str) or not UUID_RE.fullmatch(uid):
        raise AuditError("invalid_test_database_uuid")
    return uid


def inspect_test_record(payload: object) -> str:
    envelope = decode_envelope(payload)
    batches = envelope.get("result")
    if not isinstance(batches, list) or len(batches) != 1:
        raise AuditError("unexpected_d1_query_batches")
    batch = batches[0]
    if not isinstance(batch, dict) or batch.get("success") is not True:
        raise AuditError("d1_query_failed")
    rows = batch.get("results")
    if not isinstance(rows, list):
        raise AuditError("unexpected_d1_query_rows")
    if len(rows) == 0:
        return "record_missing"
    if len(rows) != 1 or not isinstance(rows[0], dict):
        raise AuditError("unexpected_duplicate_or_invalid_record")
    row = rows[0]
    if not (row.get("event_key") == TEST_KEY
            and row.get("symbol") == "LAB:TEST_ONLY"
            and row.get("version") == "synthetic-test-v0.1"
            and row.get("is_timely") == 0):
        raise AuditError("synthetic_record_metadata_mismatch")
    return "record_verified"


def api_request(method: str, path: str, token: str, body: dict | None = None) -> dict:
    if method not in ("GET", "POST"):
        raise AuditError("disallowed_http_method")
    request = Request(
        API_ORIGIN + path,
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": "Bearer " + token,
            "Accept": "application/json",
            **({"Content-Type": "application/json"} if body is not None else {}),
        },
        method=method,
    )
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(200_000)
    except (HTTPError, URLError, TimeoutError) as err:
        # Non includere mai token, response body, URL o headers nei log.
        status = err.code if isinstance(err, HTTPError) else "network"
        raise AuditError(f"cloudflare_http_error_{status}") from None
    try:
        return decode_envelope(json.loads(raw.decode("utf-8")))
    except (UnicodeError, ValueError):
        raise AuditError("invalid_cloudflare_json") from None


def audit(account_id: str, token: str) -> str:
    account = quote(require_account_id(account_id), safe="")
    if not token or len(token) < 16:
        raise AuditError("readonly_token_missing")
    base = f"/accounts/{account}/d1/database"
    # Filtro per nome; non accedere per UUID hardcodato e non usare DB principale.
    listed = api_request("GET", base + "?name=" + EXPECTED_NAME, token)
    test_uuid = find_test_database(listed)
    queried = api_request("POST", base + "/" + quote(test_uuid, safe="") + "/query",
                          token, {"sql": SQL, "params": [TEST_KEY]})
    return inspect_test_record(queried)


def main() -> int:
    try:
        status = audit(os.getenv("REMURA_CF_ACCOUNT_ID", ""),
                       os.getenv("REMURA_CF_D1_READ_TOKEN", ""))
    except AuditError as err:
        print("REMURA_D1_READONLY_AUDIT=ERROR:" + str(err))
        return 1
    print("REMURA_D1_READONLY_AUDIT=" + status)
    print("DATABASE=remura-tv-lab-test; JURISDICTION=EU; HTTP=READ_ONLY; SQL=SELECT")
    return 0 if status == "record_verified" else 2


if __name__ == "__main__":
    sys.exit(main())
