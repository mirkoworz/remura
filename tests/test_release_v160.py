"""Offline guarded v1.60 release tests; no VPS, broker or network."""
import contextlib
import datetime as dt
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import stat
import tempfile
import types
import unittest
from unittest.mock import patch
from zoneinfo import ZoneInfo
import zipfile

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "release_v160",ROOT/"deploy/oracle/release_v160.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
ORIGINAL_VERIFY_TARGET=m.verify_target
TARGET="a"*40

class ReleaseV160Tests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.private=self.root/"private";self.private.mkdir()
        self.backups=self.private/"predeploy-backups";self.backups.mkdir()
        self.work=self.root/"work";self.work.mkdir()
        (self.work/"lock").touch()
        self.env=self.private/"remura.env"
        self.env.write_text(
            "REMURA_COLLECTOR_ENABLED=1\n"
            "REMURA_SQUALINCOME_MONITOR_ENABLED=1\n"
            "REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1\n"
            "TOKEN=EXAMPLE_NOT_EXPOSED\n")
        self.state=self.private/"autoupdate-state.json"
        self.state.write_text(json.dumps({
            "enabled":True, "installedSha":m.BASE_SHA,
            "state":"data_only", "targetSha":"b"*40, "skippedSha":"b"*40,
            "failedSha":""
        }))
        self.dbfile=self.private/"remura-prices.sqlite3"
        with sqlite3.connect(self.dbfile) as db:
            db.execute("CREATE TABLE prices(symbol TEXT)")
            db.execute("CREATE TABLE status(key TEXT)")
        self.previous={}
        for name in m.EXISTING_FILES:
            dest=self.root/name
            dest.parent.mkdir(parents=True,exist_ok=True)
            data=(b"v1.59 banner 03/11/2026 00:08 (Italia)"
                  if name=="nav.js" else ("v158 "+name).encode())
            dest.write_bytes(data)
            self.previous[name]=(data,0,0,0o600)
        normalized=dict(self.previous)
        nav=self.previous["nav.js"][0].replace(
            b"03/11/2026 00:08 (Italia)",m.OLD_STAMP)
        normalized["nav.js"]=(nav,0,0,0o600)
        self.patches=[
            patch.object(m,"APP",self.root),patch.object(m,"PRIVATE",self.private),
            patch.object(m,"BACKUPS",self.backups),patch.object(m,"WORK",self.work),
            patch.object(m,"BASE_BLOBS",{k:m.git_blob(v[0])
                          for k,v in normalized.items()}),
            patch.object(m.os,"geteuid",return_value=0),
            patch.object(m.os,"fchown"),
            patch.object(m,"unit",side_effect=lambda operation,name:
                "active" if name==m.SERVICE else "inactive"),
            patch.object(m,"healthy",return_value=True),
            patch.object(m,"verify_target"),
            patch.object(m,"remote_doc",return_value={"sha":TARGET}),
            patch.object(m.subprocess,"run",
                         return_value=types.SimpleNamespace(returncode=0)),
        ]
        for p in self.patches:p.start()
        self.addCleanup(lambda:[p.stop() for p in reversed(self.patches)])
        self.staged={p:b"new-"+p.encode() for p in m.FILES}
        self.staged["nav.js"]=b"REMURA Aggiornamento v1.60 "+m.PREPARED_STAMP
        self.staged["sw.js"]=b"remura-shell-v74-v1.60"
        self.staged[m.BACKUP_MODULE]=(
            b"def create_backup():\n    return ['RESTORE_TEST=OK']\n")

    def test_exact_v158_base_and_new_file_must_not_exist(self):
        self.assertEqual(len(m.EXISTING_FILES),15)
        self.assertEqual(len(m.FILES),16)
        m.verify_live_v159(m.local_files())
        tampered=self.root/"scripts/private_server.py"
        tampered.write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError,"LIVE_V159_DIVERGED"):
            m.verify_live_v159(m.local_files())
        tampered.write_bytes(self.previous["scripts/private_server.py"][0])
        new=self.root/m.NEW_FILE
        new.write_bytes(b"unexpected")
        with self.assertRaisesRegex(RuntimeError,"NEW_MODULE_ALREADY_PRESENT"):
            m.local_files()

    def test_flag_on_is_required_and_not_modified(self):
        m.verify_flag_on()
        before=self.env.read_bytes()
        self.env.write_bytes(before.replace(
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1",
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0"))
        with self.assertRaisesRegex(RuntimeError,"POST_INGEST_FLAG_NOT_ON"):
            m.verify_flag_on()
        self.env.write_bytes(before)
        m.verify_flag_on()

    def test_italian_banner_uses_real_apply_clock(self):
        fixed=dt.datetime(2026,11,3,8,15,tzinfo=ZoneInfo("Europe/Rome"))
        stamped=m.release_stamp(self.staged,fixed)
        self.assertIn(b"03/11/2026 08:15 (Italia)",stamped["nav.js"])
        self.assertNotIn(b"preparazione",stamped["nav.js"])
        self.assertEqual(stamped[m.NEW_FILE],self.staged[m.NEW_FILE])

    def test_readonly_check_accepts_data_only_state_but_not_bad_sha(self):
        before=self.state.read_bytes()
        original={p:(self.root/p).read_bytes() for p in m.EXISTING_FILES}
        with patch.object(m,"candidate",return_value=self.staged), \
             patch.object(m,"atomic_write") as write, \
             patch.object(m,"atomic_create") as create:
            m.preflight(TARGET)
            write.assert_not_called()
            create.assert_not_called()
        self.assertEqual(self.state.read_bytes(),before)
        self.assertEqual({p:(self.root/p).read_bytes() for p in m.EXISTING_FILES},
                         original)
        self.assertEqual(list(self.backups.iterdir()),[])
        self.assertFalse((self.root/m.NEW_FILE).exists())
        self.state.write_text(json.dumps({
            "enabled":True,"installedSha":"b"*40,"state":"manual_required"}))
        with patch.object(m,"candidate",return_value=self.staged):
            with self.assertRaisesRegex(RuntimeError,"STATE_UNEXPECTED"):
                m.preflight(TARGET)

    def test_candidate_reads_immutable_zip_and_rejects_old_nav_version(self):
        staged={p:(ROOT/p).read_bytes() for p in (*m.FILES,m.BACKUP_MODULE)}
        # The v1.60 installer is immutable historical release tooling.
        # Rebuild its original versioned fixture in-memory when current
        # source has advanced, retaining the old ZIP, blob and cache guards.
        for page in (p for p in m.FILES if p.endswith(".html")):
            staged[page]=staged[page].replace(b"nav.js?v=161",b"nav.js?v=160")
        staged["nav.js"]=(staged["nav.js"]
            .replace(b"Aggiornamento v1.61",b"Aggiornamento v1.60")
            .replace(b"03/11/2026 13:06 (Italia, preparazione)",m.PREPARED_STAMP))
        staged["sw.js"]=staged["sw.js"].replace(
            b"remura-shell-v75-v1.61-batch-timing",
            b"remura-shell-v74-v1.60-squalincome-freshness")
        self.assertTrue(all(b"nav.js?v=160" in staged[p] for p in m.FILES
                            if p.endswith(".html")))
        self.assertIn(b"remura-shell-v74-v1.60",staged["sw.js"])
        def fake_run(files):
            tree={"truncated":False,"tree":[
                {"type":"blob","path":p,"sha":m.git_blob(data)}
                for p,data in files.items()
            ]}
            archive=io.BytesIO()
            with zipfile.ZipFile(archive,"w") as z:
                for p,data in files.items():
                    z.writestr("verified-root/"+p,data)
            return lambda url,cap=m.MAX_ZIP: (
                json.dumps(tree).encode() if "/git/trees/" in url
                else archive.getvalue())
        with patch.object(m,"api_read",side_effect=fake_run(staged)):
            self.assertEqual(m.candidate(TARGET),staged)
        changed=dict(staged)
        changed["asset.html"]=changed["asset.html"].replace(
            b"nav.js?v=160",b"nav.js?v=158")
        with patch.object(m,"api_read",side_effect=fake_run(changed)):
            with self.assertRaisesRegex(RuntimeError,"PAGE_CACHE_VERSION_MISMATCH"):
                m.candidate(TARGET)

    def test_apply_and_manual_rollback_preserve_env_state_database(self):
        state=self.state.read_bytes()
        env=self.env.read_bytes()
        db=self.dbfile.read_bytes()
        old={p:(self.root/p).read_bytes() for p in m.EXISTING_FILES}
        with patch.object(m,"candidate",return_value=self.staged), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            m.apply(TARGET)
            self.assertIn("RILASCIO_V160=OK",out.getvalue())
        self.assertTrue((self.root/m.NEW_FILE).is_file())
        self.assertEqual((self.root/m.NEW_FILE).read_bytes(),
                         self.staged[m.NEW_FILE])
        rollback=list(self.backups.glob("rollback-v160-*"))
        self.assertEqual(len(rollback),1)
        manifest=json.loads((rollback[0]/"manifest.json").read_text())
        self.assertIsNone(manifest["files"][m.NEW_FILE]["old"])
        self.assertFalse((rollback[0]/m.NEW_FILE).exists())
        m.rollback_from(rollback[0])
        self.assertFalse((self.root/m.NEW_FILE).exists())
        self.assertEqual({p:(self.root/p).read_bytes() for p in m.EXISTING_FILES},
                         old)
        self.assertEqual(self.env.read_bytes(),env)
        self.assertEqual(self.state.read_bytes(),state)
        self.assertEqual(self.dbfile.read_bytes(),db)

    def test_apply_health_failure_automatically_removes_new_file(self):
        old={p:(self.root/p).read_bytes() for p in m.EXISTING_FILES}
        with patch.object(m,"candidate",return_value=self.staged), \
             patch.object(m,"wait_health",side_effect=[False,True]), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(RuntimeError,"POST_INSTALL_HEALTH"):
                m.apply(TARGET)
        self.assertIn("ROLLBACK=OK",out.getvalue())
        self.assertFalse((self.root/m.NEW_FILE).exists())
        self.assertEqual({p:(self.root/p).read_bytes() for p in m.EXISTING_FILES},
                         old)

    def test_explicit_rollback_refuses_changed_new_module(self):
        with patch.object(m,"candidate",return_value=self.staged):
            m.apply(TARGET)
        folder=next(self.backups.glob("rollback-v160-*"))
        (self.root/m.NEW_FILE).write_bytes(b"unexpected-tampering")
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_HASH_OR_LIVE_CHANGED"):
            m.rollback_from(folder)
        self.assertEqual((self.root/m.NEW_FILE).read_bytes(),
                         b"unexpected-tampering")


    def test_target_must_have_exact_main_green_ci_and_reviewed_files(self):
        calls=[]
        def documented(endpoint):
            calls.append(endpoint)
            if endpoint=="/commits/main":
                return {"sha":TARGET}
            if endpoint.startswith("/compare/"):
                paths=sorted(m.REQUIRED | {"tests/test_release_v158.py",
                                            "data/myfxbook/latest.json"})
                return {"status":"ahead","files":[{"filename":p} for p in paths]}
            if "/runs?" in endpoint:
                return {"workflow_runs":[{"head_sha":TARGET,
                    "head_branch":"main","event":"push","status":"completed",
                    "conclusion":"success"}]}
            raise AssertionError(endpoint)
        with patch.object(m,"remote_doc",side_effect=documented):
            ORIGINAL_VERIFY_TARGET(TARGET)
        self.assertEqual(sum("/runs?" in call for call in calls),2)
        with patch.object(m,"remote_doc",side_effect=lambda p:
                {"workflow_runs":[]} if "/runs?" in p else documented(p)):
            with self.assertRaisesRegex(RuntimeError,"CI_NOT_GREEN"):
                ORIGINAL_VERIFY_TARGET(TARGET)
        def unknown(endpoint):
            data=documented(endpoint)
            if endpoint.startswith("/compare/"):
                data["files"].append({"filename":"deploy/oracle/autoupdate.py"})
            return data
        with patch.object(m,"remote_doc",side_effect=unknown):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                ORIGINAL_VERIFY_TARGET(TARGET)
        with patch.object(m,"remote_doc",side_effect=lambda p:
                {"sha":"b"*40} if p=="/commits/main" else documented(p)):
            with self.assertRaisesRegex(RuntimeError,"MAIN_MOVED"):
                ORIGINAL_VERIFY_TARGET(TARGET)

    def test_nonimmutable_sha_is_rejected(self):
        with self.assertRaisesRegex(RuntimeError,"COMMIT_INVALID"):
            m.candidate("main")


    def test_pwa_allowlist_and_nine_page_release_guard(self):
        """Staged iPhone asset must load without exposing API content in SW cache."""
        pages=(
            "index.html","asset.html","mercati.html","forex.html","catalogo.html",
            "statistica-squali.html","stato-prezzi.html","fonti.html","impostazioni.html")
        self.assertEqual(len(m.FILES),16)
        self.assertEqual(len(pages),9)
        self.assertEqual(m.NEW_FILE,"squalincome-freshness-core.js")
        for page in pages:
            source=(ROOT/page).read_text("utf-8")
            self.assertIn("nav.js?v=161",source,page)
        nav=(ROOT/"nav.js").read_bytes()
        self.assertEqual(nav.count(b"03/11/2026 13:06 (Italia, preparazione)"),1)
        self.assertIn("REMURA · Aggiornamento v1.61".encode("utf-8"),nav)
        mercati=(ROOT/"mercati.html").read_text("utf-8")
        self.assertIn("squalincome-freshness-core.js?v=160",mercati)
        self.assertIn("squalincome-diagnostics.js?v=160",mercati)
        sw=(ROOT/"sw.js").read_text("utf-8")
        self.assertIn("remura-shell-v75-v1.61-batch-timing",sw)
        self.assertIn("./squalincome-freshness-core.js",sw)
        self.assertIn('url.pathname.includes("/private-api/")',sw)
        backend=(ROOT/"scripts/private_server.py").read_text("utf-8")
        self.assertIn('"squalincome-freshness-core.js"',backend)
        core=(ROOT/"squalincome-freshness-core.js").read_text("utf-8")
        self.assertIn("signalAuthorized:false",core)
        self.assertFalse(any("cvd" in name.lower() for name in m.FILES))

if __name__=="__main__":unittest.main()
