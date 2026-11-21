# REMURA Contributors v0.85 LAB — 21/11/2026 Europe/Rome
# Readiness and rollback DRILL only; never touches GitHub, Cloudflare, D1 or Access.
"""Construct a conservative, deterministic staging drill from synthetic evidence.

An offline checklist is not authorization, operational proof, or provider telemetry.
The runbook explicitly excludes deployments, real users, tokens and automatic retry.
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import sys

CHECKS = (
    "PLAN_FREE_OBSERVED",
    "D1_ROWS_TODAY_OBSERVED",
    "D1_STORAGE_OBSERVED",
    "WORKERS_TODAY_OBSERVED",
    "ACCESS_SEATS_OBSERVED",
    "ACCESS_DEFAULT_DENY_REVIEWED",
    "ACCESS_JWT_SERVER_ROLE_REVIEWED",
    "ROUTER_SOURCE_PINNED",
    "D1_FIXTURE_ISOLATION_REVIEWED",
    "ORIGINAL_AND_AMENDMENT_SEPARATED",
    "RESERVED_RECONCILIATION_PROCEDURE_REVIEWED",
    "OWNER_APPEND_ONLY_AUDIT_REVIEWED",
    "SAFARI_REVOCATION_TEST_PLANNED",
    "ROLLBACK_PLAN_REVIEWED",
)
# Ordered, explicit escalation to a human, NOT an execution script.
ROLLBACK = (
    ("STOP_PRIVATE_INTAKE", ()),
    ("DENY_PRIVATE_ACCESS_POLICY", ("STOP_PRIVATE_INTAKE",)),
    ("REVOKE_ACCESS_SESSIONS", ("DENY_PRIVATE_ACCESS_POLICY",)),
    ("FREEZE_D1_FIXTURE_WRITES", ("STOP_PRIVATE_INTAKE",)),
    ("PRESERVE_OWNER_AUDIT_AND_RESERVATIONS", ("FREEZE_D1_FIXTURE_WRITES",)),
    ("WITHDRAW_PRIVATE_ROUTES", ("DENY_PRIVATE_ACCESS_POLICY",)),
    ("VERIFY_DENIAL_FROM_NEW_SESSION", ("REVOKE_ACCESS_SESSIONS","WITHDRAW_PRIVATE_ROUTES")),
    ("VERIFY_NO_AUTO_RESEND_OR_RESERVED_RELEASE", ("PRESERVE_OWNER_AUDIT_AND_RESERVATIONS",)),
    ("OWNER_SIGNOFF_ON_RECONCILIATION", ("VERIFY_DENIAL_FROM_NEW_SESSION","VERIFY_NO_AUTO_RESEND_OR_RESERVED_RELEASE")),
)
ALLOWED = frozenset({"UNKNOWN","DOCUMENTED_OFFLINE","MANUAL_PROVIDER_REVIEW_PENDING"})

class DrillError(ValueError):
    pass

def ensure_plan() -> None:
    known = set()
    if len({step for step,_ in ROLLBACK}) != len(ROLLBACK):
        raise DrillError("duplicate_rollback_step")
    for step,deps in ROLLBACK:
        if not step.isupper() or any(dep not in known for dep in deps):
            raise DrillError("rollback_order_not_safe")
        known.add(step)
    if not {"REVOKE_ACCESS_SESSIONS","FREEZE_D1_FIXTURE_WRITES"}.issubset(known):
        raise DrillError("rollback_incomplete")

def normalize(evidence: object) -> dict[str,object]:
    result: dict[str,object] = {
        "schema":"remura.contributors.staging_drill.v085.lab",
        "version":"0.85",
        "mode":"DOCUMENTATION_REHEARSAL_ONLY",
        "stage":"NO_GO",
        "status":"INVALID_OR_INCOMPLETE",
        "check_count":len(CHECKS),
        "documented_offline":0,
        "pending_manual":list(CHECKS),
        "rollback_step_count":len(ROLLBACK),
        "rollback_order":[name for name,_ in ROLLBACK],
        "actual_provider_evidence_attested":False,
        "runtime_authorized":False,
        "real_users_registered":False,
        "secrets_accessed":False,
        "cloudflare_changes_executed":False,
        "automatic_deploy_allowed":False,
        "automatic_rollback_allowed":False,
        "automatic_retry_or_reserved_release_allowed":False,
    }
    try:
        ensure_plan()
        if not isinstance(evidence,dict) or set(evidence) != set(CHECKS):
            raise DrillError("missing_or_extra_checks")
        if any(type(value) is not str or value not in ALLOWED for value in evidence.values()):
            raise DrillError("unrecognized_check_state")
        result["status"]="OFFLINE_CHECKLIST_REVIEWED_NOT_ATTESTED"
        result["documented_offline"]=sum(x=="DOCUMENTED_OFFLINE" for x in evidence.values())
        result["pending_manual"]=[
            k for k in CHECKS if evidence[k]!="DOCUMENTED_OFFLINE"
        ]
        # No simulated state, including all checkboxes, grants permission to deploy.
    except (DrillError,ValueError,TypeError):
        pass
    return result

def main(argv:list[str])->int:
    if argv != ["--synthetic-rehearsal"]:
        print("REMURA_V085_STAGING_DRILL=NO_GO_BAD_ARGUMENTS")
        return 2
    report=normalize({k:"DOCUMENTED_OFFLINE" for k in CHECKS})
    if report["status"]!="OFFLINE_CHECKLIST_REVIEWED_NOT_ATTESTED":
        print("REMURA_V085_STAGING_DRILL=INVALID")
        return 3
    print(json.dumps(report,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
