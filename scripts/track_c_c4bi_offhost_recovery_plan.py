#!/usr/bin/env python3
"""Track C4b(i): conservative encrypted off-host recovery QUOTA PLAN (OFFLINE).

No provider access, credential, backup bytes, filesystem, subprocess, network,
or archive creation. NEVER makes a claim of billing safety or recovery success.
Reported free space, object counts and request usage are UNVERIFIED inputs.
Post-trial OCI Object Storage and Google Drive capacity are separate from
boot/block-volume allowances. Use conservative STANDARD tier 10 GB while
the OCI trial/account classification remains unresolved.
"""
from __future__ import annotations

MODE = "OFFLINE_C4BI_OFFHOST_RECOVERY_CAPACITY_PLAN_ONLY"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
GB = 10**9
MB = 10**6
# Planning caps, not account entitlements or live readings. Standard tier
# 10 GB is conservative during OCI Free Trial; 20 GB combined after trial.
OCI_STANDARD_TRIAL_CONSERVATIVE = 10 * GB
OCI_OBJECT_COMBINED_POST_TRIAL = 20 * GB
OCI_REQUEST_FREE_REFERENCE = 50_000
DRIVE_ACCOUNT_TOTAL_REFERENCE = 15 * GB
MAX_SOURCE_DB_BYTES = 8 * 1024**3
MAX_GENERATIONS = 5
MAX_REQUESTS = 500_000
TARGET_FIELDS = frozenset((
    "provider", "declaredFreeBytes", "declaredUsedMonthlyRequests",
    "plannedAdditionalMonthlyRequests",
))
PROVIDERS = frozenset(("OCI_STANDARD_OBJECT_STORAGE", "GOOGLE_DRIVE_PERSONAL"))
REQUIREMENTS = (
    "CONSISTENT_SQLITE_BACKUP_API_NOT_RAW_WAL_FILE_COPY",
    "AEAD_ENCRYPT_BEFORE_NETWORK_TRANSFER",
    "DECRYPTION_KEY_RECOVERABLE_OUTSIDE_VPS_AND_PROVIDER",
    "PRIVATE_OFFHOST_DESTINATION_WITH_LEAST_PRIVILEGE",
    "REMOTE_OBJECT_SIZE_AND_DIGEST_CONFIRMATION",
    "ISOLATED_DECRYPT_AND_SQLITE_RESTORE_TEST",
    "INDEPENDENT_FAILURE_DOMAIN_SECOND_COPY",
    "RETENTION_AND_DELETION_WITH_LIMITS_AND_ALERTS",
)


def _bounded(value, *, maximum, allow_none=False, positive=False):
    if value is None and allow_none:
        return None
    if type(value) is not int or value < (1 if positive else 0) or value > maximum:
        raise ValueError("strict_bounded_integer_required")
    return value


def _fail(status):
    return {
        "schema": "remura-c4bi-offhost-plan-v1",
        "status": status,
        "offhostTargets": [],
        "declaredSourceBytes": None,
        "estimatedPerGenerationBytes": None,
        "plannedGenerations": None,
        "desiredProvidersPresent": False,
        "independentAccountsVerified": False,
        "encryptedBackupActuallyCreated": False,
        "offhostCopyActuallyCreated": False,
        "remoteDigestVerified": False,
        "keyRecoveryVerified": False,
        "isolatedRestoreTestPassed": False,
        "cloudBillingAndQuotasVerified": False,
        "requiredRecoveryEvidence": REQUIREMENTS,
        "operationalDecision": NO_GO,
        "newProviderCalls": 0,
        "newCloudResources": 0,
        "newVpsRequests": 0,
    }


def assess(*, source_bytes, generations, targets, mode=None):
    """Size planning for candidate storage, never an operational GO.

    Source is approximate DB backup size BEFORE encryption; overhead is an
    ESTIMATE (25% plus 1 MB per retained copy), not an AES/age ciphertext
    upper bound or a proof that backup compression will occur.
    """
    if mode != MODE:
        raise ValueError("explicit_offline_recovery_mode_required")
    size = _bounded(source_bytes, maximum=MAX_SOURCE_DB_BYTES,
                    allow_none=True, positive=True)
    count = _bounded(generations, maximum=MAX_GENERATIONS, positive=True)
    if type(targets) not in (list, tuple) or len(targets) > 2:
        raise ValueError("bounded_offhost_target_list_required")
    seen = set()
    results = []
    estimated = (size * 125 + 99) // 100 + MB if size is not None else None
    required = estimated * count if estimated is not None else None
    for target in targets:
        if type(target) is not dict or set(target) != TARGET_FIELDS:
            raise ValueError("strict_targets_without_credentials_required")
        provider = target["provider"]
        if type(provider) is not str or provider not in PROVIDERS or provider in seen:
            raise ValueError("unknown_or_duplicate_provider")
        seen.add(provider)
        cap = (OCI_STANDARD_TRIAL_CONSERVATIVE if provider ==
               "OCI_STANDARD_OBJECT_STORAGE" else DRIVE_ACCOUNT_TOTAL_REFERENCE)
        free = _bounded(target["declaredFreeBytes"], maximum=cap, allow_none=True)
        used = _bounded(target["declaredUsedMonthlyRequests"],
                        maximum=MAX_REQUESTS, allow_none=True)
        added = _bounded(target["plannedAdditionalMonthlyRequests"],
                         maximum=MAX_REQUESTS, allow_none=True)
        if provider == "GOOGLE_DRIVE_PERSONAL" and (used is not None or added is not None):
            # This module does not model Google's per-API request quotas.
            raise ValueError("drive_request_quota_not_modelled")
        if required is None:
            space = "UNKNOWN_SOURCE_BACKUP_SIZE"
        elif free is None:
            space = "UNKNOWN_ACCOUNT_FREE_SPACE"
        elif free < required + cap // 5:
            space = "INSUFFICIENT_DECLARED_HEADROOM_OR_RESERVE"
        else:
            space = "PLAUSIBLE_DECLARED_CAPACITY_NOT_VERIFIED"
        if provider == "OCI_STANDARD_OBJECT_STORAGE":
            if used is None or added is None:
                requests = "UNKNOWN_OCI_REQUEST_USAGE"
            elif used + added > OCI_REQUEST_FREE_REFERENCE * 4 // 5:
                requests = "DECLARED_REQUEST_MARGIN_INSUFFICIENT"
            else:
                requests = "PLAUSIBLE_DECLARED_REQUEST_MARGIN_NOT_VERIFIED"
        else:
            requests = "GOOGLE_API_USAGE_NOT_AUDITED"
        results.append({
            "provider": provider,
            "planningReferenceMaximumBytes": cap,
            "declaredAvailableBytes": free,
            "estimatedBytesForAllGenerations": required,
            "declaredSpaceAssessment": space,
            "requestAssessment": requests,
            "encryptedCopiesVerified": False,
            "separateFailureDomainVerified": False,
            "restoreOutsideVpsVerified": False,
            "freeOfChargeForThisAccountVerified": False,
        })
    out = _fail("REVIEW_ONLY_UNATTESTED_CAPACITY_PLAN")
    out.update(
        offhostTargets=results,
        declaredSourceBytes=size,
        estimatedPerGenerationBytes=estimated,
        plannedGenerations=count,
        desiredProvidersPresent=seen == PROVIDERS,
    )
    if size is None:
        out["status"] = "UNKNOWN_REAL_SQLITE_SIZE_NOT_MEASURED"
    elif not targets:
        out["status"] = "UNKNOWN_NO_OFFHOST_TARGET_DECLARED"
    return out
