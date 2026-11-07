"""Synthetic-only CVD storage envelope and non-destructive fail-closed tests.

No VPS, LIVE SQLite, real market samples, broker calls or billing API.
"""
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_cvd_storage_gate as gate
from scripts import shark_cvd_sharded_ledger as shards
from scripts import shark_cvd_shard_backup as backup
from test_shark_cvd_scan_coverage import DAY, KEY, stamp


class StorageAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory(prefix="remura-cvd-storage-fixture-")
        self.addCleanup(temp.cleanup)
        self.parent=Path(temp.name)
        self.root=self.parent/"shards"
        self.root.mkdir(mode=0o700)

    @staticmethod
    def volume(free, total=8*1024**3):
        return SimpleNamespace(total=total,free=free)

    def test_envelope_counts_two_copies_and_keeps_reserve(self):
        part=self.root/"scan-000001.sqlite3"
        part.write_bytes(b"a"*8192)
        used=[part]
        total=8*1024**3
        reserve=max(gate.MIN_RESERVE_BYTES,(total+9)//10)
        expected=2*8192+2*64_000_000+reserve
        report=gate.assess(self.parent,used,copies=2,
                           max_shard_file_bytes=64_000_000,
                           usage_fn=lambda _:self.volume(expected,total))
        self.assertEqual(report["sourceArchiveBytesNow"],8192)
        self.assertEqual(report["requiredFreeBytes"],expected)
        self.assertEqual(report["remainingFreeAfterEnvelopeBytes"],0)
        self.assertEqual(report["plannedAdditionalCopies"],2)
        self.assertFalse(report["deployAuthorized"])
        self.assertFalse(report["oracleBillingVerified"])

    def test_one_byte_below_reserve_blocks_and_does_not_modify_file(self):
        part=self.root/"sample.sqlite3"
        part.write_bytes(b"immutable")
        report=gate.assess(self.parent,[part],copies=1,
                           max_shard_file_bytes=64_000_000,
                           usage_fn=lambda _:self.volume(7*1024**3))
        with self.assertRaisesRegex(ValueError,"capacity_preflight_failed"):
            gate.assess(self.parent,[part],copies=1,
                        max_shard_file_bytes=64_000_000,
                        usage_fn=lambda _:self.volume(
                            report["requiredFreeBytes"]-1))
        self.assertEqual(part.read_bytes(),b"immutable")

    def test_untrusted_source_and_usage_are_fail_closed(self):
        part=self.root/"archive.sqlite3"
        part.write_bytes(b"data")
        alias=self.root/"alias.sqlite3"
        alias.symlink_to(part)
        with self.assertRaisesRegex(ValueError,"source_untrusted"):
            gate.assess(self.parent,[alias],copies=1,
                        max_shard_file_bytes=64_000_000)
        with self.assertRaisesRegex(ValueError,"usage_unknown"):
            gate.assess(self.parent,[part],copies=1,
                        max_shard_file_bytes=64_000_000,
                        usage_fn=lambda _:self.volume(-1))
        with self.assertRaisesRegex(ValueError,"inventory_invalid"):
            gate.assess(self.parent,[part]*gate.MAX_FILES+[part],
                        copies=1,max_shard_file_bytes=64_000_000)
        with self.assertRaisesRegex(ValueError,"policy_invalid"):
            gate.assess(self.parent,[part],copies=True,
                        max_shard_file_bytes=64_000_000)

    def add(self,index):
        at=DAY+timedelta(hours=5,minutes=15*index)
        return shards.record(self.root,symbol="EURUSD",
                             slot_closed_at=stamp(at),
                             source_document=None,secret=KEY,
                             clock=at+timedelta(minutes=1))

    def test_real_shard_record_is_blocked_before_new_sqlite(self):
        with patch.object(gate.shutil,"disk_usage",
                          return_value=self.volume(1000)):
            with self.assertRaisesRegex(ValueError,"capacity_preflight_failed"):
                self.add(0)
        self.assertFalse((self.root/shards._name(1)).exists())
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],0)

    def test_existing_attempts_not_changed_when_free_space_disappears(self):
        self.add(0)
        old=shards.verify(self.root)
        with patch.object(gate.shutil,"disk_usage",
                          return_value=self.volume(1000)):
            with self.assertRaisesRegex(ValueError,"capacity_preflight_failed"):
                self.add(1)
        self.assertEqual(shards.verify(self.root),old)

    def test_snapshot_rejected_before_directory_is_created(self):
        self.add(0)
        dest=self.parent/"snapshot"
        with patch.object(gate.shutil,"disk_usage",
                          return_value=self.volume(1000)):
            with self.assertRaisesRegex(ValueError,"capacity_preflight_failed"):
                backup.create_snapshot(self.root,dest)
        self.assertFalse(dest.exists())
        self.assertEqual(shards.verify(self.root)["totalObservedAttempts"],1)

    def test_restore_rejected_before_directory_is_created(self):
        self.add(0)
        snap=self.parent/"snapshot"
        backup.create_snapshot(self.root,snap)
        dest=self.parent/"restored"
        with patch.object(gate.shutil,"disk_usage",
                          return_value=self.volume(1000)):
            with self.assertRaisesRegex(ValueError,"capacity_preflight_failed"):
                backup.restore_snapshot(snap,dest)
        self.assertFalse(dest.exists())
        self.assertEqual(backup.verify_snapshot(snap)["observedAttempts"],1)


if __name__=="__main__":
    unittest.main()
