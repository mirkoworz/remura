#!/usr/bin/env python3
# REMURA v0.8.86 LAB — 14/11/2026 20:43 CET — synthetic metadata only
import sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_staging_metadata_preflight_v1 as p
from test_cvd_runtime_resource_gate_v1 import NOW,fixture

class Tests(unittest.TestCase):
    def setUp(self):
        self.t=tempfile.TemporaryDirectory();self.addCleanup(self.t.cleanup)
        self.root=Path(self.t.name);self.f=self.root/"core.sqlite3"
        self.f.write_bytes(b"x"*4096);self.f.chmod(0o600)
        self.lock=self.root/p.LOCK;self.lock.touch(mode=0o600)
    def inspect(self,**kw):
        with patch.object(p,"sample_host",return_value=fixture()[0]),patch.object(p.time,"time_ns",return_value=NOW*1000000),patch.object(p,"_volume",return_value=(10*1024**3,5*1024**3)):
            return p.inspect(self.root,self.root,explicit=True,**kw)
    def test_metadata_only_invalid_sqlite_not_admitted(self):
        before=self.f.read_bytes()
        r=self.inspect()
        self.assertEqual(r["status"],"METADATA_PLAUSIBLE_ONLY")
        self.assertEqual(r["snapshot_bytes"],4096)
        self.assertFalse(r["real_sqlite_opened"]);self.assertFalse(r["runtime_admitted"])
        self.assertEqual(self.f.read_bytes(),before)
    def test_size_sidecar_permissions(self):
        with patch.object(p,"MAX_TOTAL_BYTES",1000):
            self.assertEqual(self.inspect()["status"],"BLOCKED")
        wal=self.root/"core.sqlite3-wal";wal.touch()
        self.assertEqual(self.inspect()["status"],"BLOCKED");wal.unlink()
        self.f.chmod(0o644);self.assertEqual(self.inspect()["status"],"BLOCKED")
    def test_private_optional_and_symlink(self):
        self.assertEqual(self.inspect(include_private=True)["status"],"BLOCKED")
        f=self.root/"private.sqlite3";f.symlink_to(self.f)
        self.assertEqual(self.inspect(include_private=True)["status"],"BLOCKED")
    def test_host_and_disk_fail_closed(self):
        with patch.object(p,"sample_host",side_effect=ValueError),patch.object(p,"_volume",return_value=(10*1024**3,10)):
            r=p.inspect(self.root,self.root,explicit=True)
        self.assertIn("HOST_HEADROOM_UNVERIFIED",r["reasons"])
        self.assertIn("STATE_DISK_HEADROOM_FAILED",r["reasons"])
    def test_checklist_not_authorization(self):
        review={"b_checkout_sha":p.B_PIN,"d_checkout_sha":"a"*40,"authorized_detached_exports":True,
                "core_schema_and_restore_reviewed":True,"token_scopes_reviewed":True,
                "oracle_continuity_reviewed":True,"first_fx_receipt_verified":True,
                "private_execution_authorized":True,"no_live_changes":True,"fresh_quota_plan_reviewed":True}
        r=p.admission(metadata=self.inspect(),review=review,explicit=True)
        self.assertEqual(r["status"],"REVIEW_CHECKLIST_COMPLETE_ONLY")
        self.assertFalse(r["runtime_admitted"])
        review["first_fx_receipt_verified"]=False
        self.assertEqual(p.admission(metadata=self.inspect(),review=review,explicit=True)["status"],"BLOCKED")
    def test_explicit(self):
        with self.assertRaises(ValueError):p.inspect(self.root,self.root)
        with self.assertRaises(ValueError):p.admission(metadata={},review={})
if __name__=="__main__":unittest.main()
