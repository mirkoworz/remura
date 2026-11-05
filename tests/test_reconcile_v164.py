"""REMURA v1.64 state-only reconcile guards; offline and immutable SHA pinned."""
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("reconcile_v164",ROOT/"deploy/oracle/reconcile_v164.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
TARGET="a"*40
FILES=("scripts/private_server.py","nav.js","sw.js","index.html","asset.html",
"mercati.html","forex.html","catalogo.html","statistica-squali.html",
"stato-prezzi.html","fonti.html","impostazioni.html","splash.js","splash.css","splash-mascot.webp")

class ReconcileV164Tests(unittest.TestCase):
    def test_pins_and_no_unreviewed_code(self):
        self.assertEqual(m.OLD,"16fb7c84a130a2e54f849fa7eadddba4f62455bf")
        self.assertEqual(m.RELEASE_SHA,"bb3c35da03eb9c28e86fe9f5dd52765441ca9391")
        self.assertEqual(m.RELEASE_BLOB,"5aeb523d92d27405564ebddcaef5c9e44971c60d")
        self.assertEqual(m.PREPARED_STAMP,b"05/11/2026 18:03 (Italia, preparazione)")
        self.assertEqual(m.WORKFLOWS,("price-checks.yml","insights-checks.yml"))
        self.assertNotIn("scripts/private_server.py",m.ALLOWED_CODE)
        self.assertNotIn("scripts/ctrader_feed.py",m.ALLOWED_CODE)

    def test_verify_exact_files_and_runtime_italian_stamp(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            files={p:b"original-"+p.encode() for p in FILES}
            files["nav.js"]=b"banner "+m.PREPARED_STAMP
            for name,payload in files.items():
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_bytes(payload.replace(m.PREPARED_STAMP,b"05/11/2026 19:15 (Italia)") if name=="nav.js" else payload)
            with patch.object(m,"APP",root):
                actual=m.correct_live_code(files,{"FILES":FILES})
                self.assertEqual(tuple(actual),FILES)
                (root/"splash.js").write_bytes(b"tampered")
                with self.assertRaisesRegex(RuntimeError,"LIVE_FILE_DIVERGED"):
                    m.correct_live_code(files,{"FILES":FILES})

    def test_diff_and_two_ci_checks(self):
        required={
          "nav.js","sw.js","splash.js","splash.css",
          "index.html","asset.html","mercati.html","forex.html",
          "catalogo.html","statistica-squali.html","stato-prezzi.html",
          "fonti.html","impostazioni.html",
          "deploy/oracle/release_v164.py","deploy/oracle/reconcile_v164.py"
        }
        visited=[]
        def remote(path,extra=()):
            if path=="/commits/main":return {"sha":TARGET}
            if path.startswith("/compare/"):return {"status":"ahead","files":[{"filename":p} for p in sorted(required|set(extra))]}
            if "/actions/workflows/" in path:
                visited.append(path)
                return {"workflow_runs":[{"head_sha":TARGET,"head_branch":"main","event":"push","status":"completed","conclusion":"success"}]}
            raise AssertionError("unexpected API")
        with patch.object(m,"json_api",side_effect=remote):
            m.validate_target(TARGET)
        self.assertEqual(len(visited),2)
        with patch.object(m,"json_api",side_effect=lambda p:remote(p,{"scripts/ctrader_feed.py"})):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                m.validate_target(TARGET)

    def test_rollback_and_consistent_sqlite_snapshot_required(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);bk=root/"predeploy-backups";bk.mkdir()
            live={p:b"new-"+p.encode() for p in FILES}
            for name,raw in live.items():
                dest=root/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(raw)
            backup=bk/"rollback-v164-proof";backup.mkdir()
            manifest={"schema":"remura-v164-rollback-v1","commit":TARGET,"files":{}}
            for name,raw in live.items():
                prior=b"old-"+name.encode()
                dest=backup/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(prior)
                manifest["files"][name]={"new":hashlib.sha256(raw).hexdigest(),"old":hashlib.sha256(prior).hexdigest()}
            (backup/"manifest.json").write_text(json.dumps(manifest))
            snapshot=bk/"backup-v156-proof";snapshot.mkdir()
            image=snapshot/"remura-prices.sqlite3"
            with sqlite3.connect(image) as db:db.execute("CREATE TABLE x(a INTEGER)")
            (snapshot/"manifest.txt").write_text("sha256="+hashlib.sha256(image.read_bytes()).hexdigest()+"\n")
            with patch.object(m,"APP",root),patch.object(m,"BACKUPS",bk):
                m.backups_present(FILES,TARGET)
                (backup/"manifest.json").write_text("{}")
                with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
                    m.backups_present(FILES,TARGET)

if __name__=="__main__":unittest.main()
