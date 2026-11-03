"""Offline safety tests for v1.61 immutable code + SHA-only reconciliation."""
import contextlib
import datetime as dt
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import os
import sqlite3
import stat
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("reconcile_v161",ROOT/"deploy/oracle/reconcile_v161.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

FILES=(
    "scripts/private_server.py","scripts/batch_timing.py",
    "nav.js","sw.js","index.html","asset.html",
    "mercati.html","forex.html","catalogo.html","statistica-squali.html",
    "stato-prezzi.html","fonti.html","impostazioni.html",
)
TARGET="a"*40
STAMPED=b"03/11/2026 08:15 (Italia)"

def files_fixture():
    base={name:("asset-"+name).encode("ascii") for name in FILES}
    base["nav.js"]=b'/* Aggiornamento v1.61 - 03/11/2026 13:06 (Italia, preparazione) */'
    return base

class ReconcileTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.private=self.root/"private";self.private.mkdir()
        self.backups=self.private/"predeploy-backups";self.backups.mkdir()
        self.work=self.root/"work";self.work.mkdir()
        self.state=self.private/"autoupdate-state.json"
        self.state.write_text(json.dumps({"enabled":True,"installedSha":m.OLD,
            "targetSha":m.OLD,"state":"up_to_date","failedSha":"",
            "secret_field":"SECRET_NOT_PRINTED"}))
        self.state.chmod(0o600)
        self.expected=files_fixture()
        for name,data in self.expected.items():
            path=self.root/name;path.parent.mkdir(parents=True,exist_ok=True)
            if name=="nav.js":data=data.replace(m.PREPARED_STAMP,STAMPED)
            path.write_bytes(data)
        self.patchers=[
            patch.object(m,"APP",self.root),patch.object(m,"PRIVATE",self.private),
            patch.object(m,"BACKUPS",self.backups),patch.object(m,"WORK",self.work),
            patch.object(m,"STATE",self.state)]
        for p in self.patchers:p.start()
    def tearDown(self):
        for p in reversed(self.patchers):p.stop()
        self.temp.cleanup()

    def test_live_exact_match_with_only_timestamp_substitution(self):
        self.assertEqual(m.correct_live_code(self.expected,{"FILES":FILES}),FILES)
        target=self.root/"scripts/private_server.py"
        target.write_bytes(b"modified")
        with self.assertRaisesRegex(RuntimeError,"LIVE_FILE_DIVERGED"):
            m.correct_live_code(self.expected,{"FILES":FILES})
        target.write_bytes(self.expected["scripts/private_server.py"])
        p=self.root/"nav.js"
        p.write_bytes(self.expected["nav.js"].replace(m.PREPARED_STAMP,
                    b"02/11/2026 16:55 (Italia)\\nSECRET_ADDED"))
        with self.assertRaisesRegex(RuntimeError,"LIVE_STAMP_INVALID|LIVE_NAV_DIVERGED"):
            m.correct_live_code(self.expected,{"FILES":FILES})

    def test_backup_manifest_and_sqlite_backup_required(self):
        self.make_valid_archives()
        m.backups_present(FILES,TARGET)
        (self.root/"sw.js").write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
            m.backups_present(FILES,TARGET)
        (self.root/"sw.js").write_bytes(self.expected["sw.js"])
        for folder in self.backups.glob("backup-v156-*"):
            (folder/"manifest.txt").write_text("sha256="+("0"*64))
        with self.assertRaisesRegex(RuntimeError,"SQLITE_BACKUP_UNVERIFIED"):
            m.backups_present(FILES,TARGET)

    def make_valid_archives(self):
        folder=self.backups/"rollback-v161-proof";folder.mkdir()
        data={"schema":"remura-v161-rollback-v1","commit":TARGET,"files":{}}
        for name in FILES:
            target=folder/name
            digest=hashlib.sha256((self.root/name).read_bytes()).hexdigest()
            if name=="scripts/batch_timing.py":
                data["files"][name]={"old":None,"new":digest}
                continue
            old=("prior-"+name).encode("ascii")
            target.parent.mkdir(exist_ok=True,parents=True)
            target.write_bytes(old)
            data["files"][name]={"old":hashlib.sha256(old).hexdigest(),
                                "new":digest}
        (folder/"manifest.json").write_text(json.dumps(data))
        snap=self.backups/"backup-v156-proof";snap.mkdir()
        file=snap/"remura-prices.sqlite3"
        with sqlite3.connect(file) as db:
            db.execute("CREATE TABLE verify (id INTEGER)")
            db.execute("INSERT INTO verify VALUES (1)")
        h=hashlib.sha256(file.read_bytes()).hexdigest()
        (snap/"manifest.txt").write_text("remura-v156-sqlite\nsha256="+h+"\n")

    def test_failed_state_blocks_application(self):
        state=json.loads(self.state.read_text())
        state["failedSha"]="b"*40
        self.state.write_text(json.dumps(state))
        with self.assertRaisesRegex(RuntimeError,"FAILED_RELEASE_PENDING"):
            m.state_read()
        state["failedSha"]=""
        state["installedSha"]="b"*40
        self.state.write_text(json.dumps(state))
        with self.assertRaisesRegex(RuntimeError,"STATE_UNEXPECTED"):
            m.state_read()

    def test_manual_required_state_is_accepted_when_old_sha_is_exact(self):
        state=json.loads(self.state.read_text())
        state["state"]="manual_required"
        self.state.write_text(json.dumps(state))
        self.assertEqual(m.state_read()[0]["state"],"manual_required")

    def test_state_data_only_still_points_to_old_code_and_is_accepted(self):
        state=json.loads(self.state.read_text())
        state["state"]="data_only"
        state["targetSha"]="b"*40
        state["skippedSha"]="b"*40
        self.state.write_text(json.dumps(state))
        self.assertEqual(m.state_read()[0]["installedSha"],m.OLD)

    def test_new_module_must_have_no_old_rollback_copy(self):
        self.make_valid_archives()
        m.backups_present(FILES,TARGET)
        folder=next(self.backups.glob("rollback-v161-*"))
        module=folder/"scripts/batch_timing.py"
        module.parent.mkdir(exist_ok=True,parents=True)
        module.write_bytes(b"unexpected old file")
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
            m.backups_present(FILES,TARGET)

    def test_target_allowlist_and_two_ci_gates_are_required(self):
        calls=[]
        allowed=[
            "scripts/private_server.py", "scripts/batch_timing.py",
            "deploy/oracle/reconcile_v161.py", "deploy/oracle/release_v161.py",
            "nav.js", "sw.js", "index.html", "asset.html", "mercati.html",
            "forex.html", "catalogo.html", "statistica-squali.html",
            "stato-prezzi.html", "fonti.html", "impostazioni.html",
        ]
        def api(endpoint):
            calls.append(endpoint)
            if endpoint=="/commits/main":
                return {"sha":TARGET}
            if endpoint.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":p} for p in allowed]}
            if "/runs?" in endpoint:
                return {"workflow_runs":[{
                    "head_sha":TARGET,"head_branch":"main",
                    "event":"push","status":"completed","conclusion":"success"}]}
            raise AssertionError(endpoint)
        with patch.object(m,"json_api",side_effect=api):
            m.validate_target(TARGET)
            self.assertEqual(sum("/runs?" in x for x in calls),2)
        def unsafe(endpoint):
            if endpoint.startswith("/compare/"):
                return {"status":"ahead","files":[
                    {"filename":p} for p in (
                    *allowed, ".github/workflows/secret-leaking.yml")]}
            return api(endpoint)
        with patch.object(m,"json_api",side_effect=unsafe):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                m.validate_target(TARGET)
        def failed_ci(endpoint):
            if "/runs?" in endpoint:return {"workflow_runs":[]}
            return api(endpoint)
        with patch.object(m,"json_api",side_effect=failed_ci):
            with self.assertRaisesRegex(RuntimeError,"CI_NOT_GREEN"):
                m.validate_target(TARGET)

    def test_check_is_readonly_and_secret_free(self):
        before=self.state.read_bytes()
        self.make_valid_archives()
        # Test shell entry point without real root, networking or systemctl.
        def mocked_inspect(_):
            state,raw,meta=m.state_read()
            return state,raw,meta,FILES
        with patch.object(m,"inspect",side_effect=mocked_inspect),\
             patch.object(sys,"argv",["reconcile_v161.py","--check","--target",TARGET]),\
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(),0)
        self.assertIn("RICONCILIAZIONE_V161=VERIFICATA",output.getvalue())
        self.assertIn("STATO_INVARIATO=SI",output.getvalue())
        self.assertNotIn("SECRET_NOT_PRINTED",output.getvalue())
        self.assertEqual(self.state.read_bytes(),before)
        self.assertEqual(len(list(self.backups.glob("state-before-v161-*"))),0)

    def test_apply_changes_only_state_and_preserves_backup(self):
        original=self.state.read_bytes()
        _,raw,meta=m.state_read()
        files_before={name:(self.root/name).read_bytes() for name in FILES}
        with patch.object(m.os,"fchown"):
            m.commit_state(TARGET,json.loads(raw),raw,meta)
        state=json.loads(self.state.read_text())
        self.assertEqual(state["installedSha"],TARGET)
        self.assertEqual(state["targetSha"],TARGET)
        self.assertEqual(state["state"],"up_to_date")
        self.assertEqual(state["secret_field"],"SECRET_NOT_PRINTED")
        snaps=list(self.backups.glob("state-before-v161-*.json"))
        self.assertEqual(len(snaps),1)
        self.assertEqual(snaps[0].read_bytes(),original)
        self.assertEqual(stat.S_IMODE(snaps[0].stat().st_mode),0o600)
        self.assertEqual({name:(self.root/name).read_bytes() for name in FILES},
                         files_before)


    def test_rollback_manifest_requires_original_files_and_correct_commit(self):
        self.make_valid_archives()
        m.backups_present(FILES,TARGET)
        folder=next(self.backups.glob("rollback-v161-*"))
        manifest=json.loads((folder/"manifest.json").read_text())
        manifest["commit"]="b"*40
        (folder/"manifest.json").write_text(json.dumps(manifest))
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
            m.backups_present(FILES,TARGET)
        manifest["commit"]=TARGET
        (folder/"manifest.json").write_text(json.dumps(manifest))
        (folder/"nav.js").write_bytes(b"tampered")
        with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
            m.backups_present(FILES,TARGET)

    def test_live_stamp_supports_new_italian_release_day(self):
        self.assertEqual(m.correct_live_code(self.expected,{"FILES":FILES}),FILES)
        path=self.root/"nav.js"
        original=path.read_bytes()
        path.write_bytes(original.replace(b"03/11/2026 08:15 (Italia)",
                                          b"03/11/2026 08:16 (Italia)"))
        self.assertEqual(m.correct_live_code(self.expected,{"FILES":FILES}),FILES)

    def test_release_script_pin_verification_refuses_unknown_source(self):
        with patch.object(m,"request",return_value=b"tampered"):
            with self.assertRaisesRegex(RuntimeError,"RELEASE_PIN_MISMATCH"):
                m.release_module()

if __name__=="__main__":
    unittest.main()
