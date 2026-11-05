"""Synthetic-only validation for read-only Oracle storage/volume inspector.

All fixtures are temporary: no OCI, LIVE DB, trading account, broker or API.
"""
from __future__ import annotations

from contextlib import redirect_stdout
import io
from pathlib import Path
import os
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_oracle_capacity_readonly as capacity
from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_storage_gate as storage


class CapacityReadOnlyTests(unittest.TestCase):
    def test_standalone_constants_match_the_cvd_prototype(self):
        self.assertEqual(capacity.SHARD_MAX_FILE_BYTES,
                         shards.MAX_SHARD_FILE_BYTES)
        self.assertEqual(capacity.MAX_SHARDS,shards.MAX_SHARDS)
        self.assertEqual(capacity.MIN_RESERVE_BYTES,
                         storage.MIN_RESERVE_BYTES)
        self.assertEqual(capacity.RESERVE_DENOMINATOR,
                         storage.RESERVE_FRACTION_DENOMINATOR)
        self.assertEqual(storage.RESERVE_FRACTION_NUMERATOR,1)

    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="remura-readonly-oracle-unit-")
        self.addCleanup(temp.cleanup)
        self.root=Path(temp.name)
        self.private=self.root/"private"
        self.scratch=self.root/"scratch"
        self.private.mkdir()
        self.scratch.mkdir()
        self.price=self.private/capacity.LIVE_PRICE_DB_NAME
        self.price.write_bytes(b"PRIVATE_PRICE_CONTENT_NEVER_EMIT")
        self._original=self.price.read_bytes()
        self._mtime=self.price.stat().st_mtime_ns

    def test_simulated_volume_proves_two_copy_space_without_approving_deploy(self):
        total=50*1024**3
        free=27*1024**3
        info=capacity.estimate(volume_total=total,volume_free=free,
                               price_bytes=256*capacity.MiB,
                               staging_same_volume=False,
                               staging_free=8*1024**3,
                               available_mem_kib=540000)
        self.assertTrue(info["oneShardEnvelopeFitsCurrentFree"])
        self.assertTrue(info["full64ShardEnvelopeFitsCurrentFree"])
        self.assertEqual(info["status"],"NO_GO_REAL_P0B_P0C_UNVERIFIED")
        self.assertFalse(info["researchMayBeEnabled"])
        self.assertFalse(info["volumeAlwaysFreeEligibleVerified"])
        self.assertFalse(info["actualOracleChargesVerified"])
        self.assertFalse(info["livePriceIngestInterferenceMeasured"])
        self.assertEqual(info["tmpSameFilesystemAsPrivate"],False)
        self.assertNotIn("PRIVATE_PRICE_CONTENT",str(info))

    def test_threshold_exactly_and_one_byte_short(self):
        total=4*1024**3
        price=100*capacity.MiB
        reserve=max(storage.MIN_RESERVE_BYTES,
                    (total+9)//10)
        required=(3*shards.MAX_SHARD_FILE_BYTES+
                  2*price+2*shards.MAX_SHARD_FILE_BYTES+reserve)
        exact=capacity.estimate(volume_total=total,volume_free=required,
                                price_bytes=price,staging_same_volume=True)
        short=capacity.estimate(volume_total=total,volume_free=required-1,
                                price_bytes=price,staging_same_volume=True)
        self.assertTrue(exact["oneShardEnvelopeFitsCurrentFree"])
        self.assertFalse(short["oneShardEnvelopeFitsCurrentFree"])
        self.assertFalse(exact["full64ShardEnvelopeFitsCurrentFree"])

    def test_inspect_reads_only_metadata_and_never_sqlite(self):
        wal=self.private/(self.price.name+"-wal")
        wal.write_bytes(b"PRIVATE-WAL-DATA")
        content_before={p.name:(p.read_bytes(),p.stat().st_mtime_ns)
                        for p in (self.price,wal)}
        real_volume=(10*1024**3,4*1024**3)
        with patch.object(capacity,"_volume",return_value=real_volume), \
             patch.object(capacity,"_mem_available_kib",return_value=500000), \
             patch.object(sqlite3,"connect",side_effect=AssertionError(
                 "must_never_open_sqlite")):
            report=capacity.inspect(private=self.private,scratch=self.scratch)
        self.assertTrue(report["tmpSameFilesystemAsPrivate"])
        self.assertEqual(report["priceSqliteAndCurrentSidecarsMiB"],1)
        self.assertEqual(report["hostMemAvailableMiB"],500000//1024)
        self.assertFalse(report["includesExternalStorageOrHmacBackups"])
        self.assertNotIn("PRIVATE-WAL-DATA",str(report))
        self.assertNotIn(str(self.private),str(report))
        for p in (self.price,wal):
            self.assertEqual((p.read_bytes(),p.stat().st_mtime_ns),
                             content_before[p.name])
        self.assertEqual(set(p.name for p in self.private.iterdir()),
                         {self.price.name,wal.name})

    def test_symlink_database_and_sidecar_rejected(self):
        unsafe=self.private/"original.txt"
        unsafe.write_bytes(b"secret")
        self.price.unlink()
        self.price.symlink_to(unsafe)
        with self.assertRaisesRegex(ValueError,"untrusted_file"):
            capacity.inspect(private=self.private,scratch=self.scratch)
        self.price.unlink()
        self.price.write_bytes(b"db")
        (self.private/(self.price.name+"-shm")).symlink_to(unsafe)
        with self.assertRaisesRegex(ValueError,"untrusted_file"):
            capacity.inspect(private=self.private,scratch=self.scratch)

    def test_missing_or_nonregular_database_fails_closed(self):
        self.price.unlink()
        with self.assertRaisesRegex(ValueError,"metadata_unavailable"):
            capacity.inspect(private=self.private,scratch=self.scratch)
        self.price.mkdir()
        with self.assertRaisesRegex(ValueError,"untrusted_file"):
            capacity.inspect(private=self.private,scratch=self.scratch)

    def test_untrusted_parent_or_path_whitelist(self):
        other=self.root/"linked"
        other.symlink_to(self.private,target_is_directory=True)
        with self.assertRaisesRegex(ValueError,"directory_untrusted"):
            capacity.inspect(private=other,scratch=self.scratch)
        with self.assertRaisesRegex(ValueError,"allowlist"):
            capacity.inspect(private=self.private,scratch=self.scratch,
                             name="other.sqlite")

    def test_invalid_usage_and_types_block(self):
        with self.assertRaisesRegex(ValueError,"inputs_invalid"):
            capacity.estimate(volume_total=True,volume_free=1,
                              price_bytes=1,staging_same_volume=True)
        with self.assertRaisesRegex(ValueError,"inputs_invalid"):
            capacity.estimate(volume_total=100,volume_free=110,
                              price_bytes=1,staging_same_volume=True)
        with self.assertRaisesRegex(ValueError,"inputs_invalid"):
            capacity.estimate(volume_total=100,volume_free=50,
                              price_bytes=1,staging_same_volume="same")
        with patch.object(capacity.os,"statvfs") as fake:
            class Invalid:
                f_frsize=4096
                f_blocks=0
                f_bavail=100
            fake.return_value=Invalid()
            with self.assertRaisesRegex(ValueError,"volume_stats_invalid"):
                capacity._volume(self.private)

    def test_main_never_falls_back_to_synthetic_when_real_metadata_missing(self):
        output=io.StringIO()
        with patch.object(capacity,"inspect",side_effect=FileNotFoundError(
                "private-sensitive-path")):
            with redirect_stdout(output):
                exit_code=capacity.main(["--inspect"])
        self.assertEqual(exit_code,2)
        self.assertEqual(output.getvalue().strip(),
                         "REMURA_B_ORACLE_CAPACITY=NO_GO_METADATA_UNVERIFIED")
        self.assertNotIn("private-sensitive-path",output.getvalue())

    def test_self_check_is_offline_and_produces_no_files(self):
        output=io.StringIO()
        with patch.object(capacity,"inspect",side_effect=AssertionError(
                "no real host access")):
            with redirect_stdout(output):
                self.assertEqual(capacity.main(["--self-check"]),0)
        self.assertEqual(output.getvalue().strip(),
                         "REMURA_B_ORACLE_CAPACITY_SELF_CHECK=PASS")


if __name__=="__main__":
    unittest.main()
