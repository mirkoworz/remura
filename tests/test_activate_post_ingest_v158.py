"""Offline only: v1.58 private post-ingest guarded opt-in."""
import contextlib
import importlib.util
import io
import json
import stat
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location(
    "post_ingest_enable", ROOT/"deploy/oracle/activate_post_ingest_v158.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.private=self.root/"private";self.private.mkdir()
        self.work=self.root/"work";self.work.mkdir()
        self.backups=self.private/"predeploy-backups";self.backups.mkdir()
        (self.work/"lock").touch()
        self.env=self.private/"remura.env"
        self.env.write_bytes(
            b"# example config\nREMURA_COLLECTOR_ENABLED=1\n"
            b"REMURA_PRIORITY_COLLECTOR_ENABLED=1\n"
            b"TOKEN=\"EXAMPLE_SECRET_NOT_PRINTED\"\n"
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0\n")
        self.old=self.env.read_bytes()
        self.env.chmod(0o640)
        (self.private/"autoupdate-state.json").write_text(json.dumps(
            {"enabled":True,"state":"up_to_date","installedSha":m.EXPECTED,
             "failedSha":""}))
        patches=[
            patch.object(m,"ROOT",self.root),
            patch.object(m,"PRIVATE",self.private),
            patch.object(m,"WORK",self.work),
            patch.object(m,"BACKUPS",self.backups),
            patch.object(m,"LOCK",self.work/"lock"),
            patch.object(m,"ENV",self.env),
            patch.object(m,"STATE",self.private/"autoupdate-state.json"),
            patch.object(m.os,"geteuid",return_value=0),
            patch.object(m.os,"fchown"),
            patch.object(m,"active",return_value=True),
            patch.object(m,"healthy",return_value=True),
            patch.object(m,"live_flag",side_effect=lambda:
                "1" if b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1"
                in self.env.read_bytes() else "0"),
            patch.object(m,"restart"),
            patch.object(m,"cmd",return_value=types.SimpleNamespace(
                returncode=1,stdout=b"inactive")),
        ]
        for p in patches:p.start()
        self.addCleanup(lambda:[p.stop() for p in reversed(patches)])

    def test_activate_preserves_secrets_and_creates_private_backup(self):
        with contextlib.redirect_stdout(io.StringIO()) as out:
            m.apply()
        self.assertIn("ATTIVAZIONE_POST_INGEST_V158=OK",out.getvalue())
        self.assertNotIn("EXAMPLE_SECRET_NOT_PRINTED",out.getvalue())
        fresh=self.env.read_bytes()
        self.assertEqual(fresh.replace(
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=1",
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0"),self.old)
        self.assertEqual(stat.S_IMODE(self.env.stat().st_mode),0o640)
        backups=list(self.backups.glob("post-ingest-v158-before-*.env"))
        self.assertEqual(len(backups),1)
        self.assertEqual(backups[0].read_bytes(),self.old)
        self.assertEqual(stat.S_IMODE(backups[0].stat().st_mode),0o600)

    def test_restart_failure_rolls_back(self):
        calls=[]
        def fail_first():
            calls.append(1)
            if len(calls)==1:raise RuntimeError("fake_restart_failure")
        with patch.object(m,"restart",side_effect=fail_first), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(RuntimeError,"fake_restart_failure"):
                m.apply()
        self.assertEqual(self.env.read_bytes(),self.old)
        self.assertEqual(len(calls),2)
        self.assertIn("ROLLBACK_CONFIG=OK",out.getvalue())

    def test_no_preexisting_flag_is_appended_only_once(self):
        self.env.write_bytes(self.old.replace(
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0\n",b""))
        with contextlib.redirect_stdout(io.StringIO()):
            m.apply()
        self.assertEqual(self.env.read_bytes().count(
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED="),1)

    def test_duplicates_are_rejected_before_backup(self):
        self.env.write_bytes(self.old+
            b"REMURA_SQUALINCOME_AFTER_INGEST_ENABLED=0\n")
        with self.assertRaisesRegex(RuntimeError,"STOP_FLAG_NOT_OFF"):m.apply()
        self.assertEqual(list(self.backups.iterdir()),[])

    def test_unexpected_sha_is_rejected(self):
        state=self.private/"autoupdate-state.json"
        state.write_text(json.dumps(
            {"enabled":True,"state":"up_to_date","installedSha":"b"*40}))
        with self.assertRaisesRegex(RuntimeError,"STOP_SHA_OR_STATE"):m.apply()
        self.assertEqual(self.env.read_bytes(),self.old)
        self.assertEqual(list(self.backups.iterdir()),[])

    def test_post_restart_health_or_flag_failure_rolls_back(self):
        with patch.object(m,"wait_health",
                          side_effect=lambda flag,attempts=12:flag=="0"), \
             contextlib.redirect_stdout(io.StringIO()) as out:
            with self.assertRaisesRegex(RuntimeError,
                     "STOP_POST_RESTART_HEALTH_OR_FLAG"):m.apply()
        self.assertEqual(self.env.read_bytes(),self.old)
        self.assertIn("ROLLBACK_CONFIG=OK",out.getvalue())

if __name__=="__main__":
    unittest.main()
