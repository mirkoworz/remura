# REMURA v0.8.134 LAB — 17/11/2026 CET
import importlib.util,unittest
from abc_overlay_transaction_fixture_v1 import material,exact
from abc_integration_runner_lab_v1 import HERE,CHECKOUTS,SOURCES
from abc_v165_overlay_manifest_lab_v1 import combined_manifest,UI
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.before,cls.after=material()
        roots={k:HERE.parents[1]/p for k,p in CHECKOUTS.items()}
        path="deploy/oracle/v165_release_offline_preview.py"
        exact(roots["C"],SOURCES["C"],path)
        spec=importlib.util.spec_from_file_location("c_preview_fixture",roots["C"]/path)
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
        source={p:exact(roots["C"],SOURCES["C"],p) for p in mod.SOURCE_BLOBS}
        out=mod.preview(source)
        cls.ui_before={p:exact(roots["main"],SOURCES["main"],p) for p in UI}
        cls.ui_after={p:out[p] for p in UI}
        for p in UI:assert cls.ui_before[p]==source[p]
        for p in ("scripts/storage_cache_v165.py","scripts/storage_inventory_v165.py"):
            assert cls.after[p]==source[p]
    def build(self,**kw):
        args=dict(before=self.before,after=self.after,ui_before=self.ui_before,ui_after=self.ui_after,synthetic=True)
        return combined_manifest(**dict(args,**kw))
    def test_exact_combined_preview(self):
        rows,r=self.build()
        self.assertEqual((len(rows),r["existing_paths"],r["new_paths"],r["versioned_pages"]),(90,14,76,9))
        for k in ("real_install_stamp_verified","full_distribution_manifest_verified","live_baseline_verified","installer_available","restore_verified","autoupdater_reconciled","release_authorized"):self.assertFalse(r[k])
        self.assertEqual(self.build(),(rows,r))
    def test_wrong_server_pin(self):
        with self.assertRaises(ValueError):self.build(after={**self.after,"scripts/private_server.py":b"wrong"})
    def test_cache_tag_or_banner_missing(self):
        for p in ("index.html","nav.js","sw.js"):
            with self.assertRaises(ValueError):self.build(ui_after={**self.ui_after,p:b"bad"})
    def test_extra_missing_or_scope(self):
        bad=dict(self.ui_after);bad.pop("index.html")
        with self.assertRaises(ValueError):self.build(ui_after=bad)
        with self.assertRaises(ValueError):self.build(ui_after={**self.ui_after,"extra.html":b"x"})
        with self.assertRaises(ValueError):self.build(synthetic=False)
if __name__=="__main__":unittest.main()
