# REMURA Contributors v0.80 LAB — 21/11/2026 17:22 CET
# Synthetic-only parsing of Cloudflare Access GET /accounts/.../access/users pagination.
# NEVER fetches the API, stores user data, accesses GitHub secrets, or authorizes deploy.
"""Audit an already-redacted, in-memory Access users API payload.

The API's access_seat flag means 'has authenticated with Access'. It does NOT
certify current billing seats or the user's actual Zero Trust Free plan. Even
a complete authenticated-user inventory is a planning signal, never a GO.
"""
from __future__ import annotations

from dataclasses import dataclass
from math import ceil
from re import fullmatch
from typing import Any
import json
import sys

MAX_PAGES = 10
MAX_USERS = 1000
FREE_ACCESS_REFERENCE_SEATS = 50
CAUTION_AT_PERCENT = 70
UUID = r"[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}"


class InventoryError(ValueError):
    """Public-safe invariant code only; never includes raw API payloads."""


@dataclass(frozen=True)
class AccessSummary:
    status: str
    user_count: int | None
    authenticated_user_flags: int | None
    reference_free_limit: int
    seats_available: int | None
    exact_billing_attested: bool
    plan_attested: bool
    pages_checked: int
    automatic_deploy_allowed: bool = False

    def public_dict(self) -> dict[str, Any]:
        return {
            "schema": "remura.contributors.access_inventory.v080.lab",
            "version": "0.80",
            "mode": "OFFLINE_FIXTURE_ONLY",
            "status": self.status,
            "users_counted": self.user_count,
            "access_authenticated_flags": self.authenticated_user_flags,
            "free_reference_seats": self.reference_free_limit,
            # Do not infer available purchased/billable seats from login flags.
            "seats_available": None,
            "plan_attested": False,
            "exact_billing_attested": False,
            "pages_checked": self.pages_checked,
            "automatic_deploy_allowed": False,
        }


def _count(x: object, bound: int) -> int:
    if type(x) is not int or x < 0 or x > bound:
        raise InventoryError("invalid_pagination_counter")
    return x


def inspect_access_pages(pages: object) -> AccessSummary:
    if not isinstance(pages, list) or not pages or len(pages) > MAX_PAGES:
        raise InventoryError("pages_missing_or_outside_bounded_inventory")
    seen_users: set[str] = set()
    all_count = flags = 0
    total_ref: int | None = None
    expected_pages: int | None = None
    per_page_ref: int | None = None
    for index, page in enumerate(pages, start=1):
        if not isinstance(page, dict) or page.get("success") is not True or page.get("errors") not in (None, []):
            raise InventoryError("access_api_response_not_success")
        rows, info = page.get("result"), page.get("result_info")
        if not isinstance(rows, list) or not isinstance(info, dict):
            raise InventoryError("missing_access_users_or_pagination")
        current = _count(info.get("page"), MAX_PAGES)
        per_page = _count(info.get("per_page"), MAX_USERS)
        this_count = _count(info.get("count"), MAX_USERS)
        total = _count(info.get("total_count"), MAX_USERS)
        pages_total = _count(info.get("total_pages"), MAX_PAGES)
        if current != index or per_page < 1 or this_count != len(rows) or len(rows) > per_page:
            raise InventoryError("inconsistent_access_page")
        derived = ceil(total / per_page) if total else 1
        if pages_total not in (derived, 0 if total == 0 else -1):
            raise InventoryError("access_pagination_total_invalid")
        if total_ref is not None and (
            total != total_ref or pages_total != expected_pages or per_page != per_page_ref
        ):
            raise InventoryError("access_pagination_changed_mid_read")
        total_ref, expected_pages, per_page_ref = total, pages_total, per_page
        if len(pages) != (pages_total or 1):
            raise InventoryError("access_pagination_incomplete")
        for row in rows:
            if not isinstance(row, dict):
                raise InventoryError("invalid_access_user_record")
            uid = row.get("id")
            active = row.get("access_seat")
            if not isinstance(uid, str) or fullmatch(UUID, uid) is None:
                raise InventoryError("invalid_access_user_identity")
            if uid.lower() in seen_users:
                raise InventoryError("duplicate_access_user")
            seen_users.add(uid.lower())
            if type(active) is not bool:
                raise InventoryError("missing_or_nonboolean_access_seat_flag")
            all_count += 1
            flags += int(active)
    if all_count != total_ref:
        raise InventoryError("access_inventory_count_mismatch")
    if all_count == 0:
        return AccessSummary("EMPTY_NOT_SEAT_ATTESTATION", 0, 0,
                             FREE_ACCESS_REFERENCE_SEATS, None, False, False, len(pages))
    # User flags are only a planning indicator. The billing/plan are unknown.
    status = ("AUTHENTICATED_FLAGS_HIGH_NEEDS_PLAN_REVIEW"
              if flags * 100 >= FREE_ACCESS_REFERENCE_SEATS * CAUTION_AT_PERCENT
              else "INVENTORY_FLAGS_PRESENT_BILLING_UNKNOWN")
    return AccessSummary(status, all_count, flags, FREE_ACCESS_REFERENCE_SEATS,
                         None, False, False, len(pages))


def inventory_summary(pages: object) -> dict[str, Any]:
    """Fail closed; always output no user or account identifiers."""
    try:
        return inspect_access_pages(pages).public_dict()
    except InventoryError:
        return AccessSummary("UNKNOWN_INCOMPLETE_OR_INVALID", None, None,
                             FREE_ACCESS_REFERENCE_SEATS, None, False, False, 0).public_dict()


def main(argv: list[str]) -> int:
    # No path to production API or local user dumps, not even a file path.
    if argv != ["--synthetic-self-check"]:
        print("REMURA_V080_ACCESS=NO_GO")
        return 2
    demo = {"success": True, "errors": [], "result_info": {
        "page": 1, "per_page": 100, "count": 1, "total_count": 1, "total_pages": 1
    }, "result": [{"id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                   "email": "redacted-synthetic@example.invalid", "access_seat": True}]}
    output = inventory_summary([demo])
    assert output["status"] == "INVENTORY_FLAGS_PRESENT_BILLING_UNKNOWN"
    assert output["seats_available"] is None
    assert output["automatic_deploy_allowed"] is False
    message = json.dumps(output, sort_keys=True, separators=(",", ":"))
    if "redacted" in message or "@example" in message:
        raise InventoryError("unsafe_access_summary")
    print(message)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
