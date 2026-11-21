# REMURA Contributors v0.82 LAB — 21/11/2026 Europe/Rome
"""Offline staging gate coverage and role-boundary matrix (NEVER a deploy decision).

Values supplied by a caller are not authenticated. Even a fully "passed" matrix
can never trigger a real deploy, a retry, a RESERVED release or a publication.
"""
from __future__ import annotations
import json
import sys
from route_manifest_v081_lab import review, ManifestError

GATES = (
    "CF_FREE_PLAN",
    "D1_DAILY_READS_WRITES_CURRENT",
    "D1_STORAGE_MARGIN",
    "WORKERS_DAILY_REQUEST_MARGIN",
    "ACCESS_BILLABLE_SEATS_CURRENT",
    "ACCESS_ALLOWLIST_DENY_DEFAULT",
    "ACCESS_JWT_AND_ROLE_CHECK",
    "SAME_ORIGIN_PRIVATE_ASSETS",
    "D1_FIXTURE_ISOLATED",
    "SAFARI_REAL_LOGIN_LOGOUT_REVOKE",
    "ORIGINAL_AMENDMENT_SEPARATE",
    "RESERVED_NO_AUTO_RETRY_OR_RELEASE",
    "OWNER_APPROVAL_APPEND_ONLY",
    "ROLLBACK_VERIFIED",
)
STATES = frozenset({"UNKNOWN", "LAB_ONLY", "MANUAL_REVIEW_REQUIRED"})
ROLE_ACTIONS = {
    "CONTRIBUTOR": ("read_general_remura", "propose_own_original_level", "propose_own_amendment", "read_own_receipts"),
    "OWNER": ("read_general_remura", "review_proposed_levels", "review_amendments", "append_owner_audit"),
}
DENIED_ACTIONS = (
    "write_other_member_levels", "auto_approve", "auto_retry_lost_response",
    "release_reserved_automatically", "publish_telegram_unapproved",
)
class MatrixError(ValueError):
    pass

def check_matrix(states: object, *, verify_routes: bool = True) -> dict[str, object]:
    reasons = []
    if not isinstance(states, dict) or set(states) != set(GATES):
        reasons.append("MISSING_OR_EXTRA_GATES")
        safe = {k: "UNKNOWN" for k in GATES}
    else:
        safe = {}
        for k in GATES:
            if type(states[k]) is not str or states[k] not in STATES:
                reasons.append("INVALID_GATE_STATE")
                safe[k] = "UNKNOWN"
            else:
                safe[k] = states[k]
    if not verify_routes:
        reasons.append("ROUTE_MANIFEST_NOT_CHECKED")
        manifest = "NOT_CHECKED"
    else:
        try:
            contract = review()
            manifest = "SOURCE_LOCK_MATCH" if contract.get("source_status") == "PINNED_GIT_BLOBS_MATCH" else "DRIFT"
            if manifest != "SOURCE_LOCK_MATCH":
                reasons.append("ROUTE_MANIFEST_DRIFT")
        except (ManifestError, OSError, ValueError):
            manifest = "DRIFT"
            reasons.append("ROUTE_MANIFEST_DRIFT")
    unknown = tuple(k for k in GATES if safe[k] == "UNKNOWN")
    reasons.extend("PENDING_" + name for name in unknown)
    if not reasons:
        reasons.append("OFFLINE_EVIDENCE_CANNOT_AUTHORIZE_STAGING")
    return {
        "schema": "remura.contributors.staging_matrix.v082.lab",
        "version": "0.82",
        "gate_count": len(GATES),
        "unknown_gates": list(unknown),
        "route_manifest": manifest,
        "role_action_counts": {role: len(actions) for role, actions in ROLE_ACTIONS.items()},
        "globally_forbidden_actions": list(DENIED_ACTIONS),
        "reasons": sorted(set(reasons)),
        "input_attested": False,
        "provider_attested": False,
        "automatic_deploy_allowed": False,
        "decision": "NO_GO",
    }

def main(argv: list[str]) -> int:
    if argv != ["--offline-review"]:
        print("REMURA_V082_MATRIX=NO_GO_BAD_ARGUMENTS")
        return 2
    print(json.dumps(check_matrix({k: "UNKNOWN" for k in GATES}), sort_keys=True))
    return 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
