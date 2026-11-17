# REMURA v0.8.137 LAB — 17/11/2026, sessione successiva alle 14:22 CET
import json,unittest,re
from abc_overlay_transaction_fixture_v1 import exact,git
from abc_integration_runner_lab_v1 import HERE,CHECKOUTS,SOURCES
import abc_v165_overlay_manifest_fixture_v1 as overlay_fixture
from abc_v165_repository_manifest_lab_v1 import build,ASSET,DEPLOY
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        overlay_fixture.Tests.setUpClass()
        cls.overlay={**overlay_fixture.Tests.after,**overlay_fixture.Tests.ui_after}
        root=HERE.parents[1]/CHECKOUTS["main"]
        paths=git(root,"ls-tree","-r","--name-only",SOURCES["main"]).decode().splitlines()
        cls.base={p:exact(root,SOURCES["main"],p) for p in paths if ASSET.fullmatch(p) or re.fullmatch(r"scripts/[A-Za-z_][A-Za-z_0-9]*[.]py",p)}
        cls.deploy={p:exact(root,SOURCES["main"],p) for p in paths if DEPLOY.fullmatch(p)}
    def test_actual_manifest(self):
        result=build(self.base,self.overlay,self.deploy,synthetic=True)
        rows=result["application"]
        self.assertEqual(len(rows),155)
        self.assertEqual(sum(r["operation"]=="retain" for r in rows),65)
        self.assertEqual(sum(r["operation"]=="replace" for r in rows),14)
        self.assertEqual(sum(r["operation"]=="add" for r in rows),76)
        self.assertEqual(sum(r["category"]=="unclassified_retained" for r in rows),52)
        self.assertEqual(len(result["deployment_reference"]),28)
        self.assertFalse(result["release_authorized"])
        print("ABC_V165_REPOSITORY_MANIFEST="+json.dumps(result,sort_keys=True))
    def test_missing_base_or_overlay(self):
        for target in ("base","overlay","deploy"):
            args=[dict(self.base),dict(self.overlay),dict(self.deploy)]
            d=args[("base","overlay","deploy").index(target)];d.pop(next(iter(d)))
            with self.assertRaises(ValueError):build(*args,synthetic=True)
    def test_unexpected_asset_and_cache(self):
        b=dict(self.base);b["evil.js"]=b.pop("price.js")
        with self.assertRaises(ValueError):build(b,self.overlay,self.deploy,synthetic=True)
        o=dict(self.overlay);o["sw.js"]=o["sw.js"].replace(b'"./price.js",',b'')
        with self.assertRaises(ValueError):build(self.base,o,self.deploy,synthetic=True)
    def test_scope_and_determinism(self):
        a=build(self.base,self.overlay,self.deploy,synthetic=True)
        b=build(dict(reversed(list(self.base.items()))),dict(reversed(list(self.overlay.items()))),self.deploy,synthetic=True)
        self.assertEqual(a,b)
        self.assertFalse(a["full_distribution_manifest_verified"])
        with self.assertRaises(ValueError):build(self.base,self.overlay,self.deploy)
if __name__=="__main__":unittest.main()
