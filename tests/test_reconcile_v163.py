"""v1.63 SHA-only reconciliation tests. All I/O is isolated; no network."""
import datetime as dt
import hashlib
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("reconcile_v163",ROOT/"deploy/oracle/reconcile_v163.py")
m=importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
FILES=("scripts/private_server.py","nav.js","sw.js","index.html","asset.html",
       "mercati.html","forex.html","catalogo.html","statistica-squali.html",
       "stato-prezzi.html","fonti.html","impostazioni.html",
       "splash.js","splash.css","splash-mascot.webp")
TARGET="a"*40
STAMP=b"05/11/2026 19:15 (Italia)"

class ReconcileV163Tests(unittest.TestCase):
    def test_pins_and_strict_diff_policy(self):
        self.assertEqual(m.OLD,"1568edefabc7bbdb7d06485d2b863b196a4e6155")
        self.assertEqual(m.RELEASE_SHA,"21281734e8e10540e57fef15d0cb728b890f8cd0")
        self.assertEqual(m.RELEASE_BLOB,"0214b8baf5ed3bdefebb21bbfd08204c8d99dd45")
        self.assertEqual(m.PREPARED_STAMP,b"05/11/2026 16:00 (Italia, preparazione)")
        self.assertIn("splash-mascot.webp",m.ALLOWED_CODE)
        self.assertNotIn("scripts/update_capital.py",m.ALLOWED_CODE)

    def test_exact_15_installed_files_and_stamped_banner(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);staged={p:b"file:"+p.encode() for p in FILES}
            staged["nav.js"]=b"REMURA "+m.PREPARED_STAMP
            for p,raw in staged.items():
                target=root/p;target.parent.mkdir(parents=True,exist_ok=True)
                target.write_bytes(raw.replace(m.PREPARED_STAMP,STAMP) if p=="nav.js" else raw)
            with patch.object(m,"APP",root):
                got=m.correct_live_code(staged,{"FILES":FILES})
                self.assertEqual(tuple(got),FILES)
                (root/"splash.js").write_bytes(b"malicious")
                with self.assertRaisesRegex(RuntimeError,"LIVE_FILE_DIVERGED"):
                    m.correct_live_code(staged,{"FILES":FILES})
                (root/"splash.js").write_bytes(staged["splash.js"])
                (root/"nav.js").write_bytes(b"wrong stamp")
                with self.assertRaisesRegex(RuntimeError,"LIVE_STAMP_INVALID"):
                    m.correct_live_code(staged,{"FILES":FILES})

    def test_reject_forged_file_list_and_new_asset_absent(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            with patch.object(m,"APP",root):
                with self.assertRaisesRegex(RuntimeError,"FILE_COUNT"):
                    m.correct_live_code({},{"FILES":("nav.js",)})
                with self.assertRaisesRegex(RuntimeError,"LIVE_FILE_INVALID"):
                    m.correct_live_code({x:b"f" for x in FILES},{"FILES":FILES})

    def test_rollback_and_sqlite_snapshot_verified(self):
        with tempfile.TemporaryDirectory() as td:
            import sqlite3
            root=Path(td);bk=root/"backups";bk.mkdir()
            live={p:b"new-"+p.encode() for p in FILES}
            for p,raw in live.items():
                out=root/p;out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
            folder=bk/"rollback-v163-proof";folder.mkdir()
            manifest={"schema":"remura-v163-rollback-v1","commit":TARGET,"files":{}}
            new=set(("splash.js","splash.css","splash-mascot.webp"))
            for p,raw in live.items():
                prev=None if p in new else b"old-"+p.encode()
                if prev is not None:
                    old=folder/p;old.parent.mkdir(parents=True,exist_ok=True);old.write_bytes(prev)
                manifest["files"][p]={"new":hashlib.sha256(raw).hexdigest(),
                                      "old":None if prev is None else hashlib.sha256(prev).hexdigest()}
            (folder/"manifest.json").write_text(json.dumps(manifest))
            snap=bk/"backup-v156-test";snap.mkdir()
            db=snap/"remura-prices.sqlite3"
            with sqlite3.connect(db) as c: c.execute("CREATE TABLE example(a int)")
            digest=hashlib.sha256(db.read_bytes()).hexdigest()
            (snap/"manifest.txt").write_text("sha256="+digest+"\n")
            with patch.object(m,"APP",root),patch.object(m,"BACKUPS",bk):
                m.backups_present(FILES,TARGET)
                (folder/"manifest.json").write_text("{}")
                with self.assertRaisesRegex(RuntimeError,"ROLLBACK_MANIFEST_UNVERIFIED"):
                    m.backups_present(FILES,TARGET)

    def test_state_only_reconciliation_keeps_old_state_backup(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);bk=root/"backups";bk.mkdir()
            state=root/"autoupdate-state.json"
            data={"enabled":True,"installedSha":m.OLD,"state":"manual_required",
                  "targetSha":TARGET,"failedSha":""}
            state.write_text(json.dumps(data))
            with patch.object(m,"STATE",state),patch.object(m,"BACKUPS",bk),patch.object(m,"PRIVATE",root):
                obj,raw,meta=m.state_read()
                m.commit_state(TARGET,obj,raw,meta)
                after=json.loads(state.read_text())
                self.assertEqual(after["installedSha"],TARGET)
                self.assertEqual(after["state"],"up_to_date")
                saved=list(bk.glob("state-before-v163-*.json"))
                self.assertEqual(len(saved),1)
                self.assertEqual(saved[0].read_bytes(),raw)
                self.assertEqual(json.loads(saved[0].read_bytes())["installedSha"],m.OLD)
                with self.assertRaisesRegex(RuntimeError,"STATE_UNEXPECTED"):
                    m.state_read()

    def test_change_list_rejects_unreviewed_collector_update(self):
        expected=set(FILES)|{"deploy/oracle/release_v163.py","deploy/oracle/reconcile_v163.py"}
        def api(path):
            if path=="/commits/main": return {"sha":TARGET}
            if path.startswith("/compare/"):
                return {"status":"ahead","files":[{"filename":p} for p in sorted(expected|{"scripts/ctrader_feed.py"})]}
            return {"workflow_runs":[{"head_sha":TARGET,"head_branch":"main",
                                     "event":"push","status":"completed","conclusion":"success"}]}
        with patch.object(m,"json_api",side_effect=api):
            with self.assertRaisesRegex(RuntimeError,"UNREVIEWED_FILES"):
                m.validate_target(TARGET)

if __name__=="__main__":unittest.main()
