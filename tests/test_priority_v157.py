"""Offline no-network tests for guarded priority activation on VPS v1.57."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("priority_v157",ROOT/"deploy/oracle/priority_v157.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class TestPriorityActivation(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)
        self.private=self.root/"private"
        self.private.mkdir()
        self.backups=self.private/"predeploy-backups"
        self.backups.mkdir()
        self.work=self.root/"work"
        self.work.mkdir()
        (self.work/"lock").write_text("")
        self.env=self.private/"remura.env"
        self.secret=b"CTRADER_CLIENT_SECRET=SECRET_DO_NOT_EXPOSE"
        self.env.write_bytes(self.secret+b"\nMYFXBOOK_KEY=STAY_UNCHANGED\n")
        self.env.chmod(0o600)
        self.server=self.root/"scripts/private_server.py"
        self.server.parent.mkdir(parents=True)
        self.server.write_bytes(b"v157_python")
        self.state=self.private/"autoupdate-state.json"
        self.state.write_text(json.dumps({"installedSha":m.SHA_V156,"state":"up_to_date"}))
        self.patches=[
            patch.object(m,"APP",self.root),
            patch.object(m,"PRIVATE",self.private),
            patch.object(m,"ENV",self.env),
            patch.object(m,"BACKUPS",self.backups),
            patch.object(m,"WORK",self.work),
            patch.object(m,"SERVER",self.server),
            patch.object(m,"STATE",self.state),
            patch.object(m.os,"geteuid",return_value=0),
            patch.object(m,"git_blob",return_value=m.V157_SERVER_BLOB),
            patch.object(m,"service_active",return_value=True),
            patch.object(m,"health",return_value=True),
            patch.object(m,"running_mode",return_value="0"),
            patch.object(m.os,"fchown"),
            patch.object(m.subprocess,"run",return_value=types.SimpleNamespace(
                returncode=1,stdout=b"inactive"))
        ]
        for p in self.patches:p.start()

    def tearDown(self):
        for p in reversed(self.patches):p.stop()
        self.temp.cleanup()

    def test_check_is_readonly_and_silent_about_secrets(self):
        before=self.env.read_bytes()
        with patch("sys.argv",["priority_v157.py","--check"]),\
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(m.main(),0)
        self.assertEqual(before,self.env.read_bytes())
        self.assertEqual(list(self.backups.iterdir()),[])
        text=output.getvalue()
        self.assertIn("PRIORITY_PREFLIGHT=OK",text)
        self.assertIn("NESSUNA_MODIFICA=SI",text)
        self.assertNotIn("SECRET",text)
        self.assertNotIn("MYFXBOOK",text)

    def test_edits_are_bounded_and_do_not_change_existing_secrets(self):
        original=self.env.read_bytes()
        enabled=m.edited(original,"1")
        self.assertEqual(m.environment_mode(enabled),"1")
        self.assertEqual(enabled.count(self.secret),1)
        self.assertIn(b"MYFXBOOK_KEY=STAY_UNCHANGED",enabled)
        self.assertEqual(m.environment_mode(m.edited(enabled,"0")),"0")
        self.assertEqual(m.environment_mode(m.edited(original,"0")),"0")
        self.assertEqual(m.edited(enabled,"1"),enabled)

    def test_enable_and_disable_with_state_backup_no_db_changes(self):
        before=self.env.read_bytes()
        def fake_running():
            return m.environment_mode(self.env.read_bytes())
        def fake_restart(mode):
            self.assertEqual(m.environment_mode(self.env.read_bytes()),mode)
        with patch.object(m,"running_mode",side_effect=fake_running),\
             patch.object(m,"restart_and_verify",side_effect=fake_restart),\
             contextlib.redirect_stdout(io.StringIO()) as stdout:
            m.change("1")
            self.assertIn("PRIORITA=ATTIVA",stdout.getvalue())
            self.assertEqual(m.environment_mode(self.env.read_bytes()),"1")
            m.change("1")  # idempotent
            m.change("0")
        self.assertEqual(m.environment_mode(self.env.read_bytes()),"0")
        self.assertEqual(self.secret in self.env.read_bytes(),True)
        self.assertEqual(len(list(self.backups.glob("priority-v157-env-*.bak"))),2)
        self.assertTrue(all((p.stat().st_mode & 0o777)==0o600 for p in self.backups.iterdir()))
        self.assertEqual(json.loads(self.state.read_text())["state"],"up_to_date")
        self.assertEqual(before.count(self.secret),self.env.read_bytes().count(self.secret))

    def test_failed_restart_restores_previous_env_and_restarts(self):
        old=self.env.read_bytes()
        attempts=[]
        def fake_restart(mode):
            attempts.append(mode)
            if mode=="1":
                raise RuntimeError("STOP_SERVICE_RESTART")
            self.assertEqual(m.environment_mode(self.env.read_bytes()),"0")
        with patch.object(m,"running_mode",return_value="0"),\
             patch.object(m,"restart_and_verify",side_effect=fake_restart),\
             contextlib.redirect_stdout(io.StringIO()) as output:
            with self.assertRaisesRegex(RuntimeError,"SERVICE_RESTART"):
                m.change("1")
        self.assertEqual(attempts,["1","0"])
        self.assertEqual(self.env.read_bytes(),old)
        self.assertIn("ROLLBACK_CONFIGURAZIONE=OK",output.getvalue())

    def test_invalid_duplicate_or_injected_env_flags_fail_closed(self):
        for bad in (
            b"REMURA_PRIORITY_COLLECTOR_ENABLED=3\n",
            b"export REMURA_PRIORITY_COLLECTOR_ENABLED=1\n",
            b"REMURA_PRIORITY_COLLECTOR_ENABLED=0\nREMURA_PRIORITY_COLLECTOR_ENABLED=1\n",
            b"REMURA_PRIORITY_COLLECTOR_ENABLED=1 #comment\n",
            b"REMURA_PRIORITY_COLLECTOR_ENABLED=1\x00INJECT=1\n",
        ):
            self.env.write_bytes(self.secret+b"\n"+bad)
            with self.assertRaisesRegex(RuntimeError,"STOP_"):
                m.preflight()

    def test_wrong_server_or_autoupdater_blocks_without_writes(self):
        self.env.write_bytes(self.secret+b"\n")
        before=self.env.read_bytes()
        with patch.object(m,"git_blob",return_value="0"*40):
            with self.assertRaisesRegex(RuntimeError,"SERVER_NOT_V157"):
                m.preflight()
        self.state.write_text(json.dumps({"installedSha":"a"*40,"state":"manual_required"}))
        with self.assertRaisesRegex(RuntimeError,"AUTOUPDATE_STATE_UNEXPECTED"):
            m.preflight()
        self.assertEqual(self.env.read_bytes(),before)

    def test_emergency_disable_after_state_changes_but_never_enable(self):
        self.env.write_bytes(self.secret+b"\nREMURA_PRIORITY_COLLECTOR_ENABLED=1\n")
        self.state.write_text(json.dumps({"installedSha":"b"*40,"state":"manual_required"}))
        with self.assertRaisesRegex(RuntimeError,"AUTOUPDATE_STATE_UNEXPECTED"):
            m.preflight(disabling=False)
        self.assertEqual(m.preflight(disabling=True)[2],"1")
        with patch.object(m,"running_mode",return_value="1"),\
             patch.object(m,"restart_and_verify",return_value=None):
            m.change("0")
        self.assertEqual(m.environment_mode(self.env.read_bytes()),"0")

    def test_lock_and_env_symlink_guard(self):
        (self.work/"lock").unlink()
        (self.work/"lock").symlink_to(self.env)
        with self.assertRaisesRegex(RuntimeError,"LOCK_FILE"):
            m.change("1")
        self.env.unlink()
        self.env.symlink_to(self.server)
        with self.assertRaisesRegex(RuntimeError,"FILES_INVALID"):
            m.preflight()


if __name__=="__main__":
    unittest.main()
