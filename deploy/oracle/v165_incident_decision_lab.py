#!/usr/bin/env python3
"""REMURA v1.65 OFFLINE incident decision tree, not a recovery executor.

Only invented evidence is accepted. This module does not inspect a machine,
read real artifacts, execute a rollback, reconcile the updater, contact
providers, or turn any check into release approval. The CLI has just one
fixture mode and does not accept input paths, live flags, or arbitrary JSON.

An operational recovery must be designed and separately authorized after
independent LIVE attestations. All outputs remain NO_GO.
"""
from __future__ import annotations

import argparse
import json

import v165_release_protocol_draft as protocol

SCHEMA = "remura-v165-incident-decision-fixture-v1"
MODE = "OFFLINE_SYNTHETIC_INCIDENT_ONLY"
NO_GO = protocol.NO_GO
PHASES = frozenset((
    "BASELINE", "STAGED", "REPLACING", "CODE_REPLACED",
    "RECONCILED", "RESTORING", "RESTORED", "UNKNOWN",
))
CODES = frozenset(("V164", "V165", "MIXED", "UNKNOWN"))
UPDATERS = frozenset(("V164", "V165", "DIRTY", "UNKNOWN"))
BUNDLES = frozenset(("VERIFIED_FIXTURE", "CORRUPT", "UNKNOWN"))
SQLITES = frozenset(("RESTORED_FIXTURE", "FAILED", "UNKNOWN"))
HEALTHS = frozenset(("HEALTHY_FIXTURE", "FAILED", "UNKNOWN"))
LOCKS = frozenset(("HELD_FIXTURE", "BUSY", "UNKNOWN"))
FIELDS = frozenset((
    "mode", "phase", "code", "updater", "rollbackBundle",
    "sqliteRestore", "health", "lock",
))
REQUIRED_LIVE_EVIDENCE = (
    "independently_attested_v164_live_code_and_updater_sha",
    "exact_installed_12_existing_and_two_new_module_hashes",
    "independent_rollback_manifest_and_bounded_file_integrity",
    "consistent_sqlite_wal_backup_and_isolated_restore_test",
    "offhost_backup_and_recovery_evidence",
    "exclusive_real_autoupdater_lock_and_idle_collector",
    "private_origin_reverse_proxy_and_tailscale_acl_evidence",
    "oracle_billing_eligibility_and_real_disk_inode_measurements",
    "target_main_sha_and_two_real_push_main_ci_checks",
    "real_health_nine_page_rome_timestamp_and_pwa_cache",
    "verified_independent_inverse_reconcile_plan_if_rolled_back",
    "explicit_separate_operator_authorization",
)

# Every rule is a human-review classification, NEVER permission to perform it.
CLASSIFICATIONS = {
    "BASELINE_FIXTURE_ONLY": ("DOCUMENT_CURRENT_STATE", "Preserve v1.64; do not install."),
    "STAGED_FIXTURE_ONLY": ("RECHECK_PRE_FLIGHT", "Prepared files are not a release."),
    "PARTIAL_REPLACEMENT_HALT": ("REVIEW_ROLLBACK_WITH_OPERATOR", "Do not reconcile a partial install."),
    "CANDIDATE_PENDING_RECONCILE": ("REVIEW_SEPARATE_RECONCILIATION", "Candidate files alone do not change updater SHA."),
    "RECONCILED_FIXTURE_ONLY": ("OBSERVE_AND_VERIFY", "Fixture consistency is not production health."),
    "RESTORED_FIXTURE_ONLY": ("REVALIDATE_BASELINE", "Only a fake v1.64 recovery was checked."),
    "INVERSE_RECONCILE_REQUIRED": ("REVIEW_SEPARATE_INVERSE_RECONCILE", "Restored code with target updater SHA is unsafe."),
    "ROLLBACK_INTERRUPTED_HALT": ("MANUAL_RECOVERY_REVIEW", "Do not continue an incomplete recovery automatically."),
    "CORRUPT_ROLLBACK_HALT": ("QUARANTINE_AND_ESCALATE", "Do not use a corrupt backup bundle."),
    "SQLITE_FAILURE_HALT": ("QUARANTINE_AND_ESCALATE", "Do not replace code after restore failure."),
    "LOCK_NOT_ATTESTED_HALT": ("FREEZE_AND_ESCALATE", "Missing or busy lock: no mutation."),
    "UNHEALTHY_HALT": ("FREEZE_AND_ESCALATE", "Do not reconcile while service unhealthy."),
    "UNKNOWN_EVIDENCE_HALT": ("COLLECT_INDEPENDENT_EVIDENCE", "Missing facts are UNKNOWN, never success."),
    "DIRTY_UPDATER_HALT": ("FREEZE_AND_ESCALATE", "Failed/dirty updater state forbids reconciliation."),
    "CONTRADICTORY_HALT": ("FREEZE_AND_ESCALATE", "Observed state does not fit a reviewed transition."),
}


class IncidentFixtureError(ValueError):
    """Invalid fictional evidence, never a production release error."""


def require(ok, code):
    if not ok:
        raise IncidentFixtureError("STOP_" + code)


def fixture(*, phase="BASELINE", code="V164", updater="V164",
            rollbackBundle="VERIFIED_FIXTURE", sqliteRestore="RESTORED_FIXTURE",
            health="HEALTHY_FIXTURE", lock="HELD_FIXTURE"):
    """Construct typed local invented observations, not an API payload."""
    return {
        "mode": MODE, "phase": phase, "code": code,
        "updater": updater, "rollbackBundle": rollbackBundle,
        "sqliteRestore": sqliteRestore, "health": health, "lock": lock,
    }


def classify(observation):
    require(type(observation) is dict and set(observation) == FIELDS,
            "STRICT_FIELDS")
    require(observation["mode"] == MODE, "SYNTHETIC_MODE_ONLY")
    for name, allowed in (
        ("phase", PHASES), ("code", CODES), ("updater", UPDATERS),
        ("rollbackBundle", BUNDLES), ("sqliteRestore", SQLITES),
        ("health", HEALTHS), ("lock", LOCKS),
    ):
        value = observation[name]
        require(type(value) is str and value in allowed, "INVALID_" + name.upper())

    if observation["rollbackBundle"] == "CORRUPT":
        return "CORRUPT_ROLLBACK_HALT"
    if observation["sqliteRestore"] == "FAILED":
        return "SQLITE_FAILURE_HALT"
    if observation["lock"] != "HELD_FIXTURE":
        return "LOCK_NOT_ATTESTED_HALT"
    if observation["health"] == "FAILED":
        return "UNHEALTHY_HALT"
    if any(observation[k] == "UNKNOWN" for k in
           ("rollbackBundle", "sqliteRestore", "health", "code",
            "updater", "phase")):
        return "UNKNOWN_EVIDENCE_HALT"
    if observation["updater"] == "DIRTY":
        return "DIRTY_UPDATER_HALT"

    state = (observation["phase"], observation["code"], observation["updater"])
    known = {
        ("BASELINE", "V164", "V164"): "BASELINE_FIXTURE_ONLY",
        ("STAGED", "V164", "V164"): "STAGED_FIXTURE_ONLY",
        ("REPLACING", "MIXED", "V164"): "PARTIAL_REPLACEMENT_HALT",
        ("CODE_REPLACED", "V165", "V164"): "CANDIDATE_PENDING_RECONCILE",
        ("RECONCILED", "V165", "V165"): "RECONCILED_FIXTURE_ONLY",
        ("RESTORING", "MIXED", "V164"): "ROLLBACK_INTERRUPTED_HALT",
        ("RESTORING", "MIXED", "V165"): "ROLLBACK_INTERRUPTED_HALT",
        ("RESTORED", "V164", "V164"): "RESTORED_FIXTURE_ONLY",
        ("RESTORED", "V164", "V165"): "INVERSE_RECONCILE_REQUIRED",
    }
    return known.get(state, "CONTRADICTORY_HALT")


def decide(observation):
    classification = classify(observation)
    next_gate, explanation = CLASSIFICATIONS[classification]
    return {
        "schema": SCHEMA,
        "state": "OFFLINE_HUMAN_DECISION_TREE_ONLY",
        "classification": classification,
        "humanReviewGate": next_gate,
        "explanation": explanation,
        "requiredIndependentLiveEvidence": list(REQUIRED_LIVE_EVIDENCE),
        "automaticRollbackPermitted": False,
        "automaticReconciliationPermitted": False,
        "realVpsInspected": False,
        "realDatabaseRestored": False,
        "actualOffhostRecoveryVerified": False,
        "actualCIAndLiveShaAttested": False,
        "actualCostsAndAclAttested": False,
        "operatorAuthorized": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }


# Purposefully fixed scenarios: CLI cannot accept arbitrary evidence, paths,
# app credentials or a production action.
SCENARIOS = {
    "baseline": fixture(),
    "staged": fixture(phase="STAGED"),
    "partial_replacement": fixture(phase="REPLACING", code="MIXED"),
    "installed_unreconciled": fixture(phase="CODE_REPLACED", code="V165"),
    "fully_reconciled": fixture(phase="RECONCILED", code="V165", updater="V165"),
    "rollback_partial": fixture(phase="RESTORING", code="MIXED"),
    "rollback_before_reconcile": fixture(phase="RESTORED"),
    "rollback_after_reconcile": fixture(phase="RESTORED", updater="V165"),
    "corrupt_bundle": fixture(rollbackBundle="CORRUPT"),
    "sqlite_failed": fixture(sqliteRestore="FAILED"),
    "updater_busy": fixture(lock="BUSY"),
    "service_failed": fixture(health="FAILED"),
    "unknown_evidence": fixture(code="UNKNOWN"),
    "dirty_updater": fixture(updater="DIRTY"),
    "contradictory": fixture(phase="RECONCILED", code="V164", updater="V165"),
}


def rehearse():
    return {
        "schema": SCHEMA,
        "mode": MODE,
        "scenarios": {key: decide(value) for key, value in SCENARIOS.items()},
        "scenarioCount": len(SCENARIOS),
        "liveActionsAvailable": False,
        "operationalDecision": NO_GO,
    }


def main():
    parser = argparse.ArgumentParser(
        description="v1.65 synthetic incident decision tree ONLY; no LIVE commands")
    parser.add_argument("--decision-fixtures-offline", action="store_true",
                        required=True)
    parser.parse_args()
    print(json.dumps(rehearse(), sort_keys=True))


if __name__ == "__main__":
    main()
