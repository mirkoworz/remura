"""Offline protection tests for v1.58 installer; no VPS or broker access."""
import datetime as dt
import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from zoneinfo import ZoneInfo

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("release_v158",ROOT/"deploy/oracle/release_v158.py")
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
ORIGINAL_VERIFY_TARGET=m.verify_target
TARGET="a"*40

class ReleaseV158Test(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.private=self.root/"private";self.private.mkdir()
        self.backups=self.private/"predeploy-backups";self.backups.mkdir()
        self.work=self.root/"work";self.work.mkdir()
        (self.work/"lock").touch()
        (self.private/"remura.env").write_text("REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0\n")
        (self.private/"autoupdate-state.json").write_text(json.dumps(
            {"enabled":True,"installedSha":m.BASE_SHA,"state":"up_to_date","failedSha":""}))
        with sqlite3.connect(self.private/"remura-prices.sqlite3") as db:
            db.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY)")
            db.execute("CREATE TABLE status(key TEXT PRIMARY KEY)")
        self.original={}
        for name in m.FILES:
            path=self.root/name;path.parent.mkdir(exist_ok=True,parents=True)
            data=(b"REMURA 02/11/2026 16:55 (Italia)" if name=="nav.js"
                  else ("baseline-"+name).encode())
            path.write_bytes(data)
            self.original[name]=(data,0,0,0o600)
        expected=dict(self.original)
        expected["nav.js"]=(expected["nav.js"][0].replace(
            b"02/11/2026 16:55 (Italia)",m.OLD_STAMP),0,0,0o600)
        self.patches=[
            patch.object(m,"APP",self.root),
            patch.object(m,"PRIVATE",self.private),
            patch.object(m,"BACKUPS",self.backups),
            patch.object(m,"WORK",self.work),
            patch.object(m,"BASE_BLOBS",{p:m.git_blob(v[0]) for p,v in expected.items()}),
            patch.object(m.os,"geteuid",return_value=0),
            patch.object(m,"unit",side_effect=lambda action,name:
                         "active" if name==m.SERVICE else "inactive"),
            patch.object(m,"healthy",return_value=True),
            patch.object(m,"verify_target"),
            patch.object(m,"remote_doc",return_value={"sha":TARGET}),
        ]
        for p in self.patches:p.start()
    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()
    def test_exact_13_file_baseline_and_tampering(self):
        self.assertEqual(len(m.FILES),13)
        m.verify_live_v157(self.original)
        wrong=dict(self.original)
        wrong["scripts/signals_monitor.py"]=(b"tampered",0,0,0o600)
        with self.assertRaisesRegex(RuntimeError,"LIVE_V157_DIVERGED"):
            m.verify_live_v157(wrong)
        wrong=dict(self.original)
        wrong["nav.js"]=(b"no stamp",0,0,0o600)
        with self.assertRaisesRegex(RuntimeError,"LIVE_STAMP_INVALID"):
            m.verify_live_v157(wrong)
    def test_off_flag_and_private_flag_on_refused(self):
        m.verify_flag_off()
        (self.private/"remura.env").write_text("REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1\n")
        with self.assertRaisesRegex(RuntimeError,"POST_INGEST_FLAG_PREENABLED"):
            m.verify_flag_off()
    def test_stamp_is_real_italian_install_time(self):
        original={"nav.js":b"REMURA v1.58 "+m.PREPARED_STAMP,"sw.js":b"cache"}
        stamped=m.release_stamp(original,dt.datetime(2026,11,3,0,4,tzinfo=ZoneInfo("Europe/Rome")))
        self.assertIn(b"03/11/2026 00:04 (Italia)",stamped["nav.js"])
        self.assertIn(b"preparazione",original["nav.js"])
    def test_read_only_preflight_requires_known_state(self):
        before={p:(self.root/p).read_bytes() for p in m.FILES}
        staged={p:b"new-"+p.encode() for p in (*m.FILES,m.BACKUP_MODULE)}
        with patch.object(m,"candidate",return_value=staged),patch.object(m,"atomic_write") as write:
            m.preflight(TARGET)
            write.assert_not_called()
        self.assertEqual(before,{p:(self.root/p).read_bytes() for p in m.FILES})
        self.assertEqual(list(self.backups.iterdir()),[])
        (self.private/"autoupdate-state.json").write_text(json.dumps({
            "enabled":True,"installedSha":"b"*40,"state":"manual_required"}))
        with patch.object(m,"candidate",return_value=staged):
            with self.assertRaisesRegex(RuntimeError,"STATE_UNEXPECTED"):
                m.preflight(TARGET)
    def test_main_ci_and_allowlist_gates(self):
        def doc(path):
            if path=="/commits/main":return {"sha":TARGET}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":p} for p in sorted(m.REQUIRED)]}
            if "/runs?" in path:
                return {"workflow_runs":[{"head_sha":TARGET,"head_branch":"main",
                    "event":"push","status":"completed","conclusion":"success"}]}
            raise AssertionError(path)
        with patch.object(m,"remote_doc",side_effect=doc):ORIGINAL_VERIFY_TARGET(TARGET)
        with patch.object(m,"remote_doc",side_effect=lambda p:
             {"workflow_runs":[]} if "/runs?" in p else doc(p)):
            with self.assertRaisesRegex(RuntimeError,"CI_NOT_GREEN"):ORIGINAL_VERIFY_TARGET(TARGET)
        with patch.object(m,"remote_doc",side_effect=lambda p:
             {"sha":"b"*40} if p=="/commits/main" else doc(p)):
            with self.assertRaisesRegex(RuntimeError,"MAIN_MOVED"):ORIGINAL_VERIFY_TARGET(TARGET)
        def untrusted(p):
            result=doc(p)
            if p.startswith("/compare/"):result["files"].append({"filename":"deploy/oracle/autoupdate.py"})
            return result
        with patch.object(m,"remote_doc",side_effect=untrusted):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):ORIGINAL_VERIFY_TARGET(TARGET)
    def test_rollback_bundle_persists_checksums(self):
        staged={p:b"new-"+p.encode() for p in m.FILES}
        folder=m.saved_rollback(self.original,staged,TARGET)
        data=json.loads((folder/"manifest.json").read_text())
        self.assertEqual(data["schema"],"remura-v158-rollback-v1")
        self.assertEqual(set(data["files"]),set(m.FILES))
        self.assertTrue(all(data["files"][p]["old"]==m.digest(self.original[p][0]) for p in m.FILES))
    def test_apply_and_explicit_rollback_keep_database_and_state_unchanged(self):
        import contextlib
        import io
        import types
        staged={p:b"new-"+p.encode() for p in m.FILES}
        staged["nav.js"]=b"REMURA Aggiornamento v1.58 "+m.PREPARED_STAMP
        staged["sw.js"]=b"remura-shell-v72-v1.58"
        staged[m.BACKUP_MODULE]=b'def create_backup():\n    return ("RESTORE_TEST=OK",)\n'
        statefile=self.private/"autoupdate-state.json"
        dbfile=self.private/"remura-prices.sqlite3"
        state_before=statefile.read_bytes()
        db_before=dbfile.read_bytes()
        with patch.object(m,"candidate",return_value=staged), \
             patch.object(m.os,"fchown"), \
             patch.object(m.subprocess,"run",return_value=types.SimpleNamespace(returncode=0)), \
             contextlib.redirect_stdout(io.StringIO()) as log:
            m.apply(TARGET)
            self.assertIn("RILASCIO_V158=OK",log.getvalue())
            self.assertEqual(statefile.read_bytes(),state_before)
            self.assertEqual(dbfile.read_bytes(),db_before)
            self.assertIn(b"Aggiornamento v1.58",(self.root/"nav.js").read_bytes())
            self.assertNotIn(b"preparazione",(self.root/"nav.js").read_bytes())
            folders=list(self.backups.glob("rollback-v158-*"))
            self.assertEqual(len(folders),1)
            m.rollback_from(folders[0])
            self.assertEqual(statefile.read_bytes(),state_before)
            self.assertEqual(dbfile.read_bytes(),db_before)
            self.assertEqual({p:(self.root/p).read_bytes() for p in m.FILES},
                             {p:v[0] for p,v in self.original.items()})

    def test_unsafe_sha_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"COMMIT_INVALID"):m.candidate("main")

if __name__=="__main__":unittest.main()
