# REMURA v0.8.160 LAB — 18/11/2026, sessione successiva alle 13:29 CET
"""Use the existing actual pinned CI bundle; no new build, artifact or live write."""
import hashlib,os,shutil,sys,tempfile
from pathlib import Path
from abc_v165_locked_snapshot_v1 import locked_candidate_bytes, MARKER
from abc_v165_stage_bundle_v1 import PIN
from abc_v165_locked_bundle_parser_v1 import inspect_bundle_bytes

def check(source):
    with tempfile.TemporaryDirectory(prefix="remura-boundary-lab-") as root:
        root=Path(root)
        for name in ("work","stage"):
            (root/name).mkdir(mode=0o700)
        for name in ("lock",MARKER):
            (root/"work"/name).touch(mode=0o600)
        dest=root/"stage"/"remura-v165-candidate.tar"
        shutil.copyfile(source,dest)
        dest.chmod(0o600)
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            with locked_candidate_bytes(fd,["work"],["stage"],os.getuid()) as data:
                # Remove the disposable pathname to demonstrate no reopen.
                dest.unlink()
                report,manifest,app=inspect_bundle_bytes(data)
                assert report["release_authorized"] is False and report["installable"] is False
                assert manifest["manifest_sha256"]==PIN and len(app)==155
                for bad in (data+b"x", bytes([data[0]^1])+data[1:]):
                    try:
                        inspect_bundle_bytes(bad)
                    except ValueError:
                        pass
                    else:
                        raise AssertionError("altered candidate accepted")
                assert all(hashlib.sha256(app[r["path"]]).hexdigest()==r["candidate_sha256"] for r in manifest["application"])
        finally:
            os.close(fd)
    print("LOCKED_CANDIDATE_BYTES: 155/155 verified; no pathname reopen; install authorized NO")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(2)
    check(sys.argv[1])
