"""REMURA v1.64 cinematic PWA release gates. Offline, no broker/API traffic."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_v164",ROOT/"deploy/oracle/release_v164.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
SHA="a"*40

class ReleaseV164Tests(unittest.TestCase):
    def test_pinned_baseline_and_exact_15_existing_files(self):
        self.assertEqual(m.BASE_SHA,"16fb7c84a130a2e54f849fa7eadddba4f62455bf")
        self.assertEqual(len(m.FILES),15)
        self.assertEqual(m.NEW_FILES,())
        self.assertEqual(set(m.EXISTING_FILES),set(m.FILES))
        self.assertEqual(set(m.BASE_BLOBS),set(m.FILES))
        self.assertEqual(m.BACKUP_BLOB,"dc01f2b4767a5427b1d65b96f7a883870b82f608")
        self.assertTrue(m.REQUIRED<=m.ALLOWED)
        self.assertNotIn("scripts/private_server.py",m.ALLOWED)
        self.assertNotIn("scripts/ctrader_feed.py",m.ALLOWED)
        self.assertNotIn("private/remura.env",m.ALLOWED)

    def test_italian_install_timestamp_is_not_prepared_timestamp(self):
        source={"nav.js":b"REMURA v1.64 "+m.PREPARED_STAMP}
        when=dt.datetime(2026,11,5,19,42,tzinfo=ZoneInfo("Europe/Rome"))
        actual=m.release_stamp(source,when)
        self.assertIn(b"05/11/2026 19:42 (Italia)",actual["nav.js"])
        self.assertNotIn(b"preparazione",actual["nav.js"])
        with self.assertRaisesRegex(RuntimeError,"EXPECTED_RELEASE_STAMP"):
            m.release_stamp({"nav.js":b"bad"})

    def test_iphone_cinematic_shell_and_one_private_health_get(self):
        home=(ROOT/"index.html").read_text()
        js=(ROOT/"splash.js").read_text()
        sw=(ROOT/"sw.js").read_text()
        self.assertIn("splash.js?v=164",home)
        self.assertIn("splash.css?v=164",home)
        self.assertIn("remura-shell-v78-v1.64-shark-cinematic",sw)
        self.assertIn('url.pathname.includes("/private-api/")',sw)
        self.assertEqual(js.count('fetch("./private-api/health"'),1)
        self.assertIn("ATTACHED_HOLD_MS = reduced ? 80 : 700",js)
        self.assertIn("failSafeTimer=setTimeout(close,6200)",js)
        for file in m.FILES:
            if file.endswith(".html"):
                self.assertIn("nav.js?v=164",(ROOT/file).read_text(),file)

    def test_cinematic_guard_accepts_6200ms_and_rejects_old_or_missing_safety(self):
        script=(ROOT/"splash.js").read_bytes()
        m.verify_splash_safety(script)
        self.assertNotIn(b"setTimeout(close,4500)",script)
        for corrupt in (
            script.replace(b"failSafeTimer=setTimeout(close,6200)",
                           b"failSafeTimer=setTimeout(close,4500)"),
            script.replace(b'fetch("./private-api/health"',
                           b'fetch("./private-api/unknown"'),
            script.replace(b"playIntro().catch(close)",b"playIntro()"),
            script.replace(b"ATTACHED_HOLD_MS = reduced ? 80 : 700",
                           b"ATTACHED_HOLD_MS = 0"),
        ):
            self.assertNotEqual(corrupt,script)
            with self.assertRaisesRegex(RuntimeError,"STOP_SPLASH_SAFETY_GUARD"):
                m.verify_splash_safety(corrupt)

    def test_historical_live_v163_sha_mismatch_rejected(self):
        original={p:((p+"-v163").encode(),0,0,0o644) for p in m.FILES}
        original["nav.js"]=(b"REMURA v1.63 05/11/2026 17:48 (Italia)",0,0,0o644)
        hashes={}
        for name,info in original.items():
            body=info[0]
            if name=="nav.js":
                body=body.replace(b"05/11/2026 17:48 (Italia)",m.OLD_STAMP)
            hashes[name]=m.git_blob(body)
        with patch.object(m,"BASE_BLOBS",hashes):
            m.verify_live_v163(original)
            bad=dict(original);bad["sw.js"]=(b"tampered",0,0,0o644)
            with self.assertRaisesRegex(RuntimeError,"LIVE_V163_DIVERGED"):
                m.verify_live_v163(bad)

    def test_release_diff_allows_only_cosmetic_files_and_tests(self):
        def fake_remote(path,extra=()):
            if path=="/commits/main":return {"sha":SHA}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":p} for p in sorted(m.REQUIRED|set(extra))]}
            if "/actions/workflows/" in path:
                return {"workflow_runs":[{"head_sha":SHA,"head_branch":"main",
                    "event":"push","status":"completed","conclusion":"success"}]}
            raise AssertionError("unexpected endpoint")
        with patch.object(m,"remote_doc",side_effect=fake_remote):
            m.verify_target(SHA)
        with patch.object(m,"remote_doc",side_effect=lambda p:fake_remote(p,{"scripts/ctrader_feed.py"})):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                m.verify_target(SHA)

    def test_rollback_preserves_each_existing_file(self):
        with tempfile.TemporaryDirectory() as td:
            backup=Path(td)
            original={p:(b"old-"+p.encode(),0,0,0o644) for p in m.FILES}
            staged={p:b"new-"+p.encode() for p in m.FILES}
            with patch.object(m,"BACKUPS",backup):
                folder=m.saved_rollback(original,staged,SHA)
            manifest=json.loads((folder/"manifest.json").read_text())
            self.assertEqual(manifest["schema"],"remura-v164-rollback-v1")
            self.assertEqual(set(manifest["files"]),set(m.FILES))
            for p in m.FILES:
                self.assertEqual((folder/p).read_bytes(),original[p][0])
                self.assertIsNotNone(manifest["files"][p]["old"])

if __name__=="__main__":unittest.main()
