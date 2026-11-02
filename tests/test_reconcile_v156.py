"""No-network, no-VPS tests for guarded v1.56 state reconciliation."""
import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import os
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("reconcile_v156",ROOT/"deploy/oracle/reconcile_v156.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestReconcile(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.base=Path(self.temp.name)
        self.private=self.base/"private"
        self.private.mkdir()
        self.work=self.base/"work"
        self.work.mkdir()
        (self.work/"lock").touch()
        self.backups=self.private/"predeploy-backups"
        self.backups.mkdir()
        self.state=self.private/"autoupdate-state.json"
        self.data={"enabled":True,"state":"manual_required",
                   "installedSha":m.OLD,"targetSha":m.TARGET,
                   "manualSha":m.TARGET,"skippedSha":"","failedSha":"",
                   "lastSuccess":"2026-10-31T12:00:00Z","custom_info":"PRESERVE"}
        self.state.write_text(json.dumps(self.data))
        self.files=("nav.js","sw.js","scripts/private_server.py","price.js")
        self.staged={
            "nav.js":b'const a = "REMURA Aggiornamento v1.56 02/11/2026 07:43 (Italia, candidato al rilascio)";',
            "sw.js":b'const c = "remura-shell-v70-v1.56";',
            "scripts/private_server.py":b"print('placeholder')\n",
            "price.js":b"hello"
        }
        self.mod={"FILES":self.files}
        for name,body in self.staged.items():
            path=self.base/name
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(body.replace(m.STAMP,b"02/11/2026 08:44 (Italia)") if name=="nav.js" else body)
        patches=[
            patch.object(m,"APP",self.base),
            patch.object(m,"PRIVATE",self.private),
            patch.object(m,"WORK",self.work),
            patch.object(m,"BACKUPS",self.backups),
            patch.object(m,"STATE",self.state),
            patch.object(m.os,"geteuid",return_value=0),
            patch.object(m.os,"fchown"),
        ]
        self.patches=patches
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def _archive(self):
        snap=self.backups/"backup-v156-20261102"
        snap.mkdir()
        db=snap/"remura-prices.sqlite3"
        with sqlite3.connect(db) as con:
            con.execute("CREATE TABLE prices(symbol TEXT)")
            con.execute("CREATE TABLE status(key TEXT)")
        (snap/"manifest.txt").write_text("remura-v156-sqlite\nsha256="+hashlib.sha256(db.read_bytes()).hexdigest()+"\n")
        roll=self.backups/"rollback-v156-foo"
        roll.mkdir()
        manifest={"schema":"remura-v156-rollback-v1","files":{}}
        for path in self.files:
            if path in m.EXTRA: continue
            manifest["files"][path]={"old":"f"*64,
                   "new":hashlib.sha256((self.base/path).read_bytes()).hexdigest()}
        (roll/"manifest.json").write_text(json.dumps(manifest))
        return snap,roll

    def test_pinned_blob_sha_and_only_expected_release_timestamp(self):
        self.assertEqual(m.sha_blob(b"abc"),"f2ba8f84ab5c1bce84a7b441cb1959cfc7093b7f")
        self.assertEqual(m.live_code(self.staged,self.mod),4)
        (self.base/"nav.js").write_bytes((self.base/"nav.js").read_bytes()+b"// INJECTION")
        with self.assertRaisesRegex(RuntimeError,"LIVE_NAV_DIVERGED"):
            m.live_code(self.staged,self.mod)
        (self.base/"nav.js").write_bytes(self.staged["nav.js"])
        with self.assertRaisesRegex(RuntimeError,"LIVE_STAMP_MISSING"):
            m.live_code(self.staged,self.mod)

    def test_backup_manifest_verification_and_tampering(self):
        snap,roll=self._archive()
        m.check_archives(self.staged,self.mod)
        (roll/"manifest.json").write_text('{"schema":"bad"}')
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_DIVERGED"):
            m.check_archives(self.staged,self.mod)
        _,roll=self._archive_reset()
        m.check_archives(self.staged,self.mod)
        (snap/"remura-prices.sqlite3").write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError,"BACKUP_SNAPSHOT_UNVERIFIED"):
            m.check_archives(self.staged,self.mod)

    def _archive_reset(self):
        for p in self.backups.iterdir():
            import shutil
            if p.is_dir(): shutil.rmtree(p)
        return self._archive()

    def test_remote_ci_checks_and_moving_main_with_code(self):
        def fake(path):
            if path=="/commits/main": return {"sha":m.TARGET}
            if "/runs?" in path:
                return {"workflow_runs":[{"head_sha":m.TARGET,"event":"push",
                      "head_branch":"main","status":"completed","conclusion":"success"}]}
            raise AssertionError(path)
        with patch.object(m,"json_api",side_effect=fake):
            self.assertEqual(m.remote_main_ci(),m.TARGET)
        def failed(path):
            if "runs?" in path: return {"workflow_runs":[]}
            return fake(path)
        with patch.object(m,"json_api",side_effect=failed):
            with self.assertRaisesRegex(RuntimeError,"MAIN_CI_NOT_GREEN"):
                m.remote_main_ci()
        moved="b"*40
        def unsafe(path):
            if path=="/commits/main":return {"sha":moved}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":"scripts/price_feed.py"}]}
            return fake(path)
        with patch.object(m,"json_api",side_effect=unsafe):
            with self.assertRaisesRegex(RuntimeError,"MAIN_MOVED_WITH_CODE"):
                m.remote_main_ci()

    def test_main_moved_only_with_reconciler_files_and_green_ci(self):
        new_sha="b"*40
        def good(path):
            if path=="/commits/main":
                return {"sha":new_sha}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[
                    {"filename":"deploy/oracle/reconcile_v156.py"},
                    {"filename":"tests/test_reconcile_v156.py"},
                    {"filename":".github/workflows/price-checks.yml"},
                    {"filename":"ROADMAP.md"}]}
            if "/runs?" in path:
                return {"workflow_runs":[{"head_sha":new_sha,"event":"push",
                    "head_branch":"main","status":"completed","conclusion":"success"}]}
            raise AssertionError(path)
        with patch.object(m,"json_api",side_effect=good):
            self.assertEqual(m.remote_main_ci(),new_sha)
        # No CI on exact main SHA must fail, even if the diff is allowlisted.
        def bad(path):
            result=good(path)
            return {"workflow_runs":[]} if "/runs?" in path else result
        with patch.object(m,"json_api",side_effect=bad):
            with self.assertRaisesRegex(RuntimeError,"MAIN_CI_NOT_GREEN"):
                m.remote_main_ci()

    def test_check_is_readonly_apply_changes_only_state_and_preserves_fields(self):
        self._archive()
        old_files={p:(self.base/p).read_bytes() for p in self.files}
        old_state=self.state.read_bytes()
        def fake_release():return self.mod
        with patch.object(m,"release_module",side_effect=fake_release),\
             patch.object(m,"candidate",return_value=self.staged),\
             patch.object(m,"live_healthy"),\
             patch.object(m,"remote_main_ci",return_value=m.TARGET):
            stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):
                m.perform(False)
            self.assertIn("RICONCILIAZIONE=VERIFICATA",stdout.getvalue())
            self.assertEqual(self.state.read_bytes(),old_state)
            self.assertEqual(list(self.backups.glob("state-before*")),[])
            stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):
                m.perform(True)
            self.assertIn("RICONCILIAZIONE=OK",stdout.getvalue())
            after=json.loads(self.state.read_text())
            self.assertEqual(after["installedSha"],m.TARGET)
            self.assertEqual(after["lastSuccess"],self.data["lastSuccess"])
            self.assertEqual(after["custom_info"],"PRESERVE")
            self.assertEqual(len(list(self.backups.glob("state-before-v156-*.json"))),1)
            self.assertEqual(old_files,{p:(self.base/p).read_bytes() for p in self.files})
            stdout=io.StringIO()
            with contextlib.redirect_stdout(stdout):
                m.perform(True)
            self.assertIn("GIA_ESEGUITA",stdout.getvalue())

    def test_rejects_unknown_state_sha_and_failed_release(self):
        data=json.loads(self.state.read_text())
        data["installedSha"]="c"*40
        self.state.write_text(json.dumps(data))
        with patch.object(m,"release_module",return_value=self.mod),             patch.object(m,"candidate",return_value=self.staged),             patch.object(m,"live_healthy"),             patch.object(m,"check_archives"),             patch.object(m,"remote_main_ci",return_value=m.TARGET):
            with self.assertRaisesRegex(RuntimeError,"UNEXPECTED_INSTALLED_SHA"):
                m.inspection()
        data["installedSha"]=m.OLD
        data["failedSha"]="a"*40
        self.state.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError,"PENDING_FAILED_RELEASE"):
            m.load_state()


if __name__=="__main__":
    unittest.main()
