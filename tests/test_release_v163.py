"""Offline regressions for guarded v1.63 launch release. No VPS or broker network."""
import datetime as dt
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_v163",ROOT/"deploy/oracle/release_v163.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ReleaseV163Tests(unittest.TestCase):
    def test_exact_files_and_pinned_v162_base(self):
        self.assertEqual(m.BASE_SHA,"1568edefabc7bbdb7d06485d2b863b196a4e6155")
        self.assertEqual(len(m.FILES),15)
        self.assertEqual(len(m.EXISTING_FILES),12)
        self.assertEqual(set(m.NEW_FILES),{"splash.js","splash.css","splash-mascot.webp"})
        self.assertEqual(set(m.BASE_BLOBS),set(m.EXISTING_FILES))
        self.assertEqual(m.BACKUP_BLOB,"dc01f2b4767a5427b1d65b96f7a883870b82f608")
        self.assertTrue(m.REQUIRED<=m.ALLOWED)
        self.assertTrue(all(path.endswith((".html",".js",".css",".py",".webp")) for path in m.FILES))

    def test_only_reviewed_roadmap_docs_pass_diff_gate(self):
        target="a"*40
        required=set(m.REQUIRED)
        docs={"ROADMAP.md","ROADMAP-A-H1.md","ROADMAP-B-SHARK-SCIENCE.md"}
        self.assertTrue(docs<=m.ALLOWED)
        self.assertNotIn("scripts/ctrader_feed.py",m.ALLOWED)
        self.assertNotIn("private/remura.env",m.ALLOWED)
        def fake_remote(path,extra=()):
            if path=="/commits/main": return {"sha":target}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":p}
                    for p in sorted(required|docs|set(extra))]}
            return {"workflow_runs":[{"head_sha":target,"head_branch":"main",
                "event":"push","status":"completed","conclusion":"success"}]}
        with patch.object(m,"remote_doc",side_effect=fake_remote):
            m.verify_target(target)
        def unapproved(path):
            return fake_remote(path,{"scripts/ctrader_feed.py"})
        with patch.object(m,"remote_doc",side_effect=unapproved):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                m.verify_target(target)

    def test_install_stamp_uses_real_italian_clock(self):
        staged={"nav.js":b"REMURA Aggiornamento v1.63 "+m.PREPARED_STAMP,
                "sw.js":b"remura-shell-v77-v1.63-shark-splash"}
        when=dt.datetime(2026,11,5,19,28,tzinfo=ZoneInfo("Europe/Rome"))
        actual=m.release_stamp(staged,when)
        self.assertIn(b"05/11/2026 19:28 (Italia)",actual["nav.js"])
        self.assertNotIn(b"preparazione",actual["nav.js"])
        self.assertEqual(actual["sw.js"],staged["sw.js"])
        with self.assertRaisesRegex(RuntimeError,"EXPECTED_RELEASE_STAMP"):
            m.release_stamp({"nav.js":b"no stamp"})

    def test_pwa_files_not_private_api_cached(self):
        sw=(ROOT/"sw.js").read_text()
        nav=(ROOT/"nav.js").read_text()
        home=(ROOT/"index.html").read_text()
        backend=(ROOT/"scripts/private_server.py").read_text()
        self.assertIn("Aggiornamento v1.64",nav)
        self.assertIn("remura-shell-v78-v1.64-shark-cinematic",sw)
        self.assertIn('url.pathname.includes("/private-api/")',sw)
        for name in m.NEW_FILES:
            self.assertIn('"'+name+'"',backend)
            self.assertIn('./'+name,sw)
            self.assertTrue((ROOT/name).is_file())
        self.assertIn("splash.js?v=164",home)
        self.assertIn("splash.css?v=164",home)
        for name in m.FILES:
            if name.endswith(".html"):
                self.assertIn("nav.js?v=164",(ROOT/name).read_text(),name)

    def test_existing_h1_gate_is_preserved_and_not_disabled(self):
        backend=(ROOT/"scripts/private_server.py").read_text()
        self.assertIn("REMURA_H1_PAIRED_ENABLED",backend)
        self.assertIn("if h1_paired_enabled():",backend)
        installer=(ROOT/"deploy/oracle/release_v163.py").read_text()
        self.assertNotIn("verify_pair_flag_off",installer)
        self.assertIn("verify_flag_on()",installer)
        self.assertNotIn("requests.get(",installer)

    def test_v162_base_blob_check_rejects_drift(self):
        payloads={p:(("base-"+p).encode(),0,0,0o644) for p in m.EXISTING_FILES}
        nav=("REMURA banner 05/11/2026 15:30 (Italia)").encode()
        payloads["nav.js"]=(nav,0,0,0o644)
        hashes={}
        for key,(value,*_) in payloads.items():
            if key=="nav.js":
                value=value.replace(b"05/11/2026 15:30 (Italia)",m.OLD_STAMP)
            hashes[key]=m.git_blob(value)
        with patch.object(m,"BASE_BLOBS",hashes):
            m.verify_live_v162(payloads)
            bad=dict(payloads)
            bad["sw.js"]=(b"unapproved",0,0,0o644)
            with self.assertRaisesRegex(RuntimeError,"LIVE_V162_DIVERGED"):
                m.verify_live_v162(bad)

    def test_rollback_manifest_keeps_old_files_and_marks_new_files_for_removal(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            staged={p:b"new-"+p.encode() for p in m.FILES}
            originals={p:(b"old-"+p.encode(),0,0,0o644) for p in m.EXISTING_FILES}
            with patch.object(m,"BACKUPS",root):
                folder=m.saved_rollback(originals,staged,"a"*40)
            manifest=json.loads((folder/"manifest.json").read_text())
            self.assertEqual(manifest["schema"],"remura-v163-rollback-v1")
            self.assertEqual(set(manifest["files"]),set(m.FILES))
            for name in m.NEW_FILES:
                self.assertIsNone(manifest["files"][name]["old"])
                self.assertFalse((folder/name).exists())
            for name in m.EXISTING_FILES:
                self.assertEqual((folder/name).read_bytes(),originals[name][0])

    def test_preflight_declines_unknown_state_without_writes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/"private").mkdir()
            (root/"private"/"remura-prices.sqlite3").touch()
            state=root/"private"/"autoupdate-state.json"
            state.write_text(json.dumps({"enabled":True,"installedSha":"0"*40,
                                         "state":"manual_required","failedSha":""}))
            originals={p:(b"base",0,0,0o644) for p in m.EXISTING_FILES}
            staged={p:b"new" for p in m.FILES}
            with patch.object(m,"PRIVATE",root/"private"),\
                 patch.object(m.os,"geteuid",return_value=0),\
                 patch.object(m,"unit",return_value="inactive"),\
                 patch.object(m,"healthy",return_value=True),\
                 patch.object(m,"local_files",return_value=originals),\
                 patch.object(m,"verify_live_v162"),\
                 patch.object(m,"verify_flag_on"):
                # Service must pass first, state test is intentionally fail-closed.
                def active(action,name):
                    return "active" if name==m.SERVICE else "inactive"
                with patch.object(m,"unit",side_effect=active):
                    with self.assertRaisesRegex(RuntimeError,"STATE_UNEXPECTED"):
                        m.preflight("a"*40,staged)

if __name__=="__main__":unittest.main()
