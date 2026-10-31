#!/usr/bin/env python3
"""REMURA P0: bounded, local, read-only resource preflight.

Checks capacity before *considering* extra live data collection. This does NOT
verify the Oracle tenancy's Always Free eligibility or billing settings.
No broker/API calls, no SSH, no service changes, no database reads/writes.
No paths, tokens, hostnames, or account information appear in the JSON output.
"""
from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import stat

GIB = 1024 ** 3
MIB = 1024 ** 2
MIN_DISK_FREE = 2 * GIB
MIN_RAM_FREE = 512 * MIB
MIN_DISK_FREE_FRACTION = 0.20
MIN_RAM_FREE_FRACTION = 0.20
MIN_INODE_FREE_FRACTION = 0.10
DEFAULT_PRIVATE = "/opt/remura/private"
DB_FILES = ("remura-prices.sqlite3", "remura-prices.sqlite3-wal",
            "remura-prices.sqlite3-shm")


def _bounded_int(value):
    return int(value) if isinstance(value, (int, float)) and math.isfinite(value) and value >= 0 else None


def _regular_file_size(path):
    """Do not follow symlinks, regardless of what lies behind them."""
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size < 0:
            return None
        return info.st_size
    except OSError:
        return None


def _read_meminfo(path=Path("/proc/meminfo")):
    try:
        content = path.read_text(encoding="ascii")[:16000]
        fields = {}
        for line in content.splitlines():
            pieces = line.split()
            if len(pieces) >= 3 and pieces[2] == "kB" and pieces[0] in ("MemTotal:", "MemAvailable:"):
                fields[pieces[0]] = int(pieces[1]) * 1024
        return fields.get("MemTotal:"), fields.get("MemAvailable:")
    except (OSError, ValueError, UnicodeError):
        return None, None


def _read_cgroup_memory(cgroup=Path("/sys/fs/cgroup")):
    """Prefer the effective v2 cgroup limit if smaller than host RAM."""
    try:
        raw_max = (cgroup / "memory.max").read_text(encoding="ascii").strip()
        raw_used = (cgroup / "memory.current").read_text(encoding="ascii").strip()
        if raw_max == "max":
            return None, None
        maximum, used = int(raw_max), int(raw_used)
        if maximum < 1 or used < 0 or used > maximum:
            return None, None
        return maximum, maximum - used
    except (OSError, ValueError, UnicodeError):
        return None, None


def _read_cpu_limit(cgroup=Path("/sys/fs/cgroup")):
    try:
        fields = (cgroup / "cpu.max").read_text(encoding="ascii").split()
        if len(fields) != 2 or fields[0] == "max":
            return None
        quota, period = int(fields[0]), int(fields[1])
        return quota / period if quota > 0 and period > 0 else None
    except (OSError, ValueError, UnicodeError):
        return None


def read_linux_memory(proc=Path("/proc/meminfo"), cgroup=Path("/sys/fs/cgroup")):
    host_total, host_available = _read_meminfo(proc)
    quota_total, quota_available = _read_cgroup_memory(cgroup)
    if not host_total or host_available is None:
        if quota_total:
            return {"total": quota_total, "available": quota_available, "source": "cgroup"}
        return {"total": None, "available": None, "source": "unavailable"}
    if quota_total and quota_total < host_total:
        return {"total": quota_total, "available": min(quota_available, host_available),
                "source": "cgroup_and_host"}
    return {"total": host_total, "available": host_available, "source": "host_meminfo"}


def classify_capacity(snapshot):
    """Conservative capacity gate, not a cloud billing or trading safety gate."""
    failures = []
    unknown = []
    disk_total = snapshot.get("diskTotalBytes")
    disk_free = snapshot.get("diskAvailableBytes")
    if not disk_total or disk_free is None:
        unknown.append("disk")
    elif disk_free < max(MIN_DISK_FREE, disk_total * MIN_DISK_FREE_FRACTION):
        failures.append("disk_free_low")
    inode_total = snapshot.get("inodeTotal")
    inode_free = snapshot.get("inodeAvailable")
    if not inode_total or inode_free is None:
        unknown.append("inodes")
    elif inode_free < inode_total * MIN_INODE_FREE_FRACTION:
        failures.append("inodes_free_low")
    ram_total = snapshot.get("memoryTotalBytes")
    ram_free = snapshot.get("memoryAvailableBytes")
    if not ram_total or ram_free is None:
        unknown.append("ram")
    elif ram_free < max(MIN_RAM_FREE, ram_total * MIN_RAM_FREE_FRACTION):
        failures.append("memory_free_low")
    if not snapshot.get("databasePresent", False):
        failures.append("database_missing_or_unverified")
    if not snapshot.get("backupDirectoryPresent", False):
        failures.append("backup_directory_missing")
    return {
        "capacityGate": "hold" if failures or unknown else "capacity_only_pass",
        "reasons": sorted(set(failures + ["unknown_" + name for name in unknown])),
        # Must always be false: cloud subscription status is not observable here.
        "allowAutomaticExpansion": False,
        "oracleAlwaysFreeVerified": False,
        "backupIntegrityVerified": False,
    }


def capture(private_path=DEFAULT_PRIVATE, *, mem_reader=read_linux_memory):
    """Local metadata only. Never scans the DB or walks backup contents."""
    root = Path(private_path).expanduser()
    if root.is_symlink() or not root.is_dir():
        raise ValueError("private_directory_missing_or_unsafe")
    root = root.resolve(strict=True)
    try:
        stats = os.statvfs(root)
    except OSError as exc:
        raise ValueError("filesystem_statistics_unavailable") from exc
    memory = mem_reader()
    database_sizes = [_regular_file_size(root / name) for name in DB_FILES]
    # A symlink or abnormal database is never treated as a valid local archive.
    db_present = database_sizes[0] is not None and database_sizes[0] > 0
    backup = root / "predeploy-backups"
    backup_present = backup.is_dir() and not backup.is_symlink()
    try:
        load1 = round(os.getloadavg()[0], 3)
    except (AttributeError, OSError):
        load1 = None
    limit = _read_cpu_limit()
    cpus = os.cpu_count()
    if limit is None and cpus:
        limit = float(cpus)
    cpu_capacity = round(limit, 2) if limit and limit > 0 else None
    snapshot = {
        "schema": "remura-p0-capacity-v1",
        "diskTotalBytes": _bounded_int(stats.f_blocks * stats.f_frsize),
        "diskAvailableBytes": _bounded_int(stats.f_bavail * stats.f_frsize),
        "inodeTotal": _bounded_int(stats.f_files),
        "inodeAvailable": _bounded_int(stats.f_favail),
        "memoryTotalBytes": _bounded_int(memory["total"]),
        "memoryAvailableBytes": _bounded_int(memory["available"]),
        "memorySource": memory["source"],
        "cpuCapacityEstimate": cpu_capacity,
        "loadAverage1Minute": load1,
        "databasePresent": db_present,
        "databaseTotalBytes": sum(s for s in database_sizes if s is not None),
        "backupDirectoryPresent": backup_present,
    }
    # Load average is informational, not CPU usage nor an always-free quota.
    return {**snapshot, **classify_capacity(snapshot),
            "interpretation": "local_capacity_only_not_oracle_billing_attestation",
            "notes": ["not_a_deployment_approval", "not_a_backup_integrity_test",
                      "not_an_oci_account_audit", "no_remote_calls_or_db_queries"]}


def main():
    parser = argparse.ArgumentParser(description="REMURA P0 read-only local capacity check")
    parser.add_argument("--private-dir", default=DEFAULT_PRIVATE,
                        help="Existing local REMURA private directory")
    args = parser.parse_args()
    try:
        report = capture(args.private_dir)
    except (ValueError, OSError):
        parser.error("capacity_preflight_unavailable")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
