"""Offline tests for REMURA P0 local metadata-only preflight."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import hashlib
import json
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import resource_preflight as p

GIB = p.GIB


def good_snapshot():
    return {
        "diskTotalBytes": 80 * GIB, "diskAvailableBytes": 30 * GIB,
        "inodeTotal": 500_000, "inodeAvailable": 450_000,
        "memoryTotalBytes": 6 * GIB, "memoryAvailableBytes": 3 * GIB,
        "databasePresent": True, "backupDirectoryPresent": True,
    }


class ResourcePreflightTests(unittest.TestCase):
    def test_capacity_pass_never_grants_cloud_or_deployment_permission(self):
        result = p.classify_capacity(good_snapshot())
        self.assertEqual(result["capacityGate"], "capacity_only_pass")
        self.assertFalse(result["oracleAlwaysFreeVerified"])
        self.assertFalse(result["allowAutomaticExpansion"])
        self.assertFalse(result["backupIntegrityVerified"])

    def test_low_disk_ram_inodes_fail_closed(self):
        data = good_snapshot()
        data.update(diskAvailableBytes=1 * GIB,
                    memoryAvailableBytes=300 * p.MIB,
                    inodeAvailable=10_000)
        result = p.classify_capacity(data)
        self.assertEqual(result["capacityGate"], "hold")
        self.assertEqual(result["reasons"], [
            "disk_free_low", "inodes_free_low", "memory_free_low"
        ])
        self.assertFalse(result["allowAutomaticExpansion"])

    def test_missing_measurements_and_backup_fail_closed(self):
        data = good_snapshot()
        data.update(memoryTotalBytes=None, memoryAvailableBytes=None,
                    inodeTotal=0, backupDirectoryPresent=False)
        result = p.classify_capacity(data)
        self.assertEqual(result["capacityGate"], "hold")
        self.assertIn("unknown_ram", result["reasons"])
        self.assertIn("unknown_inodes", result["reasons"])
        self.assertIn("backup_directory_missing", result["reasons"])

    def test_host_memory_read_without_cgroup(self):
        with tempfile.TemporaryDirectory() as root:
            proc = Path(root) / "meminfo"
            cgroup = Path(root) / "cgroup"
            cgroup.mkdir()
            proc.write_text("MemTotal:       6000000 kB\nMemAvailable:   2500000 kB\n")
            (cgroup / "memory.max").write_text("max\n")
            (cgroup / "memory.current").write_text("20000000\n")
            out = p.read_linux_memory(proc, cgroup)
            self.assertEqual(out["source"], "host_meminfo")
            self.assertEqual(out["total"], 6_000_000 * 1024)
            self.assertEqual(out["available"], 2_500_000 * 1024)

    def test_cgroup_limit_is_respected(self):
        with tempfile.TemporaryDirectory() as root:
            proc = Path(root) / "meminfo"
            cgroup = Path(root) / "cgroup"
            cgroup.mkdir()
            proc.write_text("MemTotal:       9000000 kB\nMemAvailable:   5000000 kB\n")
            (cgroup / "memory.max").write_text(str(2 * GIB))
            (cgroup / "memory.current").write_text(str(int(1.8 * GIB)))
            out = p.read_linux_memory(proc, cgroup)
            self.assertEqual(out["source"], "cgroup_and_host")
            self.assertEqual(out["total"], 2 * GIB)
            self.assertLess(out["available"], 300 * p.MIB)

    def test_capture_only_metadata_never_modifies_db_or_prints_paths(self):
        with tempfile.TemporaryDirectory() as root:
            private = Path(root) / "private"
            private.mkdir()
            (private / "predeploy-backups").mkdir()
            dbfile = private / "remura-prices.sqlite3"
            dbfile.write_bytes(b"PRIVATE-DB-DO-NOT-DISCLOSE")
            before = hashlib.sha256(dbfile.read_bytes()).hexdigest()
            fake_stat = SimpleNamespace(f_blocks=100, f_frsize=GIB,
                 f_bavail=30, f_files=1_000_000, f_favail=800_000)
            memory = lambda: {"total": 6 * GIB, "available": 3 * GIB,
                              "source": "test"}
            with patch.object(p.os, "statvfs", return_value=fake_stat), \
                 patch.object(p.os, "getloadavg", return_value=(0.11, 0.33, 0.25)), \
                 patch.object(p.os, "cpu_count", return_value=2), \
                 patch.object(p, "_read_cpu_limit", return_value=2):
                out = p.capture(private, mem_reader=memory)
            self.assertEqual(out["capacityGate"], "capacity_only_pass")
            self.assertEqual(out["databaseTotalBytes"], dbfile.stat().st_size)
            self.assertEqual(before, hashlib.sha256(dbfile.read_bytes()).hexdigest())
            self.assertNotIn(root, json.dumps(out))
            self.assertNotIn("PRIVATE-DB", json.dumps(out))
            self.assertNotIn("trade", json.dumps(out).lower())

    def test_symlink_directory_and_symlink_db_are_rejected(self):
        with tempfile.TemporaryDirectory() as root:
            home = Path(root)
            folder = home / "private"
            folder.mkdir()
            link = home / "external"
            link.symlink_to(folder, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "private_directory_missing_or_unsafe"):
                p.capture(link)
            (folder / "predeploy-backups").mkdir()
            secret = home / "secret.sqlite3"
            secret.write_bytes(b"confidential")
            (folder / "remura-prices.sqlite3").symlink_to(secret)
            fake_stat = SimpleNamespace(f_blocks=100, f_frsize=GIB,
                  f_bavail=30, f_files=1000, f_favail=900)
            with patch.object(p.os, "statvfs", return_value=fake_stat):
                out = p.capture(folder, mem_reader=lambda: {
                    "total": 6 * GIB, "available": 3 * GIB, "source": "test"})
            self.assertFalse(out["databasePresent"])
            self.assertEqual(out["capacityGate"], "hold")

    def test_no_backup_integrity_claim_from_empty_directory(self):
        with tempfile.TemporaryDirectory() as root:
            private = Path(root)
            (private / "predeploy-backups").mkdir()
            (private / "remura-prices.sqlite3").write_bytes(b"db")
            fake_stat = SimpleNamespace(f_blocks=50, f_frsize=GIB,
                  f_bavail=20, f_files=1000, f_favail=800)
            with patch.object(p.os, "statvfs", return_value=fake_stat):
                out = p.capture(private, mem_reader=lambda: {
                    "total": 6 * GIB, "available": 3 * GIB, "source": "test"})
            self.assertTrue(out["backupDirectoryPresent"])
            self.assertFalse(out["backupIntegrityVerified"])


if __name__ == "__main__":
    unittest.main()
