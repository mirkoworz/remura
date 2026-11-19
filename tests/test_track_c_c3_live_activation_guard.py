"""Track C3: enforce that no experimental callbacks are wired in LIVE paths.

This AST-only test never imports private_server, opens a provider or VPS.
It must become RED if anyone accidentally connects research COT witness,
research receipts, market data source replay or a Track C module to the
deployed price, retail, COT or Squalincome loops without coordinated release.
"""
from __future__ import annotations

import ast
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT/"scripts"
sys.path.insert(0,str(SCRIPTS))
import cot_monitor


class C3NoAccidentalLiveActivation(unittest.TestCase):
    def code(self, filename):
        return (SCRIPTS/filename).read_text(encoding="utf-8")

    def ast(self, filename):
        return ast.parse(self.code(filename),filename=filename)

    def test_original_cot_hooks_default_OFF(self):
        import inspect
        fn=inspect.signature(cot_monitor.collect_once)
        for key in ("research_response_observer", "research_atomic_witness"):
            self.assertIn(key,fn.parameters)
            self.assertIsNone(fn.parameters[key].default)
        self.assertEqual(tuple(cot_monitor.DATASETS),("tff","disagg"))

    def test_no_track_c_or_b_import_inside_current_live_processes(self):
        for path in ("private_server.py","signals_monitor.py","price_store.py",
                     "update_myfxbook.py"):
            with self.subTest(filename=path):
                tree=self.ast(path)
                imports=[]
                for item in ast.walk(tree):
                    if isinstance(item,ast.Import):
                        imports.extend(x.name for x in item.names)
                    elif isinstance(item,ast.ImportFrom):
                        imports.append(item.module or "")
                self.assertFalse(
                    any("track_c_" in item or "shark_retail_" in item
                        or "shark_cot_asof_witness" in item
                        for item in imports),
                    f"{path} started importing research in a LIVE path")

    def test_live_cot_loop_has_no_research_witness_argument(self):
        tree=self.ast("private_server.py")
        cot_aliases={
            alias.asname or alias.name
            for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)
            and n.module=="cot_monitor"
            for alias in n.names if alias.name=="collect_once"
        }
        self.assertEqual(cot_aliases,{"collect_official_cot"})
        loops=[n for n in tree.body
               if isinstance(n,(ast.FunctionDef,ast.AsyncFunctionDef))
               and n.name=="cot_loop"]
        self.assertEqual(len(loops),1)
        calls=[n for n in ast.walk(loops[0])
               if isinstance(n,ast.Call) and isinstance(n.func,ast.Name)
               and n.func.id=="collect_official_cot"]
        self.assertEqual(len(calls),1)
        self.assertEqual(len(calls[0].args),1)
        self.assertFalse(calls[0].keywords,
                         "core COT loop must not pass research hooks")

    def test_no_late_retroactive_research_capture_in_live_loops(self):
        for filename in ("private_server.py","signals_monitor.py"):
            tree=self.ast(filename)
            suspicious=[]
            for node in ast.walk(tree):
                if not isinstance(node,ast.Call):
                    continue
                for arg in node.keywords:
                    if arg.arg and (arg.arg.startswith("research_")
                                    or arg.arg.startswith("track_c_")):
                        suspicious.append((node.lineno,arg.arg))
            self.assertEqual(suspicious,[],
                             "research kwarg unexpectedly attached to LIVE")

    def test_cot_collector_has_no_default_research_migration(self):
        tree=self.ast("cot_monitor.py")
        for node in ast.walk(tree):
            if isinstance(node,ast.ImportFrom):
                self.assertFalse(
                    (node.module or "").startswith("scripts.shark_")
                    or (node.module or "").startswith("scripts.track_c_"))
            if isinstance(node,ast.Import):
                self.assertFalse(any(
                    (n.name.startswith("scripts.track_c_")
                     or n.name.startswith("scripts.shark_"))
                    for n in node.names))
        self.assertNotIn("track_c_cot_atomic_b_witness",
                         self.code("cot_monitor.py"))
        self.assertNotIn("shark_cot_asof_witness",
                         self.code("cot_monitor.py"))


if __name__=="__main__":
    unittest.main()
