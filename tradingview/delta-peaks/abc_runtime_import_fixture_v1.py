# REMURA v0.8.136 LAB — 17/11/2026, sessione 14:22 CET
import json,unittest
from abc_overlay_transaction_fixture_v1 import material,exact,git
from abc_integration_runner_lab_v1 import HERE,CHECKOUTS,SOURCES
from abc_runtime_import_lab_v1 import observe,ROOTS
class Tests(unittest.TestCase):
    def test_pinned_actual_imports(self):
        _,overlay=material()
        root=HERE.parents[1]/CHECKOUTS["main"]
        paths=git(root,"ls-tree","-r","--name-only",SOURCES["main"],"--","scripts").decode().splitlines()
        files={p:exact(root,SOURCES["main"],p) for p in paths if p.endswith(".py") and p.count("/")==1}
        files.update(overlay)
        r=observe(files,synthetic=True)
        self.assertEqual([x["root"] for x in r["entrypoints"]],list(ROOTS))
        self.assertIn("scripts/collector_watchdog.py",r["observed_import_paths"])
        self.assertIn("scripts/storage_cache_v165.py",r["observed_import_paths"])
        self.assertFalse(r["release_authorized"])
        self.assertFalse(r["safe_to_remove_unobserved"])
        print("ABC_RUNTIME_IMPORT_OBSERVATION="+json.dumps(r,sort_keys=True))
    def test_dynamic_import_observed(self):
        files={"scripts/start.py":b"import importlib\nname='leaf'\nimportlib.import_module(name)\n","scripts/leaf.py":b"pass","scripts/unused.py":b"pass"}
        r=observe(files,synthetic=True,roots=("start",))
        self.assertEqual(r["observed_outside_static"],["scripts/leaf.py"])
        self.assertEqual(r["unclassified_retained"],["scripts/unused.py"])
    def test_block_network_database_and_write(self):
        for body in (b"import socket\nsocket.socket()",
                     b"import sqlite3\nsqlite3.connect(':memory:')",
                     b"open('forbidden','w')",
                     b"import subprocess\nsubprocess.run(['true'])"):
            with self.subTest(body=body):
                with self.assertRaises(ValueError):
                    observe({"scripts/start.py":body},synthetic=True,roots=("start",))
    def test_main_not_executed(self):
        r=observe({"scripts/start.py":b"if __name__=='__main__':\n    raise RuntimeError()"},
                  synthetic=True,roots=("start",))
        self.assertFalse(r["service_functions_executed"])
if __name__=="__main__":unittest.main()
