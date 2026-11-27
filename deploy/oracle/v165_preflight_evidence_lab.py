#!/usr/bin/env python3
"""REMURA v1.65: public-safe, OFFLINE evidence-plan *schema* only.

This module does not collect, parse, attach, attest, upload or store any
real-world evidence. Its 12 exact slots correspond to the recovery decision
tree. Live proofs must later be collected in an independently authorized,
private and reviewed workflow, which is NOT implemented here.

Any input record marked REAL/VERIFIED, or containing paths, URLs, secrets,
raw responses, credentials, timestamps or other unreviewed fields is rejected.
Even 12/12 mocked receipts NEVER grant permission or prove actual readiness.
No files, network, services, SQLite, environment variables or cost APIs read.
"""
from __future__ import annotations

import argparse
import json

import v165_incident_decision_lab as incident

SCHEMA = "remura-v165-preflight-evidence-plan-offline-v1"
MODE = "OFFLINE_EVIDENCE_PLAN_FIXTURES_ONLY"
NO_GO = incident.NO_GO
MISSING = "ABSENT"
MOCK = "SYNTHETIC_RECEIPT_ONLY"
SLOT_FIELDS = frozenset(("gateId", "fixtureReceipt"))
CAPTURE_CLASSES = frozenset((
    "FUTURE_READ_ONLY_ATTESTATION",
    "FUTURE_CONTROLLED_WRITE_AND_RESTORE",
    "FUTURE_EXTERNAL_BILLING_ATTESTATION",
    "FUTURE_RELEASE_TIME_VERIFICATION",
    "FUTURE_OPERATOR_AUTHORIZATION",
))
CUSTODY = frozenset(("PRIVATE_OPERATOR_REVIEW", "PRIVATE_DIAGNOSTIC_EVIDENCE"))
GATES = (
    ("independently_attested_v164_live_code_and_updater_sha",
     "FUTURE_READ_ONLY_ATTESTATION", "PRIVATE_DIAGNOSTIC_EVIDENCE",
     "Correlate actual installed code identity and updater installedSha; GitHub main alone is insufficient."),
    ("exact_installed_12_existing_and_two_new_module_hashes",
     "FUTURE_READ_ONLY_ATTESTATION", "PRIVATE_DIAGNOSTIC_EVIDENCE",
     "Compare approved old file inventory and candidate 12+2 hashes; no symlink, extra or missing entries."),
    ("independent_rollback_manifest_and_bounded_file_integrity",
     "FUTURE_CONTROLLED_WRITE_AND_RESTORE", "PRIVATE_OPERATOR_REVIEW",
     "Prepare independently verified sealed rollback copies before service change; demonstrate integrity and recovery."),
    ("consistent_sqlite_wal_backup_and_isolated_restore_test",
     "FUTURE_CONTROLLED_WRITE_AND_RESTORE", "PRIVATE_OPERATOR_REVIEW",
     "Use consistent SQLite backup API, isolated restore, integrity/schema checks; never assume hot copy of WAL works."),
    ("offhost_backup_and_recovery_evidence",
     "FUTURE_CONTROLLED_WRITE_AND_RESTORE", "PRIVATE_OPERATOR_REVIEW",
     "Demonstrate encrypted authorized external recovery with actual independent restore; same-runner fixture is insufficient."),
    ("exclusive_real_autoupdater_lock_and_idle_collector",
     "FUTURE_CONTROLLED_WRITE_AND_RESTORE", "PRIVATE_OPERATOR_REVIEW",
     "Verify and coordinate the real exclusive update lock, paused operations and single operator; requires separate consent."),
    ("private_origin_reverse_proxy_and_tailscale_acl_evidence",
     "FUTURE_READ_ONLY_ATTESTATION", "PRIVATE_DIAGNOSTIC_EVIDENCE",
     "Independently review 127.0.0.1 origin, reverse proxy, tailnet tag/ACL and effective non-public access."),
    ("oracle_billing_eligibility_and_real_disk_inode_measurements",
     "FUTURE_EXTERNAL_BILLING_ATTESTATION", "PRIVATE_OPERATOR_REVIEW",
     "Review post-trial Oracle billing/Always Free eligibility and quotas, then actual disk/inode measurements."),
    ("target_main_sha_and_two_real_push_main_ci_checks",
     "FUTURE_READ_ONLY_ATTESTATION", "PRIVATE_OPERATOR_REVIEW",
     "Require pinned main target, two distinct successful push/main workflows, and recheck main HEAD under lock."),
    ("real_health_nine_page_rome_timestamp_and_pwa_cache",
     "FUTURE_RELEASE_TIME_VERIFICATION", "PRIVATE_OPERATOR_REVIEW",
     "After a separately authorized release verify health, all nine live top banners, real Europe/Rome timestamp and SW cache."),
    ("verified_independent_inverse_reconcile_plan_if_rolled_back",
     "FUTURE_CONTROLLED_WRITE_AND_RESTORE", "PRIVATE_OPERATOR_REVIEW",
     "If rolled back after SHA reconciliation, verify a separate authorized inverse recovery; never silently edit updater state."),
    ("explicit_separate_operator_authorization",
     "FUTURE_OPERATOR_AUTHORIZATION", "PRIVATE_OPERATOR_REVIEW",
     "Record distinct authorized operator decision for production changes; fixture receipt is not approval."),
)
PUBLIC_REPORT_FIELDS = frozenset((
    "schema", "state", "gateCount", "gates",
    "missingRealEvidenceCount", "syntheticReceiptCount",
    "containsRealEvidence", "containsPrivateValues", "actualCostsAttested",
    "actualBackupRestored", "actualLiveShaVerified", "releaseAuthorized",
    "vpsContacted", "readOnlyVpsChecksPerformed",
    "productionWritesPerformed", "researchC5Enabled",
    "operationalDecision",
))


class EvidencePlanError(ValueError):
    """Offline-only contract rejection; never a real provider error."""


def require(ok, reason):
    if not ok:
        raise EvidencePlanError("STOP_" + reason)


def validate_plan():
    ids = tuple(item[0] for item in GATES)
    require(ids == incident.REQUIRED_LIVE_EVIDENCE, "GATE_DRIFT")
    require(len(ids) == 12 and len(set(ids)) == 12, "DUPLICATE_GATES")
    require(all(
        type(name) is str and type(klass) is str and
        klass in CAPTURE_CLASSES and custody in CUSTODY and
        type(reason) is str and 20 <= len(reason) <= 210
        for name, klass, custody, reason in GATES
    ), "INVALID_GATE_SPEC")
    return True


def fixtures(*, simulated_gates=()):
    """Produce only fixed-form synthetic receipts; not collected evidence."""
    validate_plan()
    require(type(simulated_gates) in (list, tuple, frozenset),
            "INVALID_FIXTURE_IDS")
    require(all(type(v) is str for v in simulated_gates),
            "INVALID_FIXTURE_IDS")
    values = tuple(simulated_gates)
    require(len(values) == len(set(values)) and
            set(values).issubset(incident.REQUIRED_LIVE_EVIDENCE),
            "UNKNOWN_OR_DUPLICATE_FIXTURE_ID")
    sample = set(values)
    return [
        {"gateId": gate[0], "fixtureReceipt": MOCK if gate[0] in sample else MISSING}
        for gate in GATES
    ]


def evaluate_only_fixture_rows(rows):
    """Strictly refuse any REAL proof/value. Never emits success/GO."""
    validate_plan()
    require(type(rows) in (list, tuple) and len(rows) == len(GATES),
            "EXACT_ROW_COUNT")
    allowed_ids = tuple(x[0] for x in GATES)
    received = []
    mock_count = 0
    for row in rows:
        require(type(row) is dict and set(row) == SLOT_FIELDS,
                "STRICT_PUBLIC_FIXTURE_FIELDS")
        gate_id, state = row["gateId"], row["fixtureReceipt"]
        require(type(gate_id) is str and gate_id in allowed_ids,
                "INVALID_GATE_ID")
        require(type(state) is str and state in (MISSING, MOCK),
                "REAL_EVIDENCE_NOT_ACCEPTED")
        received.append(gate_id)
        mock_count += state == MOCK
    require(tuple(received) == allowed_ids, "GATE_ORDER_OR_DUPLICATE")
    gates = [
        {
            "gateId": gate[0],
            "plannedCaptureClass": gate[1],
            "plannedFutureCustody": gate[2],
            "humanReviewCriterion": gate[3],
            "actualRealEvidenceState": "NOT_ATTESTED",
            "syntheticFixtureReceiptPresent": rows[i]["fixtureReceipt"] == MOCK,
            "separateOperatorAuthorizationRequired": True,
            "publicEvidenceUploadPermitted": False,
        }
        for i, gate in enumerate(GATES)
    ]
    report = {
        "schema": SCHEMA,
        "state": "PUBLIC_SAFE_PLAN_ONLY_NO_EVIDENCE_COLLECTED",
        "gateCount": len(GATES),
        "gates": gates,
        "missingRealEvidenceCount": len(GATES),
        "syntheticReceiptCount": mock_count,
        "containsRealEvidence": False,
        "containsPrivateValues": False,
        "actualCostsAttested": False,
        "actualBackupRestored": False,
        "actualLiveShaVerified": False,
        "releaseAuthorized": False,
        "vpsContacted": False,
        "readOnlyVpsChecksPerformed": False,
        "productionWritesPerformed": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }
    require(set(report) == PUBLIC_REPORT_FIELDS, "REPORT_SCHEMA_CHANGED")
    return report


def plan():
    return evaluate_only_fixture_rows(fixtures())


def main():
    parser = argparse.ArgumentParser(
        description="REMURA v1.65 public-safe OFFLINE evidence schema only")
    parser.add_argument("--plan-evidence-offline", action="store_true",
                        required=True)
    parser.parse_args()
    print(json.dumps(plan(), sort_keys=True))


if __name__ == "__main__":
    main()
