"""REMURA Track B — conservative storage admission for PRIVATE synthetic CVD shards.

Offline prototype. Guards are disabled nowhere in the sharded prototype, but
this module is NOT used by REMURA LIVE. It measures current filesystem free
space and source file sizes, never deletes or rotates data. Numbers represent
an internal safety policy, NOT Oracle Always Free quotas or a guaranteed bound
under concurrent external writers. A passing guard is NOT deploy approval.
"""
from __future__ import annotations

from pathlib import Path
import shutil
import stat

SCHEMA = "remura-cvd-private-storage-admission-v1"
MIN_RESERVE_BYTES = 256 * 1024 * 1024
RESERVE_FRACTION_NUMERATOR = 1
RESERVE_FRACTION_DENOMINATOR = 10
MAX_FILES = 192
MAX_COPIES = 2


def _source_bytes(files, *, max_file_bytes):
    if not isinstance(files, (tuple, list)) or len(files) > MAX_FILES:
        raise ValueError("cvd_storage_inventory_invalid")
    total = 0
    seen = set()
    for raw in files:
        path = Path(raw)
        if path.name in seen or path.is_symlink() or not path.is_file():
            raise ValueError("cvd_storage_source_untrusted")
        seen.add(path.name)
        info = path.stat()
        if (not stat.S_ISREG(info.st_mode) or info.st_size < 0
                or info.st_size > max_file_bytes):
            raise ValueError("cvd_storage_source_untrusted")
        total += info.st_size
    return total


def assess(parent, files, *, copies, max_shard_file_bytes,
           future_growth_bytes=0, usage_fn=None):
    """Return a redacted capacity envelope or raise BEFORE creating/writing.

    copies=2 budgets for both snapshot and restore coexisting with original
    shards on the SAME target filesystem. For another filesystem, this is a
    conservative target-local envelope, not an atomic cross-volume guarantee.
    2*max_shard_file_bytes is a pessimistic journal + temporary buffer.
    Always re-evaluate at execution; external writers can consume free space
    immediately after preflight, so SQLITE_FULL must still propagate.
    """
    location = Path(parent)
    if location.is_symlink() or not location.is_dir():
        raise ValueError("cvd_storage_private_parent_required")
    if (type(copies) is not int or not 0 <= copies <= MAX_COPIES
            or type(max_shard_file_bytes) is not int
            or not 4096 <= max_shard_file_bytes <= 256_000_000
            or type(future_growth_bytes) is not int
            or not 0 <= future_growth_bytes <= max_shard_file_bytes):
        raise ValueError("cvd_storage_policy_invalid")
    current = _source_bytes(files, max_file_bytes=max_shard_file_bytes)
    usage = (usage_fn or shutil.disk_usage)(location)
    total, free = usage.total, usage.free
    if (type(total) is not int or type(free) is not int
            or total <= 0 or not 0 <= free <= total):
        raise ValueError("cvd_storage_usage_unknown")
    reserve = max(MIN_RESERVE_BYTES,
                  (total * RESERVE_FRACTION_NUMERATOR
                   + RESERVE_FRACTION_DENOMINATOR - 1)
                  // RESERVE_FRACTION_DENOMINATOR)
    # Keep two entire *maximum-sized* transient work files as a buffer:
    # rollback-journal/backup temp and interrupted rollover. Not a proof of
    # actual journal peak; measured separately in staging.
    transient = 2 * max_shard_file_bytes
    required = (copies * current + transient + future_growth_bytes
                + reserve)
    if free < required:
        raise ValueError("cvd_storage_capacity_preflight_failed")
    return {
        "schema": SCHEMA,
        "status": "CAPACITY_PRECHECK_ONLY",
        "sourceArchiveBytesNow": current,
        "plannedAdditionalCopies": copies,
        "plannedAdditionalCopyBytes": copies * current,
        "transientBufferBytes": transient,
        "futureGrowthBytes": future_growth_bytes,
        "reservedForOtherWorkBytes": reserve,
        "requiredFreeBytes": required,
        "observedFreeBytes": free,
        "remainingFreeAfterEnvelopeBytes": free - required,
        "filesystemTotalBytes": total,
        "liveCollectorInterferenceMeasured": False,
        "oracleBillingVerified": False,
        "deployAuthorized": False,
    }
