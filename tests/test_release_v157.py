"""Offline-only integrity and rollback tests for guarded v1.57 release."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_v157", ROOT/"deploy/oracle/release_v157.py")
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
SHA = "a"*40


def source_file(path):
    if path.endswith(".py"):
        if path == tool.BACKUP_MODULE:
            return b'def create_backup():\n    return ("RESTORE_TEST=OK",)\n'
        return b"# Test module\npass\n"
    if path == "nav.js":
        return b"REMURA Aggiornamento v1.57 02/11/2026 16:25 (Italia, preparazione)"
    if path == "sw.js":
        return b'const CACHE="remura-shell-v71-v1.57-test";'
    if path.endswith(".html"):
        return b'<script src="./nav.js?v=157"></script>'
    return ("new " + path).encode("utf-8")


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.private = self.base/"private"
        self.private.mkdir()
        self.work = self.base/"work"
        self.work.mkdir()
        self.backups = self.private/"predeploy-backups"
        self.backups.mkdir()
        self.source = self.private/"remura-prices.sqlite3"
        with sqlite3.connect(self.source) as db:
            db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY, payload TEXT NOT NULL)")
            db.execute("CREATE TABLE status(key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        (self.private/"autoupdate-state.json").write_text(
            json.dumps({"installedSha": "d6e2cd7575e0e58a36d1512f6ccffee24fe2438a",
                        "state": "up_to_date"}))
        self.initial = {}
        for name in tool.FILES:
            path = self.base/name
            path.parent.mkdir(exist_ok=True, parents=True)
            content = (b"REMURA Aggiornamento v1.56" if name == "nav.js" else
                       b'const CACHE="remura-shell-v70-v1.56";' if name == "sw.js"
                       else ("old "+name).encode())
            path.write_bytes(content)
            self.initial[name] = content
        self.staged = {path:source_file(path) for path in (*tool.FILES, tool.BACKUP_MODULE)}
        self.staged["nav.js"] = source_file("nav.js")
        self.patches = [
            patch.object(tool, "APP", self.base),
            patch.object(tool, "PRIVATE", self.private),
            patch.object(tool, "BACKUPS", self.backups),
            patch.object(tool, "WORK", self.work),
            patch.object(tool.os, "geteuid", return_value=0),
            patch.object(tool, "unit", side_effect=lambda action,name: "active" if name == tool.SERVICE else "inactive"),
            patch.object(tool, "healthy", return_value=True),
            patch("os.fchown"),
        ]
        for p in self.patches: p.start()

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.temp.cleanup()

    def test_blob_hash_and_bad_sha_rejected(self):
        self.assertEqual(tool.git_blob(b"abc"), "f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")
        for invalid in ("main", "G"*40, "z"*40, "a"*41, None):
            self.assertFalse(tool.valid_sha(invalid))
        with self.assertRaisesRegex(RuntimeError, "COMMIT_INVALID"):
            tool.candidate("main")

    def test_candidate_uses_pinned_verified_git_tree_and_zip(self):
        archive = io.BytesIO()
        with zipfile.ZipFile(archive,"w") as z:
            for name,source in self.staged.items():
                z.writestr("root/"+name, source)
        tree = {"truncated": False, "tree": [
            {"type":"blob","path":p,"sha":tool.git_blob(raw)}
            for p,raw in self.staged.items()
        ]}
        def fetch(path,cap=tool.MAX_ZIP):
            return json.dumps(tree).encode() if path.startswith("/git/trees/") else archive.getvalue()
        with patch.object(tool,"api_read",side_effect=fetch) as r:
            output=tool.candidate(SHA)
        self.assertEqual(output,self.staged)
        self.assertEqual(r.call_count,2)
        self.assertIn(SHA,r.call_args_list[0].args[0])
        tree["tree"][0]["sha"]="f"*40
        with patch.object(tool,"api_read",side_effect=fetch):
            with self.assertRaisesRegex(RuntimeError,"GIT_BLOB_MISMATCH"):
                tool.candidate(SHA)

    def test_candidate_rejects_wrong_html_cache_version(self):
        candidate=dict(self.staged)
        candidate["asset.html"]=b'<script src="./nav.js?v=156"></script>'
        archive=io.BytesIO()
        with zipfile.ZipFile(archive,"w") as z:
            for name,payload in candidate.items():
                z.writestr("root/"+name,payload)
        tree={"truncated":False,"tree":[{"path":name,"type":"blob","sha":tool.git_blob(payload)}
                                         for name,payload in candidate.items()]}
        with patch.object(tool,"api_read",side_effect=lambda url, cap=tool.MAX_ZIP:
                          json.dumps(tree).encode() if url.startswith("/git/trees/") else archive.getvalue()):
            with self.assertRaisesRegex(RuntimeError,"PAGE_CACHE_VERSION_MISMATCH"):
                tool.candidate(SHA)

    def test_check_only_reads_without_writing_or_restarting(self):
        before = {p:(self.base/p).read_bytes() for p in tool.FILES}
        with patch.object(tool,"candidate",return_value=self.staged) as staged, \
             patch.object(tool,"atomic_write") as written, \
             patch.object(tool.subprocess,"run") as called:
            outcome,originals=tool.preflight(SHA)
            self.assertEqual(outcome,self.staged)
            self.assertEqual(set(originals),set(tool.FILES))
            written.assert_not_called()
            called.assert_not_called()
        self.assertEqual(before,{p:(self.base/p).read_bytes() for p in tool.FILES})
        self.assertFalse(list(self.backups.iterdir()))

    def test_apply_and_explicit_persistent_rollback(self):
        with patch.object(tool,"candidate",return_value=self.staged), \
             patch.object(tool.subprocess,"run",return_value=types.SimpleNamespace(returncode=0)), \
             patch.object(tool,"wait_health",return_value=True):
            with contextlib.redirect_stdout(io.StringIO()) as out:
                tool.apply(SHA)
            self.assertIn("BACKUP_SQLITE=VERIFICATO",out.getvalue())
            self.assertIn("RILASCIO_V157=OK",out.getvalue())
            for name in tool.FILES:
                if name == "nav.js":
                    self.assertIn(b"Aggiornamento v1.57", (self.base/name).read_bytes())
                    self.assertNotIn(b"preparazione", (self.base/name).read_bytes())
                else:
                    self.assertEqual((self.base/name).read_bytes(),self.staged[name])
            folders=list(self.backups.glob("rollback-v157-*"))
            self.assertEqual(len(folders),1)
            manifest=json.loads((folders[0]/"manifest.json").read_text())
            self.assertEqual(set(manifest["files"]),set(tool.FILES))
            tool.rollback_from(folders[0])
            for name in tool.FILES:
                self.assertEqual((self.base/name).read_bytes(),self.initial[name])

    def test_restart_failure_rolls_back_without_touching_sqlite(self):
        before_db=self.source.read_bytes()
        def fail_start(command,*args,**kwargs):
            if command[:2]==["systemctl","start"]:
                return types.SimpleNamespace(returncode=1)
            return types.SimpleNamespace(returncode=0)
        with patch.object(tool,"candidate",return_value=self.staged), \
             patch.object(tool.subprocess,"run",side_effect=fail_start), \
             patch.object(tool,"wait_health",return_value=True), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(RuntimeError,"POST_INSTALL_HEALTH"):
                tool.apply(SHA)
        self.assertIn("ROLLBACK=OK",out.getvalue())
        self.assertEqual(self.source.read_bytes(),before_db)
        for name in tool.FILES:
            self.assertEqual((self.base/name).read_bytes(),self.initial[name])

    def test_wrong_current_live_rejects_old_rollback(self):
        with patch.object(tool,"candidate",return_value=self.staged), \
             patch.object(tool.subprocess,"run",return_value=types.SimpleNamespace(returncode=0)), \
             patch.object(tool,"wait_health",return_value=True):
            tool.apply(SHA)
        folder=next(self.backups.glob("rollback-v157-*"))
        (self.base/"sw.js").write_bytes(b"modified by third party")
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_HASH_OR_LIVE_CHANGED"):
            tool.rollback_from(folder)

    def test_release_stamp_is_actual_italian_time(self):
        import datetime as dt
        from zoneinfo import ZoneInfo
        moment=dt.datetime(2026,11,2,9,47,tzinfo=ZoneInfo("Europe/Rome"))
        stamped=tool.release_stamp(self.staged,now=moment)
        self.assertIn(b"02/11/2026 09:47 (Italia)",stamped["nav.js"])
        self.assertIn(b"preparazione",self.staged["nav.js"])
        self.assertEqual(stamped["sw.js"],self.staged["sw.js"])

    def test_check_rejects_unreconciled_state(self):
        file=self.private/"autoupdate-state.json"
        file.write_text(json.dumps({"installedSha":"d8ae01e19dd87e21b48c0d08c4b0c46a66b1eee4",
                                    "state":"manual_required"}))
        with patch.object(tool,"candidate",return_value=self.staged):
            with self.assertRaisesRegex(RuntimeError,"AUTOUPDATE_NOT_RECONCILED"):
                tool.preflight(SHA)

    def test_check_rejects_unknown_installed_version_and_symlink(self):
        (self.base/"nav.js").write_bytes(b"VERSION 0.4")
        with patch.object(tool,"candidate",return_value=self.staged):
            with self.assertRaisesRegex(RuntimeError,"EXPECTED_V156"):
                tool.preflight(SHA)
        (self.base/"nav.js").unlink()
        (self.base/"nav.js").symlink_to(self.base/"price.js")
        with self.assertRaisesRegex(RuntimeError,"LOCAL_FILE_MISSING"):
            tool.local_files()


if __name__=="__main__":
    unittest.main()
