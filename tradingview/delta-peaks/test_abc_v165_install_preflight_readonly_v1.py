# REMURA v0.8.147 LAB — 18/11/2026
import os,tempfile,unittest
from pathlib import Path
from abc_v165_install_preflight_readonly_v1 import regular_bytes,existing_application,work_report,MARKERS,unit_report
from abc_installed_baseline_readonly_v1 import blob
class Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve()
    def test_regular_read_and_symlink_rejected(self):
        p=self.root/"file";p.write_bytes(b"abc")
        self.assertEqual(regular_bytes(p,3)[0],b"abc")
        with self.assertRaises(ValueError):regular_bytes(p,2)
        q=self.root/"link";q.symlink_to(p)
        with self.assertRaises(ValueError):regular_bytes(q,3)
    def test_baseline_present_and_additions_absent(self):
        (self.root/"nav.js").write_bytes(b"old")
        rows=[{"path":"nav.js","operation":"replace","base_git_blob":blob(b"old")},
              {"path":"index.html","operation":"add"}]
        self.assertEqual(existing_application(self.root,rows)["counts"],{"exact":1,"expected_absent":1})
        p=self.root/"index.html";p.symlink_to(self.root/"missing")
        self.assertEqual(existing_application(self.root,rows)["mismatched_application_paths"],["index.html"])
    def test_work_metadata_without_lock(self):
        p=self.root/"lock";p.touch(mode=0o600)
        r=work_report(self.root,os.getuid())
        self.assertEqual(r["state"],"metadata_only")
        self.assertFalse(r["lock_acquired"])
        (self.root/MARKERS[0]).touch()
        self.assertEqual(work_report(self.root,os.getuid())["markers"][MARKERS[0]],"present_inhibits")
    def test_unit_fail_closed(self):
        r=unit_report("remura-private.service",{"LoadState":"loaded","ActiveState":"active"})
        self.assertFalse(r["reference_fragment_exact"])
        self.assertFalse(r["no_dropins_or_pending_reload"])
        self.assertFalse(r["expected_effective_metadata"])
