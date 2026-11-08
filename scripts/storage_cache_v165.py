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
            if (type(item) is not dict or
                    item.get("schema") != SCHEMA or
                    item.get("operationalDecision") != NO_GO or
                    item.get("offhostBackupVerified") is not False or
                    item.get("restoreOutsideVpsVerified") is not False or
                    item.get("researchLiveEnabled") is not False):
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
