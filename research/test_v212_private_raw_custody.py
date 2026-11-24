"""REMURA A v21.2 — only NEW synthetic private original-byte custody tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import stat
import tempfile
import unittest

from test_v211_raw_cvd_direction_admission import freeze, raw
from v211_raw_cvd_direction_admission import store_private_raw_evidence


class NewV212RawCustodyTests(unittest.TestCase):
    def test_original_exact_bytes_and_two_existing_evidence_files_are_custodied(self):
        original = raw()
        ledger, manifest = freeze(original)
        with tempfile.TemporaryDirectory() as base:
            directory = Path(base) / "locked"
            result = store_private_raw_evidence(ledger, manifest, original, directory)
            self.assertEqual(result["files_created"], 3)
            self.assertTrue(result["original_raw_bytes_preserved_privately"])
            self.assertFalse(result["source_origin_independently_authenticated"])
            self.assertFalse(result["public_manifest_uploaded"])
            files = list(directory.iterdir())
            self.assertEqual(len(files), 3)
            raw_copy = next(directory.glob("*.original-cvd.raw.json"))
            self.assertEqual(raw_copy.read_bytes(), original)
            self.assertEqual(hashlib.sha256(raw_copy.read_bytes()).hexdigest(),
                             ledger["decisions"][0]["source_event_sha256"])
            self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
            self.assertTrue(all(stat.S_IMODE(p.stat().st_mode) == 0o600
                                for p in files))
            self.assertNotIn("100.125", str(result))
            self.assertNotIn("SYNTHETIC_CTRADER_ONLY", str(result))

    def test_changed_original_even_with_same_side_is_rejected_without_output(self):
        ledger, manifest = freeze()
        altered = raw(first="100.125", last="106.125")
        with tempfile.TemporaryDirectory() as base:
            directory = Path(base) / "locked"
            with self.assertRaisesRegex(ValueError, "raw_source_or_private"):
                store_private_raw_evidence(ledger, manifest, altered, directory)
            self.assertFalse(directory.exists())

    def test_duplicate_cannot_overwrite_or_delete_frozen_original(self):
        original = raw()
        ledger, manifest = freeze(original)
        with tempfile.TemporaryDirectory() as base:
            directory = Path(base) / "locked"
            store_private_raw_evidence(ledger, manifest, original, directory)
            before = {p.name: p.read_bytes() for p in directory.iterdir()}
            with self.assertRaisesRegex(ValueError, "already_frozen"):
                store_private_raw_evidence(ledger, manifest, original, directory)
            self.assertEqual({p.name: p.read_bytes() for p in directory.iterdir()},
                             before)

    def test_refuse_public_repository_and_excessive_directory_permissions(self):
        original = raw()
        ledger, manifest = freeze(original)
        with self.assertRaisesRegex(ValueError, "outside_public_repo"):
            store_private_raw_evidence(
                ledger, manifest, original, Path(__file__).resolve().parent
            )
        with tempfile.TemporaryDirectory() as base:
            directory = Path(base) / "too-open"
            directory.mkdir(mode=0o755)
            directory.chmod(0o755)
            with self.assertRaisesRegex(ValueError, "permissions_too_open"):
                store_private_raw_evidence(ledger, manifest, original, directory)
            self.assertEqual(list(directory.iterdir()), [])

    def test_symlink_directory_refused(self):
        original = raw()
        ledger, manifest = freeze(original)
        with tempfile.TemporaryDirectory() as base:
            real = Path(base) / "real"
            real.mkdir(mode=0o700)
            shortcut = Path(base) / "link"
            shortcut.symlink_to(real, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "symlink_rejected"):
                store_private_raw_evidence(ledger, manifest, original, shortcut)
            self.assertEqual(list(real.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
