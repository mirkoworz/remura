import tempfile
import unittest
from pathlib import Path
from owner_static_resolver import resolve_owner_shell

class Gate(unittest.TestCase):
    def test_owner_shell(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp).resolve()
            loc=root/"local"/"remura-ui"
            releases=loc/"releases"
            release=releases/("a"*40)
            release.mkdir(parents=True)
            (release/"index.html").write_text("new")
            (release/"data").mkdir()
            (release/"data"/"cot-history-public.json").write_text("{}")
            (root/"index.html").write_text("old")
            (root/"capital-cloud-config.js").write_text("runtime")
            legacy=lambda u: root/"index.html" if u=="/" else root/"capital-cloud-config.js" if u=="/capital-cloud-config.js" else None
            f=lambda u: resolve_owner_shell(root,u,legacy)
            self.assertEqual(f("/"),root/"index.html")
            (loc/"active").symlink_to(release,target_is_directory=True)
            self.assertEqual(f("/"),release/"index.html")
            self.assertEqual(f("/index.html?v=1"),release/"index.html")
            self.assertEqual(f("/data/cot-history-public.json"),release/"data"/"cot-history-public.json")
            self.assertEqual(f("/capital-cloud-config.js"),root/"capital-cloud-config.js")
            for p in ["/private/remura.env","/private-api/health","/../index.html","/%2e%2e/index.html","/data//cot-history-public.json","/nav.js","/local/remura-ui/active/index.html","/README.md"]:
                self.assertIsNone(f(p))
            (release/"nav.js").symlink_to(root/"index.html")
            self.assertIsNone(f("/nav.js"))
            (loc/"active").unlink()
            (loc/"active").symlink_to(root,target_is_directory=True)
            self.assertIsNone(f("/"))
            (loc/"active").unlink()
            (loc/"active").symlink_to(releases/("b"*40),target_is_directory=True)
            self.assertIsNone(f("/"))
            (loc/"active").unlink()
            self.assertEqual(f("/"),root/"index.html")

if __name__=="__main__":
    unittest.main()
