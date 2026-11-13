#!/usr/bin/env python3
"""REMURA v1.65: pure OFFLINE read-only preflight calculation on invented data.

This is NOT a collector, server probe, disk scanner or release gate. All
inputs must be explicitly tagged synthetic. No host paths, external
responses, URLs, services, SQLite, credential inspection or billing APIs are
accepted. It ONLY computes a conservative *mock* capacity and consistency
classification. Even a plausible result is always NO_GO for LIVE and C5.
"""
from __future__ import annotations

import argparse
import json

import v165_preflight_evidence_lab as evidence
import v165_release_protocol_draft as protocol

SCHEMA = "remura-v165-readonly-preflight-fixture-v1"
MODE = "OFFLINE_READONLY_PREFLIGHT_FIXTURE_ONLY"
NO_GO = protocol.NO_GO
MIB = 1024 ** 2
GIB = 1024 ** 3
MAX_META_AGE_SECONDS = 300
MAX_DATA_BYTES = 8 * GIB
MAX_CANDIDATE_BYTES = 512 * MIB
MAX_FREE_BYTES = 64 * 1024 ** 4
MAX_INODES = 10 ** 10
REQUIRED_FREE_INODES = 256
FIXTURE_FIELDS = frozenset((
    "mode", "fakeInstalled", "fakeUpdater", "fakeIngress",
    "fakeBilling", "fakeCi", "metadataAgeSeconds", "sizes",
))
SIZE_FIELDS = frozenset((
    "dbBytes", "walBytes", "shmBytes", "candidateBytes",
    "freeBytes", "freeInodes",
))
IDENTITIES = frozenset(("FAKE_V164_MATCH", "FAKE_MISMATCH", "UNKNOWN"))
INGRESS = frozenset(("FAKE_PRIVATE", "FAKE_PUBLIC", "UNKNOWN"))
BILLING = frozenset(("FAKE_ALWAYS_FREE", "FAKE_BILLING_RISK", "UNKNOWN"))
CI = frozenset(("FAKE_PUSH_MAIN_BOTH_GREEN", "FAKE_CI_UNVERIFIED", "UNKNOWN"))


class MockPreflightError(ValueError):
    """Synthetic schema error only, not production monitoring evidence."""


def require(ok, reason):
    if not ok:
        raise MockPreflightError("STOP_" + reason)


def fake_snapshot():
    """Entirely fabricated bounded numbers; not a measurement of Oracle."""
    return {
        "mode": MODE,
        "fakeInstalled": "FAKE_V164_MATCH",
        "fakeUpdater": "FAKE_V164_MATCH",
        "fakeIngress": "FAKE_PRIVATE",
        "fakeBilling": "FAKE_ALWAYS_FREE",
        "fakeCi": "FAKE_PUSH_MAIN_BOTH_GREEN",
        "metadataAgeSeconds": 20,
        "sizes": {
            "dbBytes": 16 * MIB, "walBytes": 2 * MIB,
            "shmBytes": 1 * MIB, "candidateBytes": 2 * MIB,
            "freeBytes": 4 * GIB, "freeInodes": 4096,
        },
    }


def _bounded_int(value, *, maximum, allow_zero=True):
    if value is None:
        return None
    require(type(value) is int and 0 <= value <= maximum
            and (allow_zero or value > 0), "INVALID_BOUNDED_NUMBER")
    return value


def validate_snapshot(snapshot):
    require(type(snapshot) is dict and set(snapshot) == FIXTURE_FIELDS,
            "STRICT_FIXTURE_FIELDS")
    require(snapshot["mode"] == MODE, "OFFLINE_FIXTURE_ONLY")
    for field, values in (("fakeInstalled", IDENTITIES),
                          ("fakeUpdater", IDENTITIES),
                          ("fakeIngress", INGRESS),
                          ("fakeBilling", BILLING), ("fakeCi", CI)):
        require(type(snapshot[field]) is str and snapshot[field] in values,
                "INVALID_" + field.upper())
    age = _bounded_int(snapshot["metadataAgeSeconds"], maximum=86400)
    require(type(snapshot["sizes"]) is dict and
            set(snapshot["sizes"]) == SIZE_FIELDS, "STRICT_SIZE_FIELDS")
    size = snapshot["sizes"]
    bounded = {
        "dbBytes": _bounded_int(size["dbBytes"],
                               maximum=MAX_DATA_BYTES, allow_zero=False),
        "walBytes": _bounded_int(size["walBytes"], maximum=MAX_DATA_BYTES),
        "shmBytes": _bounded_int(size["shmBytes"], maximum=MAX_DATA_BYTES),
        "candidateBytes": _bounded_int(size["candidateBytes"],
                                      maximum=MAX_CANDIDATE_BYTES,
                                      allow_zero=False),
        "freeBytes": _bounded_int(size["freeBytes"], maximum=MAX_FREE_BYTES),
        "freeInodes": _bounded_int(size["freeInodes"], maximum=MAX_INODES),
    }
    return age, bounded


def assess_mock(snapshot):
    """Pure arithmetic + priority classification; NEVER returns GO."""
    age, sizes = validate_snapshot(snapshot)
    missing = age is None or any(v is None for v in sizes.values())
    reserve = None
    disk_enough = False
    inode_enough = False
    if not missing:
        reserve = (4 * (sizes["dbBytes"] + sizes["walBytes"]
                        + sizes["shmBytes"])
                   + 3 * sizes["candidateBytes"] + 512 * MIB)
        disk_enough = sizes["freeBytes"] > reserve
        inode_enough = sizes["freeInodes"] >= REQUIRED_FREE_INODES
    elif all(sizes[k] is not None for k in
             ("dbBytes", "walBytes", "shmBytes", "candidateBytes")):
        reserve = (4 * (sizes["dbBytes"] + sizes["walBytes"]
                        + sizes["shmBytes"])
                   + 3 * sizes["candidateBytes"] + 512 * MIB)

    if (snapshot["fakeInstalled"] == "FAKE_MISMATCH" or
            snapshot["fakeUpdater"] == "FAKE_MISMATCH"):
        classification = "STOP_FAKE_SHA_MISMATCH"
    elif snapshot["fakeIngress"] == "FAKE_PUBLIC":
        classification = "STOP_FAKE_PUBLIC_INGRESS"
    elif snapshot["fakeBilling"] == "FAKE_BILLING_RISK":
        classification = "STOP_FAKE_BILLING_RISK"
    elif snapshot["fakeCi"] == "FAKE_CI_UNVERIFIED":
        classification = "STOP_FAKE_CI_UNVERIFIED"
    elif missing or any(snapshot[k] == "UNKNOWN" for k in
                        ("fakeInstalled", "fakeUpdater",
                         "fakeIngress", "fakeBilling", "fakeCi")):
        classification = "UNKNOWN_NO_REAL_EVIDENCE"
    elif age > MAX_META_AGE_SECONDS:
        classification = "STOP_FAKE_METADATA_STALE"
    elif not disk_enough:
        classification = "STOP_FAKE_DISK_HEADROOM"
    elif not inode_enough:
        classification = "STOP_FAKE_INODE_HEADROOM"
    else:
        classification = "MOCK_CAPACITY_PLAUSIBLE_NOT_LIVE_PROOF"

    gates = evidence.plan()
    require(gates["gateCount"] == 12 and
            gates["missingRealEvidenceCount"] == 12,
            "INDEPENDENT_GATES_NOT_MISSING")
    return {
        "schema": SCHEMA,
        "mode": MODE,
        "classification": classification,
        "fakeReserveBytes": reserve,
        "fakeDiskAboveReserve": disk_enough if not missing else None,
        "fakeInodesAboveReserve": inode_enough if not missing else None,
        "syntheticMetricAgeSeconds": age,
        "requiredRealEvidenceGates": gates["gateCount"],
        "missingRealEvidenceGates": gates["missingRealEvidenceCount"],
        "actualLiveInstalledShaVerified": False,
        "actualOracleFreeCapacityMeasured": False,
        "actualOracleBillingChecked": False,
        "realTailscalePolicyChecked": False,
        "actualCIPushMainVerified": False,
        "realBackupOrRestorePerformed": False,
        "realVpsContacted": False,
        "actualPrivateEvidenceCollected": False,
        "databaseOpened": False,
        "productionWritePerformed": False,
        "releaseAuthorized": False,
        "researchC5Enabled": False,
        "operationalDecision": NO_GO,
    }


def main():
    parser = argparse.ArgumentParser(
        description="REMURA v1.65 invented-metadata preflight ONLY, NO LIVE")
    parser.add_argument("--check-synthetic-readonly", action="store_true",
                        required=True)
    parser.parse_args()
    print(json.dumps(assess_mock(fake_snapshot()), sort_keys=True))


if __name__ == "__main__":
    main()
