import contextlib
import importlib.util
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = pathlib.Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("release_v152", ROOT / "deploy/oracle/release_v152.py")
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)

class ReleaseTests(unittest.TestCase):
    def test_git_blob_calculates_correct_git_object(self):
        self.assertEqual(r.git_blob(b"abc"), "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")
        self.assertEqual(len(r.BLOBS), 12)
        self.assertEqual(r.SOURCE_COMMIT, "51bcdb2f73204ec98acd5b8338daadd68d696caf")

    def test_check_is_read_only_and_does_not_apply(self):
        with patch.object(r, "prepare", return_value={"nav.js": (b"old", b"new", 1, 1, 0o644)}), \
             patch.object(r, "apply") as applied, \
             patch.object(sys, "argv", ["release_v152.py", "--check"]):
            with contextlib.redirect_stdout(io.StringIO()) as stream:
                r.main()
            applied.assert_not_called()
            self.assertIn("ESITO=PRONTO_PER_RELEASE_V152", stream.getvalue())

    def test_apply_preserves_origins_and_starts_no_service(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            (base / "private").mkdir()
            (base / "nav.js").write_bytes(b"old nav")
            (base / "sw.js").write_bytes(b"old sw")
            original = {key: ((base/key).read_bytes(), b"new "+key.encode(), 0, 0, 0o644)
                        for key in ("nav.js", "sw.js")}
            with patch.object(r, "APP", base), patch.object(r, "BACKUP_DIR", base/"private"), \
                 patch.object(r, "unit", return_value="active"), patch.object(r, "healthy", return_value=True), \
                 patch("os.fchown"), patch.object(r, "atomic_write", wraps=r.atomic_write) as writer:
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    r.apply(original)
                self.assertEqual(writer.call_count, 2)
            self.assertIn("ESITO=RELEASE_V152_OK", stream.getvalue())
            for name, (_, new, _, _, _) in original.items():
                self.assertEqual((base/name).read_bytes(), new)
            copies=list((base/"private").glob("rollback-v152-*"))
            self.assertEqual(len(copies),1)
            self.assertEqual((copies[0]/"nav.js").read_bytes(),b"old nav")

    def test_partial_write_failure_rolls_back_originals(self):
        with tempfile.TemporaryDirectory() as folder:
            base = pathlib.Path(folder)
            (base/"private").mkdir()
            for name in ("nav.js", "sw.js"):
                (base/name).write_bytes(("old "+name).encode())
            changes={name:((base/name).read_bytes(),("new "+name).encode(),0,0,0o644)
                     for name in ("nav.js","sw.js")}
            real_write=r.atomic_write
            attempted=[0]
            def maybe_fail(*args):
                attempted[0]+=1
                if attempted[0]==2:raise OSError("simulated second write failure")
                return real_write(*args)
            with patch.object(r,"APP",base),patch.object(r,"BACKUP_DIR",base/"private"), \
                 patch.object(r,"atomic_write",side_effect=maybe_fail),patch("os.fchown"):
                with contextlib.redirect_stdout(io.StringIO()) as stream:
                    with self.assertRaises(OSError):
                        r.apply(changes)
            self.assertIn("ROLLBACK=OK",stream.getvalue())
            for name in changes:
                self.assertEqual((base/name).read_bytes(),("old "+name).encode())
