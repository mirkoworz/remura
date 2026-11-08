"""DRAFT-only background cache for the optional private resources metadata.

Default-OFF: module import has zero filesystem, network, thread, or SQLite
effects. An explicitly enabled future LIVE service may sample read-only
filesystem metadata every 15 minutes on a daemon thread. HTTP requests read
only in-memory cache, never a file, SQLite database or provider.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import threading
import time

from storage_inventory_v165 import (
    LIVE_MODE, NO_GO, inventory,
)

EXPECTED_DATABASE = Path("/opt/remura/private/remura-prices.sqlite3")
PERIOD_SECONDS = 900
TTL_SECONDS = 1200
SCHEMA = "remura-storage-cache-v165-draft"


def _unavailable(state):
    return {
        "schema": SCHEMA,
        "state": state,
        "sampledAtUtc": None,
        "metadata": None,
        "offhostBackupVerified": False,
        "restoreOutsideVpsVerified": False,
        "oracleBillingVerified": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
    }


def _live_sample(db_path):
    """No network, content reads, credentials, SQLite connections or writes."""
    if type(db_path) not in (str, Path) or Path(db_path) != EXPECTED_DATABASE:
        return _unavailable("UNKNOWN_OUT_OF_SCOPE_DATABASE_PATH")
    try:
        data = inventory(
            "/opt/remura/private", mode=LIVE_MODE, live_approved=True
        )
    except (OSError, RuntimeError, ValueError, TypeError):
        return _unavailable("UNKNOWN_METADATA_SAMPLE_FAILED")
    if data.get("operationalDecision") != NO_GO:
        return _unavailable("UNKNOWN_METADATA_UNSAFE_DECISION")
    return {
        "schema": SCHEMA,
        "state": "METADATA_ONLY_NEVER_OFFHOST_PROOF",
        "sampledAtUtc": datetime.now(timezone.utc).isoformat(),
        "metadata": data,
        "offhostBackupVerified": False,
        "restoreOutsideVpsVerified": False,
        "oracleBillingVerified": False,
        "researchLiveEnabled": False,
        "operationalDecision": NO_GO,
    }



# HTTP responses must never echo arbitrary future sampler fields: the cache
# accepts a strict, numeric, path-free allowlist even if a sampler regresses.
_CACHE_FIELDS = frozenset((
    "schema", "state", "sampledAtUtc", "metadata",
    "offhostBackupVerified", "restoreOutsideVpsVerified",
    "oracleBillingVerified", "researchLiveEnabled", "operationalDecision",
))
_INVENTORY_FIELDS = frozenset((
    "schema", "state", "main", "wal", "shm", "localBackups",
    "filesystem", "pressure", "scope", "noDatabaseFileContentRead",
    "noSqliteConnectionOpened", "sourceUnmodifiedProven",
    "offhostBackupExistsVerified", "backupRestoreIntegrityVerified",
    "allOtherPrivateStorageCovered", "oracleAlwaysFreeBillingVerified",
    "operationalDecision", "newNetworkCalls",
))
_FILE_FIELDS = frozenset(("state", "apparentBytes", "allocatedBytes"))
_BACKUP_FIELDS = frozenset((
    "state", "archives", "apparentBytes", "rollbacks", "rollbackApparentBytes",
))
_BACKUP_STATES = frozenset((
    "LOCAL_ARCHIVE_METADATA_NOT_RESTORE_EVIDENCE",
    "LOCAL_ROLLBACK_METADATA_NOT_SQLITE_BACKUP_PROOF",
    "UNKNOWN_NO_LOCAL_BACKUP_ARCHIVE",
    "UNKNOWN_NO_LOCAL_BACKUP_DIRECTORY",
    "UNKNOWN_BACKUP_DIRECTORY_TYPE",
    "UNKNOWN_LOCAL_BACKUP_LAYOUT_OR_BOUNDS",
))


def _byte_count(value):
    return type(value) is int and 0 <= value <= 2**63 - 1


def _file_metadata_safe(value):
    if type(value) is not dict or set(value) != _FILE_FIELDS:
        return False
    state = value["state"]
    if state == "FILE_SIZE_METADATA_ONLY":
        return (_byte_count(value["apparentBytes"])
                and _byte_count(value["allocatedBytes"]))
    return (state == "NOT_PRESENT_AT_METADATA_INSTANT"
            and value["apparentBytes"] is None
            and value["allocatedBytes"] is None)


def _inventory_safe(value):
    if type(value) is not dict:
        return False
    keys = set(value)
    state = value.get("state")
    full = state == "METADATA_ONLY_NOT_INDEPENDENTLY_ATTESTED"
    expected = _INVENTORY_FIELDS | ({"suggestedLabReserveBytes"} if full else set())
    if keys != expected or value.get("schema") != "remura-c4bf-readonly-metadata-v1":
        return False
    if state not in (
            "METADATA_ONLY_NOT_INDEPENDENTLY_ATTESTED",
            "UNKNOWN_READONLY_METADATA_INVENTORY_INCOMPLETE"):
        return False
    if (value["scope"] != "ONE_KNOWN_PRICE_DATABASE_AND_LOCAL_PREDEPLOY_DIRECTORY_ONLY"
            or value["noDatabaseFileContentRead"] is not True
            or value["noSqliteConnectionOpened"] is not True
            or any(value[k] is not False for k in (
                "sourceUnmodifiedProven", "offhostBackupExistsVerified",
                "backupRestoreIntegrityVerified", "allOtherPrivateStorageCovered",
                "oracleAlwaysFreeBillingVerified"))
            or value["operationalDecision"] != NO_GO
            or value["newNetworkCalls"] != 0
            or value["pressure"] not in (
                "RESEARCH_PRESSURE_CAUTION",
                "METADATA_HEADROOM_NOT_OPERATIONAL_GO", "UNKNOWN")):
        return False
    local = value["localBackups"]
    if type(local) is not dict:
        return False
    if set(local) == {"state"}:
        if local["state"] != "UNKNOWN_NO_SCANNED_BACKUP":
            return False
    elif set(local) == _BACKUP_FIELDS and local["state"] in _BACKUP_STATES:
        if any(x is not None and not _byte_count(x)
               for k, x in local.items() if k != "state"):
            return False
    else:
        return False
    if full:
        fs = value["filesystem"]
        return (
            all(_file_metadata_safe(value[k]) for k in ("main", "wal", "shm"))
            and type(fs) is dict
            and set(fs) == {"availableBytes", "availableInodes"}
            and all(_byte_count(x) for x in fs.values())
            and _byte_count(value["suggestedLabReserveBytes"]))
    return (value["main"] is None and value["wal"] is None
            and value["shm"] is None and value["filesystem"] is None)


def _safe_cache_payload(item):
    if type(item) is not dict or set(item) != _CACHE_FIELDS:
        return False
    if (item["schema"] != SCHEMA
            or item["operationalDecision"] != NO_GO
            or any(item[k] is not False for k in (
                "offhostBackupVerified", "restoreOutsideVpsVerified",
                "oracleBillingVerified", "researchLiveEnabled"))):
        return False
    state = item["state"]
    if state == "METADATA_ONLY_NEVER_OFFHOST_PROOF":
        timestamp = item["sampledAtUtc"]
        return (type(timestamp) is str
                and 20 <= len(timestamp) <= 40
                and timestamp.endswith("+00:00")
                and _inventory_safe(item["metadata"]))
    return (type(state) is str and state.startswith("UNKNOWN_")
            and len(state) <= 80
            and all(c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_" for c in state)
            and item["sampledAtUtc"] is None and item["metadata"] is None)


class StorageMetadataCache:
    """Bounded refresh in a background thread; HTTP GET performs no sampling."""

    def __init__(self, sampler=None):
        self._sampler = sampler if sampler is not None else _live_sample
        self._lock = threading.Lock()
        self._latest = _unavailable("UNKNOWN_NOT_INITIALIZED")
        self._observed = None
        self._started = False

    def peek(self):
        with self._lock:
            item = deepcopy(self._latest)
            observed = self._observed
        if observed is None or time.monotonic() - observed > TTL_SECONDS:
            return _unavailable("UNKNOWN_MISSING_OR_STALE_CACHE")
        return item

    def refresh_once(self, db_path):
        """For worker and isolated tests; never call inside HTTP handler."""
        try:
            item = self._sampler(db_path)
            if not _safe_cache_payload(item):
                item = _unavailable("UNKNOWN_INVALID_SAMPLER_PAYLOAD")
        except Exception:
            item = _unavailable("UNKNOWN_SAMPLER_EXCEPTION")
        with self._lock:
            self._latest = deepcopy(item)
            self._observed = time.monotonic()

    def start(self, db_path, stop):
        """Explicit opt-in only. Use the existing server's shutdown event."""
        with self._lock:
            if self._started:
                return False
            self._started = True

        def poll():
            while not stop.is_set():
                self.refresh_once(db_path)
                if stop.wait(PERIOD_SECONDS):
                    break

        worker = threading.Thread(
            target=poll,
            name="remura-private-storage-metadata",
            daemon=True,
        )
        worker.start()
        return True
