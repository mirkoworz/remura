#!/usr/bin/env python3
# REMURA v0.8.81 LAB — 14/11/2026 19:58 CET — synthetic only
import os,sqlite3,sys,tempfile,unittest
from pathlib import Path
from hashlib import sha256
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_detached_snapshots_v1 as s
import cvd_linux_host_evidence_v1 as h
import cvd_staged_runtime_preflight_v1 as p

class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.f=self.root/"core.sqlite3"
        with sqlite3.connect(self.f) as db:
            db.execute("CREATE TABLE sample (v INTEGER)")
            db.execute("INSERT INTO sample VALUES (42)")
        db.close();self.f.chmod(0o600)
        self.manifest={"core.sqlite3":sha256(self.f.read_bytes()).hexdigest()}
    def test_snapshot_only_memory_query_only_closed(self):
        before=self.f.read_bytes()
        with s.open_snapshots(self.root,self.manifest,explicit=True) as (db,private):
            self.assertIsNone(private);self.assertEqual(db.execute("SELECT v FROM sample").fetchone(),(42,))
            self.assertEqual(db.execute("PRAGMA query_only").fetchone(),(1,))
            self.assertEqual(db.execute("PRAGMA database_list").fetchone()[2],"")
            with self.assertRaises(sqlite3.DatabaseError):db.execute("DELETE FROM sample")
        with self.assertRaises(sqlite3.ProgrammingError):db.execute("SELECT 1")
        self.assertEqual(before,self.f.read_bytes())
    def test_manifest_mismatch_and_explicit(self):
        for manifest,explicit in ((self.manifest,False),({"core.sqlite3":"0"*64},True),({"../core.sqlite3":"0"*64},True)):
            with self.assertRaises(ValueError):
                with s.open_snapshots(self.root,manifest,explicit=explicit):pass
    def test_sidecar_permissions_and_size(self):
        side=self.root/"core.sqlite3-wal";side.touch()
        with self.assertRaises(ValueError):
            with s.open_snapshots(self.root,self.manifest,explicit=True):pass
        side.unlink();self.f.chmod(0o644)
        with self.assertRaises(ValueError):
            with s.open_snapshots(self.root,self.manifest,explicit=True):pass
        self.f.chmod(0o600)
        with patch.object(s,"MAX_TOTAL_BYTES",100):
            with self.assertRaises(ValueError):
                with s.open_snapshots(self.root,self.manifest,explicit=True):pass
    def test_symlink_rejected(self):
        target=self.root/"original";self.f.rename(target);self.f.symlink_to(target)
        with self.assertRaises(OSError):
            with s.open_snapshots(self.root,self.manifest,explicit=True):pass
    def test_bad_header(self):
        raw=bytearray(self.f.read_bytes());raw[18]=2
        self.f.write_bytes(raw)
        with self.assertRaises(ValueError):
            with s.open_snapshots(self.root,{"core.sqlite3":sha256(raw).hexdigest()},explicit=True):pass
    def test_distinct_two_sources(self):
        f=self.root/"private.sqlite3"
        with sqlite3.connect(f) as db:db.execute("CREATE TABLE another (v INTEGER)")
        db.close();f.chmod(0o600)
        manifest={**self.manifest,"private.sqlite3":sha256(f.read_bytes()).hexdigest()}
        with s.open_snapshots(self.root,manifest,explicit=True) as (core,private):
            self.assertIsNot(core,private);self.assertEqual(private.execute("PRAGMA query_only").fetchone(),(1,))
    def test_cgroup_bounds(self):
        self.assertEqual(h.bounds(1000,8,[("800","200","200000 100000"),("700","300","max 100000")]),(400,2))
        with self.assertRaises(ValueError):h.bounds(1000,8,[("max","0","50000 100000")])
    def test_block_before_snapshots(self):
        with patch.object(p,"sample_host",return_value={}),patch.object(p,"assess",return_value={"status":"BLOCKED"}),patch.object(p,"open_snapshots") as op:
            with self.assertRaises(ValueError):
                with p.prepared(self.root,self.manifest,budget={},explicit=True):pass
            op.assert_not_called()
    def test_recheck_after_snapshot(self):
        ok={"status":"ONE_SHOT_TEST_PREVIEW_PLAUSIBLE"}
        with patch.object(p,"sample_host",return_value={}),patch.object(p,"assess",side_effect=[ok,{"status":"BLOCKED"}]):
            with self.assertRaises(ValueError):
                with p.prepared(self.root,self.manifest,budget={},explicit=True):pass
        with patch.object(p,"sample_host",return_value={}),patch.object(p,"assess",return_value=ok) as call:
            with p.prepared(self.root,self.manifest,budget={},explicit=True) as (db,_,gate):
                self.assertEqual(gate,ok);self.assertEqual(db.execute("SELECT v FROM sample").fetchone(),(42,))
            self.assertEqual(call.call_count,2)
if __name__=="__main__":unittest.main()
