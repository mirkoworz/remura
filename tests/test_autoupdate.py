import importlib.util,io,pathlib,stat,tempfile,unittest,zipfile
root=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location("autoupdater",root/"deploy/oracle/autoupdate.py")
u=importlib.util.module_from_spec(spec);spec.loader.exec_module(u)
class Tests(unittest.TestCase):
 def test_ci_requires_success_on_exact_sha(self):
  sha="a"*40
  good=lambda uri:{"workflow_runs":[{"head_sha":sha,"head_branch":"main","event":"push","status":"completed","conclusion":"success"}]}
  self.assertTrue(u.ci_passed(sha,good))
  self.assertFalse(u.ci_passed("invalid",good))
  self.assertFalse(u.ci_passed(sha,lambda uri:{"workflow_runs":[]}))
  self.assertFalse(u.ci_passed(sha,lambda uri:{"workflow_runs":[{"head_sha":"b"*40,"head_branch":"main","event":"push","status":"completed","conclusion":"success"}]}))
 def test_archive_rejects_traversal_private_and_symlinks(self):
  for name in ("repo/../../etc/passwd","repo/private/credentials.json"):
   b=io.BytesIO()
   with zipfile.ZipFile(b,"w") as z:z.writestr(name,"x")
   with tempfile.TemporaryDirectory() as d:
    with self.assertRaises(ValueError):u.safe_extract(b.getvalue(),pathlib.Path(d))
  b=io.BytesIO()
  with zipfile.ZipFile(b,"w") as z:
   item=zipfile.ZipInfo("repo/link");item.create_system=3;item.external_attr=(stat.S_IFLNK|0o777)<<16
   z.writestr(item,"/etc/passwd")
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaises(ValueError):u.safe_extract(b.getvalue(),pathlib.Path(d))
 def test_secrets_never_exposed_in_status_or_sync(self):
  for key in ("private/","local/",".venv/","data/prices/"):self.assertIn(key,u.EXCLUDES)
  with tempfile.TemporaryDirectory() as d:
   path=pathlib.Path(d)/"state.json"
   u.save_state({"enabled":True,"state":"configured","broker_password":"secret"},path)
   self.assertNotIn("secret",path.read_text())
   self.assertEqual(u.load_state(path)["state"],"configured")
