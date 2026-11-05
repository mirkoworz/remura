#!/usr/bin/env python3
"""REMURA Track B P0c — READ-ONLY Oracle disk capacity discovery.

This optional one-shot preflight only reads filesystem metadata. It never
opens SQLite connections, reads database contents, creates directories, writes
files, uses credentials, contacts OCI or broker APIs, or enables CVD. For a
real host run use: python -B scripts/shark_oracle_capacity_readonly.py --inspect
ONLY from a trusted checkout; it is not scheduled or connected to LIVE.

A passing capacity estimate is NOT proof of Oracle Always Free eligibility,
billing, performance or safe deployment. Future writes and WAL may grow.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import sys

from scripts import shark_cvd_storage_gate as storage
from scripts import shark_cvd_sharded_ledger as shards

SCHEMA = "remura-track-b-oracle-readonly-capacity-v1"
LIVE_PRIVATE = Path("/opt/remura/private")
LIVE_PRICE_DB_NAME = "remura-prices.sqlite3"
STAGING = Path("/tmp")
MiB = 1024 * 1024
MAX_SAFE_BYTES = 1 << 60


def _directory(path):
    p = Path(path)
    info = p.lstat()
    if (not stat.S_ISDIR(info.st_mode) or
            stat.S_ISLNK(info.st_mode)):
        raise ValueError("capacity_directory_untrusted")
    return p, info.st_dev


def _file_bytes(directory, name, *, missing_ok=False):
    path = directory / name
    try:
        info = path.lstat()  # Never follow a source symlink.
    except FileNotFoundError:
        if missing_ok:
            return 0
        raise ValueError("price_sqlite_metadata_unavailable") from None
    if not stat.S_ISREG(info.st_mode) or stat.S_ISLNK(info.st_mode):
        raise ValueError("price_sqlite_untrusted_file")
    logical = info.st_size
    allocated = info.st_blocks * 512
    if (logical < 0 or allocated < 0 or
            max(logical, allocated) >= MAX_SAFE_BYTES):
        raise ValueError("price_sqlite_metadata_invalid")
    return max(logical, allocated)


def _volume(path):
    stats = os.statvfs(path)  # Filesystem metadata only, no file handle.
    unit = stats.f_frsize
    total = stats.f_blocks * unit
    free = stats.f_bavail * unit  # Available to ordinary user, not f_bfree.
    if (unit <= 0 or not 0 < total < MAX_SAFE_BYTES or
            not 0 <= free <= total):
        raise ValueError("capacity_volume_stats_invalid")
    return total, free


def _mem_available_kib():
    try:
        with open("/proc/meminfo", "r", encoding="ascii") as stream:
            for line in stream:
                if line.startswith("MemAvailable:"):
                    value=int(line.split()[1])
                    return value if value >= 0 else None
    except (OSError, IndexError, ValueError):
        return None
    return None


def estimate(*, volume_total, volume_free, price_bytes,
             staging_same_volume, staging_free=None,
             available_mem_kib=None):
    """Pure conservative sizing; zero real broker/OCI/SQLite interaction.

    The original ledger doesn't exist on LIVE. For a hypothetical new
    pilot, reserve original+snapshot+restore (3 copies), PLUS two independent
    price SQLite backup/restore copies. The existing price DB is already
    deducted from observed free; do not double count the original.
    """
    values=(volume_total,volume_free,price_bytes)
    if (any(type(x) is not int for x in values)
            or not 0 < volume_total < MAX_SAFE_BYTES
            or not 0 <= volume_free <= volume_total
            or not 0 < price_bytes < MAX_SAFE_BYTES
            or type(staging_same_volume) is not bool
            or (available_mem_kib is not None and
                (type(available_mem_kib) is not int or available_mem_kib<0))
            or (staging_free is not None and
                (type(staging_free) is not int or staging_free < 0))):
        raise ValueError("capacity_inputs_invalid")

    reserve=max(storage.MIN_RESERVE_BYTES,
                (volume_total+storage.RESERVE_FRACTION_DENOMINATOR-1)
                // storage.RESERVE_FRACTION_DENOMINATOR)
    transient=2*shards.MAX_SHARD_FILE_BYTES
    price_copies=2*price_bytes
    single=3*shards.MAX_SHARD_FILE_BYTES+price_copies+transient+reserve
    maximal=(3*shards.MAX_SHARDS*shards.MAX_SHARD_FILE_BYTES
             +price_copies+transient+reserve)
    # Conservatively use metadata: no estimated private storage may be
    # created merely because an estimate passed.
    return {
        "schema":SCHEMA,
        "status":"NO_GO_REAL_P0B_P0C_UNVERIFIED",
        "scope":"READ_ONLY_FILE_METADATA_ONLY",
        "dataVolumeTotalMiB":volume_total//MiB,
        "dataVolumeAvailableMiB":volume_free//MiB,
        "priceSqliteAndCurrentSidecarsMiB":(price_bytes+MiB-1)//MiB,
        "reservePolicyMiB":(reserve+MiB-1)//MiB,
        "additionalPriceBackupAndRestoreMiB":(price_copies+MiB-1)//MiB,
        "oneShardWithTwoCopiesAndReserveMiB":(single+MiB-1)//MiB,
        "full64ShardsWithTwoCopiesAndReserveMiB":(maximal+MiB-1)//MiB,
        "oneShardEnvelopeFitsCurrentFree":volume_free>=single,
        "full64ShardEnvelopeFitsCurrentFree":volume_free>=maximal,
        "tmpSameFilesystemAsPrivate":staging_same_volume,
        "tmpVolumeAvailableMiB":(
            staging_free//MiB if staging_free is not None else None),
        "hostMemAvailableMiB":(
            available_mem_kib//1024 if available_mem_kib is not None else None),
        "actualExistingCvdShardCount":None,
        "predictsFutureWalPeak":False,
        "assessesEntireOciAllocation":False,
        "includesExternalStorageOrHmacBackups":False,
        "volumeAlwaysFreeEligibleVerified":False,
        "actualOracleChargesVerified":False,
        "livePriceIngestInterferenceMeasured":False,
        "researchMayBeEnabled":False,
        "requiresManualReviewAndOfflineStaging":True,
    }


def inspect(*, private=LIVE_PRIVATE, scratch=STAGING,
            name=LIVE_PRICE_DB_NAME):
    """Read only the fixed production price DB's size and mount information."""
    if name != LIVE_PRICE_DB_NAME:
        raise ValueError("price_sqlite_allowlist_only")
    folder,data_dev=_directory(private)
    staging,temp_dev=_directory(scratch)
    main=_file_bytes(folder,name)
    sidecars=sum(_file_bytes(folder,name+suffix,missing_ok=True)
                 for suffix in ("-wal","-shm","-journal"))
    total,free=_volume(folder)
    _,temporary_free=_volume(staging)
    return estimate(volume_total=total,volume_free=free,
                    price_bytes=main+sidecars,
                    staging_same_volume=data_dev==temp_dev,
                    staging_free=temporary_free,
                    available_mem_kib=_mem_available_kib())


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args==["--inspect"]:
        try:
            output=inspect()
        except (OSError,ValueError) as error:
            # No local paths, tokens, or private contents in errors.
            print("REMURA_B_ORACLE_CAPACITY=NO_GO_METADATA_UNVERIFIED")
            return 2
        print("REMURA_B_ORACLE_CAPACITY="+json.dumps(
            output,sort_keys=True,separators=(",",":")))
        return 0
    if args==["--self-check"]:
        # Does not probe the host, even if run on an operator machine.
        sample=estimate(volume_total=8*1024**3,
                        volume_free=4*1024**3,
                        price_bytes=128*MiB,
                        staging_same_volume=False)
        if sample["status"]!="NO_GO_REAL_P0B_P0C_UNVERIFIED":
            raise ValueError("capacity_self_check_invalid")
        print("REMURA_B_ORACLE_CAPACITY_SELF_CHECK=PASS")
        return 0
    print("usage: python -B scripts/shark_oracle_capacity_readonly.py --self-check|--inspect")
    return 2


if __name__=="__main__":
    raise SystemExit(main())
