# REMURA v0.8.132 LAB — 17/11/2026 CET
"""Resolve exact checked-out Git objects, verify candidate pin, exercise all rollback boundaries."""
import hashlib,json,subprocess,unittest
from pathlib import Path
from abc_integration_runner_lab_v1 import SOURCES,CHECKOUTS,OVERLAYS,BASE,HERE
from abc_overlay_transaction_lab_v1 import manifest,rehearse,need,sha
PIN="b70b82f6b2752536b5bbe8c6493072c4b5cff982da0f35124beb60779b92d4ab"
def git(root,*args):return subprocess.check_output(["git","-C",str(root),*args])
def exact(root,ref,path):
    expected=git(root,"show",ref+":"+path)
    need((root/path).read_bytes()==expected)
    return expected
def material():
    roots={k:HERE.parents[1]/v for k,v in CHECKOUTS.items()}
    for k,r in roots.items():need(git(r,"rev-parse","HEAD").decode().strip()==SOURCES[k])
    original={}
    for p,h in BASE.items():
        b=exact(roots["main"],SOURCES["main"],p)
        need(hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()==h)
        original[p]=b
    candidate={"scripts/private_server.py":(HERE/"abc_private_server_candidate_v1.txt").read_bytes()}
    need(sha(candidate["scripts/private_server.py"])==PIN)
    for k in ("A","B","C"):
        for item in OVERLAYS[k]:
            p=item["path"];need(p not in candidate)
            if item["status"]=="added":
                need(p not in original and not (roots["main"]/p).exists())
                # Prove absence in the pinned Git tree, not just worktree.
                need(not git(roots["main"],"ls-tree",SOURCES["main"],"--",p))
            else:need(item["status"]=="modified" and p in original)
            candidate[p]=exact(roots[k],SOURCES[k],p)
    need(len(candidate)==79 and len(original)==3)
    return original,candidate
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original,cls.candidate=material()
        cls.pin=manifest(cls.original,cls.candidate)
    def test_all_rollback_boundaries(self):
        for i in range(len(self.pin)+1):
            with self.subTest(i=i):
                r=rehearse(self.original,self.candidate,self.pin,fail_after=i,synthetic=True)
                self.assertEqual(r,{"status":"SYNTHETIC_ROLLBACK_VERIFIED","restored":3,"added_removed":76,"release_authorized":False})
    def test_success_exact_overlay(self):
        out=rehearse(self.original,self.candidate,self.pin,synthetic=True)
        self.assertEqual(out,{"status":"SYNTHETIC_OVERLAY_VERIFIED","files":79,"release_authorized":False})
    def test_tampered_content_missing_and_extra(self):
        for changes in ("tamper","missing","extra"):
            c=dict(self.candidate)
            if changes=="tamper":c["scripts/private_server.py"]+=b"\n"
            elif changes=="missing":c.pop("scripts/collector_watchdog.py")
            else:c["scripts/unexpected.py"]=b"x"
            with self.assertRaises(ValueError):rehearse(self.original,c,self.pin,synthetic=True)
    def test_wrong_predecessor_and_scope(self):
        with self.assertRaises(ValueError):rehearse(self.original,self.candidate,self.pin)
        with self.assertRaises(ValueError):rehearse({**self.original,"scripts/private_server.py":b"wrong"},self.candidate,self.pin,synthetic=True)
    def test_unsafe_path_and_invalid_failure(self):
        with self.assertRaises(ValueError):manifest(self.original,{**self.candidate,"scripts/../escape.py":b"x"})
        for i in (-1,80,True):
            with self.assertRaises(ValueError):rehearse(self.original,self.candidate,self.pin,fail_after=i,synthetic=True)
if __name__=="__main__":
    unittest.main()
