# REMURA Worker PUBLIC FAIL-CLOSED AUDIT v0.2 — 13/11/2026 ore 06:52 CET
# Solo 2 GET senza credenziali: /health e /, MAI POST /ingest né token URL.
"""Read-only verification that the deployed public TV LAB Worker remains disabled."""
from __future__ import annotations

import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import HTTPRedirectHandler, Request, build_opener

BASE = "https://remura-tv-ingest-lab.mirkoworz.workers.dev"
ALLOWED_PATHS = frozenset(("/health", "/"))
MAX_RESPONSE_BYTES = 2048


class GatewayNotSafe(Exception):
    """The public gateway is not verifiably fail-closed."""


class DenyRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_public(path: str, opener=None) -> tuple[int, dict]:
    if path not in ALLOWED_PATHS:
        raise GatewayNotSafe("disallowed_probe_path")
    opener = opener or build_opener(DenyRedirects)
    request = Request(BASE + path, method="GET",
                      headers={"Accept": "application/json", "Cache-Control": "no-cache"})
    try:
        with opener.open(request, timeout=10) as response:
            status = response.status
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as error:
        status = error.code
        raw = error.read(MAX_RESPONSE_BYTES + 1)
    except (URLError, TimeoutError):
        raise GatewayNotSafe("public_gateway_unreachable") from None
    if len(raw) > MAX_RESPONSE_BYTES:
        raise GatewayNotSafe("response_too_large")
    try:
        body = json.loads(raw)
    except (ValueError, UnicodeError):
        raise GatewayNotSafe("invalid_json") from None
    if not isinstance(body, dict):
        raise GatewayNotSafe("invalid_response_structure")
    return status, body


def validate_failclosed(health: tuple[int, dict], root: tuple[int, dict]) -> None:
    health_code, health_body = health
    root_code, root_body = root
    if (health_code != 200 or health_body.get("status") != "lab_only"
            or health_body.get("accepting") is not False):
        raise GatewayNotSafe("health_not_failclosed")
    if root_code != 503 or root_body.get("status") != "disabled":
        raise GatewayNotSafe("root_not_disabled")


def main() -> int:
    try:
        health = fetch_public("/health")
        root = fetch_public("/")
        health_code, health_body = health
        root_code, root_body = root
        # Sanitized diagnostics only: never print raw Cloudflare body.
        health_status = health_body.get("status")
        root_status = root_body.get("status")
        health_flag = health_body.get("accepting")
        print("REMURA_PUBLIC_HEALTH_HTTP=" + str(health_code))
        print("REMURA_PUBLIC_HEALTH_STATUS=" +
              (health_status if health_status in ("lab_only", "disabled", "not_found")
               else "UNEXPECTED"))
        print("REMURA_PUBLIC_HEALTH_ACCEPTING=" +
              ("true" if health_flag is True else
               "false" if health_flag is False else "UNKNOWN"))
        print("REMURA_PUBLIC_ROOT_HTTP=" + str(root_code))
        print("REMURA_PUBLIC_ROOT_STATUS=" +
              (root_status if root_status in ("lab_only", "disabled", "not_found")
               else "UNEXPECTED"))
        validate_failclosed(health, root)
    except GatewayNotSafe as error:
        print("REMURA_TV_PUBLIC_FAILCLOSED=ERROR:" + str(error))
        return 1
    print("REMURA_TV_PUBLIC_FAILCLOSED=VERIFIED")
    print("HEALTH=lab_only; ACCEPTING=false; ROOT=disabled; HTTP_METHOD=GET; INGEST_POST=NOT_ATTEMPTED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
