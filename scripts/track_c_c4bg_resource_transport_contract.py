#!/usr/bin/env python3
"""Track C4b(g): FUTURE private resource-extension transport CONTRACT (offline).

This only validates a pre-redacted, caller-supplied payload. It does NOT
modify private_server, resource_monitor, existing GET endpoints, the VPS or
an Action. It NEVER reads files, connects to GitHub, uses providers or
authorizes prospective collection. Synthetic tests only until separately
approved LIVE release. A plausible timestamp is not an authenticated source.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math

MODE = "OFFLINE_C4BG_PROPOSED_TRANSPORT_ONLY"
SCHEMA = "remura-c4bg-private-storage-envelope-v1"
SOURCE = "remura-resources-v1"
INVENTORY = "remura-c4bf-readonly-metadata-v1"
NO_GO = "NO_GO_RESEARCH_AND_PROSPECTIVE_COLLECTION"
MAX_AGE = timedelta(minutes=10)
MAX_BYTES = 2**63 - 1
MAX_ARCHIVES = 64
ROOT_KEYS = {"schema", "resourceSchema", "sampledAtUtc", "inventory"}
INV_KEYS = {
    "schema", "state", "main", "wal", "shm", "localBackups",
    "filesystem", "pressure", "scope", "noDatabaseFileContentRead",
    "noSqliteConnectionOpened", "sourceUnmodifiedProven",
    "offhostBackupExistsVerified", "backupRestoreIntegrityVerified",
    "allOtherPrivateStorageCovered", "oracleAlwaysFreeBillingVerified",
    "operationalDecision", "newNetworkCalls", "suggestedLabReserveBytes",
}
ITEM_KEYS = {"state", "apparentBytes", "allocatedBytes"}
BK_KEYS = {"state", "archives", "apparentBytes", "rollbacks", "rollbackApparentBytes"}
FS_KEYS = {"availableBytes", "availableInodes"}
PRESENT = "FILE_SIZE_METADATA_ONLY"
ABSENT = "NOT_PRESENT_AT_METADATA_INSTANT"
LOCAL_OK = {
    "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE",
    "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF",
    "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE",
    "UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY",
    "UNKNOWN_BACKUP_DIRECTORY_TYPE",
    "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS",
}
PRESSURE = {"RESEARCH_PRESSURE_CAUTION",
            "METADATA_HEADROOM_NOT_OPERATIONAL_GO",
            "UNKNOWN"}


def _clock(value):
    if type(value) is not str or not 20 <= len(value) <= 35 or not (
            value.endswith("Z") or value.endswith("+00:00")):
        raise ValueError("utc_timestamp_required")
    try:
        t = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, OverflowError) as exc:
        raise ValueError("invalid_utc") from exc
    if t.utcoffset() != timedelta(0):
        raise ValueError("utc_timestamp_required")
    return t.astimezone(timezone.utc)


def _num(value, *, allow_none=False):
    if value is None and allow_none:
        return None
    if type(value) is not int or value < 0 or value > MAX_BYTES:
        raise ValueError("bounded_integer_required")
    return value


def _item(obj, *, required=False):
    if type(obj) is not dict or set(obj) != ITEM_KEYS:
        raise ValueError("strict_item_fields")
    state = obj["state"]
    if state == PRESENT:
        size, alloc = _num(obj["apparentBytes"]), _num(obj["allocatedBytes"])
        if required and size == 0:
            raise ValueError("required_core_size_zero")
        return {"state": "REPORTED_SIZE_NOT_ATTESTED",
                "apparentBytes": size, "allocatedBytes": alloc}
    if state == ABSENT and not required:
        if obj["apparentBytes"] is not None or obj["allocatedBytes"] is not None:
            raise ValueError("absent_file_must_not_claim_zero_usage")
        return {"state": "REPORTED_ABSENT_NOT_ZERO_PROOF",
                "apparentBytes": None, "allocatedBytes": None}
    raise ValueError("unexpected_item_state")


def _local(obj):
    if type(obj) is not dict or set(obj) != BK_KEYS or obj["state"] not in LOCAL_OK:
        raise ValueError("strict_local_backup_schema")
    name = obj["state"]
    local_report = name in {
        "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE",
        "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF",
        "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE",
    }
    count = _num(obj["archives"], allow_none=True)
    rb = _num(obj["rollbacks"], allow_none=True)
    size = _num(obj["apparentBytes"], allow_none=True)
    rb_size = _num(obj["rollbackApparentBytes"], allow_none=True)
    if (local_report and (count is None or rb is None or
                          count > MAX_ARCHIVES or rb > MAX_ARCHIVES)):
        raise ValueError("local_count_incomplete")
    if not local_report and (count is not None or rb is not None or
                             size is not None or rb_size is not None):
        raise ValueError("unknown_local_backup_is_not_zero")
    if local_report and (
        (count == 0 and size is not None) or
        (count > 0 and (size is None or size == 0)) or
        (rb == 0 and rb_size is not None) or
        (rb > 0 and (rb_size is None or rb_size == 0))
    ):
        raise ValueError("inconsistent_snapshot_rollback_totals")
    if name == "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE" and count == 0:
        raise ValueError("reported_snapshot_missing")
    if name == "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF" and (rb == 0 or count != 0):
        raise ValueError("rollback_not_data_snapshot")
    if name == "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE" and (count != 0 or rb != 0):
        raise ValueError("inconsistent_no_backup")
    return {"state": name, "localSnapshotDirectoriesReported": count,
            "localCodeRollbackDirectoriesReported": rb,
            "localSnapshotApparentBytes": size,
            "localRollbackApparentBytes": rb_size,
            "offhostRecoveryAttested": False}


def _empty(status):
    return {
        "schema": "remura-c4bg-redacted-review-v1",
        "status": status, "sampledAtUtc": None,
        "core": None, "wal": None, "shm": None,
        "localBackups": None,
        "filesystemAvailableBytesReported": None,
        "filesystemAvailableInodesReported": None,
        "diskPressureReported": None,
        "dataProvenanceAuthenticated": False,
        "currentVpsCapacityProven": False,
        "sqliteDataIntegrityProven": False,
        "offhostRestoreProven": False,
        "oracleBillingProven": False,
        "providerFirstSeenProven": False,
        "remoteEndpointCurrentlyImplemented": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
        "newNetworkCalls": 0,
    }


def review(payload, *, observed_at_utc, mode=None):
    """Fail-closed verification of the *proposed* allowlisted extension.

    Supplying metadata that looks fresh proves neither actual source
    identity nor billing nor any existing backup. This is not a live client.
    """
    if mode != MODE:
        raise ValueError("offline_contract_mode_required")
    now = _clock(observed_at_utc)
    if payload is None:
        return _empty("MISSING_EXTENSION_ON_EXISTING_ENDPOINT")
    try:
        if type(payload) is not dict or set(payload) != ROOT_KEYS:
            raise ValueError("unexpected_transport_fields")
        if payload["schema"] != SCHEMA or payload["resourceSchema"] != SOURCE:
            raise ValueError("wrong_transport_version")
        t = _clock(payload["sampledAtUtc"])
        if t > now or now - t > MAX_AGE:
            return _empty("MISSING_FRESH_ATTESTED_RESOURCE_EVIDENCE")
        inv = payload["inventory"]
        if type(inv) is not dict or set(inv) != INV_KEYS:
            raise ValueError("unexpected_inventory_fields")
        if inv["schema"] != INVENTORY or inv["state"] != "METADATA_ONLY_NOT_INDEPENDENTLY_ATTESTED":
            raise ValueError("unrecognized_inventory_status")
        if (inv["scope"] != "ONE_KNOWN_PRICE_DATABASE_AND_LOCAL_PREDEPLOY_DIRECTORY_ONLY" or
                inv["noDatabaseFileContentRead"] is not True or
                inv["noSqliteConnectionOpened"] is not True or
                inv["sourceUnmodifiedProven"] is not False or
                inv["offhostBackupExistsVerified"] is not False or
                inv["backupRestoreIntegrityVerified"] is not False or
                inv["allOtherPrivateStorageCovered"] is not False or
                inv["oracleAlwaysFreeBillingVerified"] is not False or
                inv["operationalDecision"] != NO_GO or
                inv["newNetworkCalls"] != 0 or
                inv["pressure"] not in PRESSURE):
            raise ValueError("attempted_false_operational_attestation")
        core = _item(inv["main"], required=True)
        wal, shm = _item(inv["wal"]), _item(inv["shm"])
        local = _local(inv["localBackups"])
        fs = inv["filesystem"]
        if type(fs) is not dict or set(fs) != FS_KEYS:
            raise ValueError("strict_filesystem_fields")
        free, inodes = _num(fs["availableBytes"]), _num(fs["availableInodes"])
        reserve = _num(inv["suggestedLabReserveBytes"])
        # A "low" percentage from a historical log cannot override this
        # metadata-only pressure caution. It never makes a GO anyway.
        pressure = ("REVIEW_LOW_LAB_HEADROOM" if free < reserve or inodes < 512
                    else "REPORTED_HEADROOM_UNAUTHENTICATED")
        out = _empty("FRESH_FORMAT_VALID_BUT_NOT_AUTHENTICATED")
        out.update(sampledAtUtc=t.isoformat(), core=core, wal=wal, shm=shm,
                   localBackups=local,
                   filesystemAvailableBytesReported=free,
                   filesystemAvailableInodesReported=inodes,
                   diskPressureReported=pressure)
        return out
    except (ValueError, TypeError, KeyError, OverflowError):
        return _empty("UNKNOWN_INVALID_OR_UNTRUSTED_EXTENSION")
