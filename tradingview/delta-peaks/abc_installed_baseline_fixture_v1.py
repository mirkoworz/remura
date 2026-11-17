# REMURA v0.8.140 LAB — 17/11/2026 CET
import tempfile,unittest
from pathlib import Path
from abc_installed_baseline_readonly_v1 import code_status,blob,private_metadata,STAMP,PINS
class Tests(unittest.TestCase):
    def test_code_and_stamp(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);data=b'banner '+STAMP
            h=blob(data);(p/"nav.js").write_bytes(data)
            self.assertEqual(code_status(p,"nav.js",h),"exact")
            (p/"nav.js").write_bytes(data.replace(STAMP,b"17/11/2026 17:27 (Italia)"))
            self.assertEqual(code_status(p,"nav.js",h),"stamp_only")
            (p/"nav.js").write_bytes(b"tampered")
            self.assertEqual(code_status(p,"nav.js",h),"different")
            self.assertEqual(code_status(p,"missing.js",h),"missing")
            self.assertEqual(len(PINS),107)
    def test_symlink_refused_and_no_private_content(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t);(p/"private").mkdir();(p/"private/ctrader-tokens.json").write_text("FAKE_SECRET")
            (p/"private/a.sqlite3").write_bytes(b"fake")
            (p/"nav.js").symlink_to(p/"private/ctrader-tokens.json")
            self.assertEqual(code_status(p,"nav.js",blob(b"FAKE_SECRET")),"unsafe")
            out=private_metadata(p)
            self.assertEqual(out["categories"]["credentials_or_config"]["files"],1)
            self.assertEqual(out["categories"]["sqlite"]["bytes"],4)
            self.assertNotIn("FAKE_SECRET",str(out))
            self.assertNotIn("ctrader-tokens.json",str(out))
if __name__=="__main__":unittest.main()
