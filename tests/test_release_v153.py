"""Test offline del rilascio protetto: nessuna chiamata alla VPS."""
import importlib.util
import os
import pathlib
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_v153", ROOT / "deploy/oracle/release_v153.py")
release = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(release)


class ReleaseV153Tests(unittest.TestCase):
    def test_expected_release_is_pinned(self):
        self.assertEqual(release.TARGET, "cd54befa0234add86077eee1d3d56a8469d1df54")
        self.assertEqual(len(release.FILES), 15)
        self.assertIn("scripts/resource_monitor.py", release.FILES)
        self.assertIn("scripts/private_server.py", release.FILES)
        self.assertTrue(all(not p.startswith("private/") and
                            not p.startswith("data/") and
                            not p.startswith(".github/") for p in release.FILES))

    def test_hash_function_is_git_compatible(self):
        with tempfile.TemporaryDirectory() as d:
            f = pathlib.Path(d) / "sample"
            f.write_bytes(b"abc")
            self.assertEqual(release.git_blob(f), "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")

    def test_atomic_replace_is_functional(self):
        with tempfile.TemporaryDirectory() as d:
            old = pathlib.Path(d) / "old"
            new = pathlib.Path(d) / "new"
            old.write_bytes(b"unmodified-original")
            new.write_bytes(b"expected-updated")
            release.replace_file(new, old, os.getuid(), os.getgid(), 0o600)
            self.assertEqual(old.read_bytes(), b"expected-updated")
            self.assertEqual(old.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(pathlib.Path(d).glob(".remura-v153-*")), [])

    def test_preflight_rejects_non_root_before_looking_at_data(self):
        with patch.object(release.os, "geteuid", return_value=1000):
            with self.assertRaisesRegex(RuntimeError, "ROOT_RICHIESTO"):
                release.preflight()


if __name__ == "__main__":
    unittest.main()
