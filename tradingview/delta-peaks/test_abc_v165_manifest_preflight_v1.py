# REMURA v0.8.148 LAB — 18/11/2026
import json,tempfile,unittest
from pathlib import Path
from abc_v165_install_preflight_readonly_v1 import load_public_manifest
class Tests(unittest.TestCase):
    def test_actual_public_manifest(self):
        p=Path(__file__).resolve().parent/"abc-v165-pinned-application-manifest.json"
        r=load_public_manifest(p)
        self.assertEqual(len(r),155)
        self.assertEqual(sum(x["operation"]=="add" for x in r),76)
        self.assertEqual(sum(x["operation"]=="replace" for x in r),14)
    def test_modified_manifest_denied(self):
        p=Path(__file__).resolve().parent/"abc-v165-pinned-application-manifest.json"
        doc=json.loads(p.read_bytes())
        with tempfile.TemporaryDirectory() as t:
            q=Path(t).resolve()/"manifest.json"
            doc["application"][0]["bytes"]+=1
            q.write_text(json.dumps(doc))
            with self.assertRaises(ValueError):load_public_manifest(q)
