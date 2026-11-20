# REMURA v0.8.135 LAB — 17/11/2026 13:17 CET
import json,unittest
from abc_overlay_transaction_fixture_v1 import material,exact,git
from abc_integration_runner_lab_v1 import HERE,CHECKOUTS,SOURCES
from abc_dependency_inventory_lab_v1 import inspect
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _,cls.overlay=material()
        root=HERE.parents[1]/CHECKOUTS["main"]
        paths=git(root,"ls-tree","-r","--name-only",SOURCES["main"],"--","scripts").decode().splitlines()
        cls.all={p:exact(root,SOURCES["main"],p) for p in paths if p.endswith(".py") and p.count("/")==1}
        cls.all.update(cls.overlay)
    def test_actual_inventory(self):
        r=inspect(self.all,synthetic=True)
        groups=[set(r[k]) for k in ("startup_static","other_service_reachable_static","not_reached_statically")]
        self.assertEqual(set.union(*groups),set(self.all))
        self.assertEqual(sum(map(len,groups)),len(self.all))
        for p in ("scripts/collector_watchdog.py","scripts/storage_cache_v165.py","scripts/storage_inventory_v165.py"):
            self.assertIn(p,groups[0])
        self.assertIn("scripts/shark_ingest_first_seen.py",groups[1])
        self.assertIn("scripts/watchdog_release_blueprint.py",groups[2])
        for f in ("ctrader_feed","update_myfxbook","update_capital","update_ig"):
            self.assertIn("scripts/"+f+".py",groups[1])
        self.assertIn("ctrader_open_api",r["external_import_names"])
        self.assertIn("twisted",r["external_import_names"])
        for k in ("dynamic_closure_verified","live_environment_verified","safe_to_remove_unreached","release_authorized"):self.assertFalse(r[k])
        print("ABC_STATIC_DEPENDENCY_INVENTORY="+json.dumps(r,sort_keys=True))
    def test_optional_and_eager_and_unknown(self):
        f={"scripts/start.py":b"import common\ndef foo():\n    from scripts import optional\n    import external_pkg\n    __import__('another_pkg')\n",
           "scripts/common.py":b"pass","scripts/optional.py":b"pass","scripts/unused.py":b"pass"}
        r=inspect(f,roots=("start",),synthetic=True)
        self.assertEqual(r["startup_static"],["scripts/common.py","scripts/start.py"])
        self.assertEqual(r["other_service_reachable_static"],["scripts/optional.py"])
        self.assertEqual(r["not_reached_statically"],["scripts/unused.py"])
        self.assertEqual(r["external_import_names"],["another_pkg","external_pkg"])
        self.assertIn(["start","DYNAMIC___IMPORT__"],r["dynamic_review_sites"])
    def test_missing_explicit_dependency(self):
        with self.assertRaises(ValueError):inspect({"scripts/start.py":b"from scripts import absent"},roots=("start",),synthetic=True)
    def test_invalid_scope_and_source(self):
        for f in ({"scripts/start.py":b"("},{"scripts/../escape.py":b"pass"}):
            with self.assertRaises((SyntaxError,ValueError)):inspect(f,roots=("start",),synthetic=True)
        with self.assertRaises(ValueError):inspect(self.all)
    def test_import_cycle_bounded(self):
        f={"scripts/a.py":b"import b","scripts/b.py":b"import a"}
        self.assertEqual(inspect(f,roots=("a",),synthetic=True)["startup_static"],["scripts/a.py","scripts/b.py"])
if __name__=="__main__":unittest.main()
