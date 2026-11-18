# REMURA v0.8.173 LAB — 18/11/2026, sessione successiva alle 17:48 CET
"""Existing actual pinned CI bundle, one outer maintenance lock, disposable disk only.
No new bundle build, artifact, live data, root execution or service commands.
"""
import fcntl,hashlib,io,os,sys,tempfile,zipfile
from abc_v165_candidate_zip_gate_v1 import _decode,verified_tar
from pathlib import Path
from abc_v165_locked_snapshot_v1 import MARKER
from abc_v165_dual_inhibit_boundary_v1 import locked_dual_inhibit_bytes, MARKERS
from abc_v165_bootstrap_source_gate_v1 import PINS
from abc_v165_verified_parser_lab_v1 import verified_parser
from abc_v165_stage_bundle_v1 import PIN
from abc_v165_transaction_plan_v1 import prepare_plan
from abc_v165_baseline_fd_lab_v1 import read_baseline
from abc_rollback_disk_lab_v1 import Journal
from abc_v165_repository_manifest_fixture_v1 import Tests as Repository

def must_be_locked(path):
    with path.open("rb") as contender:
        try:
            fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
        except BlockingIOError:
            return
        raise AssertionError("maintenance lock not held")

def observed(journal,manifest):
    # Disposable, quiescent fixture: read actual scoped file bytes and absences.
    # Journal.current is LAB-only and NOT a safe live path traversal.
    from abc_rollback_disk_lab_v1 import unpack
    base={}
    for row in manifest["application"]:
        p=row["path"]
        value=journal.current(p)
        if value is not None:base[p]=unpack(value)[0]
    return base

def check(source):
    Repository.setUpClass()
    with tempfile.TemporaryDirectory(prefix="remura-boundary-lab-") as root, \
         tempfile.TemporaryDirectory(prefix="remura-journal-lab-") as journal_dir, \
         tempfile.TemporaryDirectory(prefix="remura-witness-lab-") as witness_dir:
        root=Path(root)
        jr=Path(journal_dir).resolve()
        (jr/"app"/"scripts").mkdir(parents=True)
        for name,data in Repository.base.items():
            target=jr/"app"/name
            target.write_bytes(data)
            target.chmod(0o640)
        journal=Journal(jr,synthetic=True,auth_key=os.urandom(32),
                        transaction_id=os.urandom(32).hex(),
                        witness_root=Path(witness_dir).resolve())
        for name in ("work","stage","sources"):
            (root/name).mkdir(mode=0o700)
        for name in ("lock",*MARKERS):
            (root/"work"/name).touch(mode=0o600)
        for name in PINS:
            target=root/"sources"/name
            target.write_bytes(Path(__file__).with_name(name).read_bytes())
            target.chmod(0o400)
        lock=root/"work"/"lock"
        dest=root/"stage"/"remura-v165-candidate.tar"
        # Reuse actual deterministic TAR; fixture ZIP is not the historical delivery.
        tar=Path(source).read_bytes()
        wrapped=io.BytesIO()
        with zipfile.ZipFile(wrapped,"w",compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("remura-v165-candidate.tar",tar)
            z.writestr("candidate-attestation.json","fixture only")
            z.writestr("READ-ME.txt","not authorized")
        data=wrapped.getvalue()
        assert _decode(data)==tar
        try:verified_tar(data)
        except ValueError:pass
        else:raise AssertionError("fixture accepted as historical delivery")
        dest.write_bytes(_decode(data))
        dest.chmod(0o600)
        fd=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            with locked_dual_inhibit_bytes(fd,["work"],["stage"],os.getuid()) as data:
                inspect_bundle_bytes=verified_parser(fd,("sources",),os.getuid(),synthetic=True)
                must_be_locked(lock)
                dest.unlink()
                report,manifest,app=inspect_bundle_bytes(data)
                assert report["release_authorized"] is False and report["installable"] is False
                assert manifest["manifest_sha256"]==PIN and len(app)==155
                for bad in (data+b"x", bytes([data[0]^1])+data[1:]):
                    try:inspect_bundle_bytes(bad)
                    except ValueError:pass
                    else:raise AssertionError("altered candidate accepted")
                assert all(hashlib.sha256(app[r["path"]]).hexdigest()==r["candidate_sha256"] for r in manifest["application"])
                appfd=os.open(jr/"app",os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
                try:
                    baseline=read_baseline(appfd,manifest,os.getuid(),synthetic=True)
                    # Attack cases on actual pinned candidate paths, LAB only.
                    added=next(row["path"] for row in manifest["application"] if row["operation"]=="add")
                    target=jr/"app"/added
                    target.write_bytes(b"unexpected predecessor")
                    try:
                        try:read_baseline(appfd,manifest,os.getuid(),synthetic=True)
                        except ValueError:pass
                        else:raise AssertionError("unexpected predecessor accepted")
                    finally:target.unlink()
                    existing=next(iter(baseline))
                    target=jr/"app"/existing
                    target.chmod(0o666)
                    try:
                        try:read_baseline(appfd,manifest,os.getuid(),synthetic=True)
                        except ValueError:pass
                        else:raise AssertionError("writable predecessor accepted")
                    finally:target.chmod(0o640)
                    target.unlink()
                    target.symlink_to(jr/"app"/next(p for p in baseline if p!=existing))
                    try:
                        try:read_baseline(appfd,manifest,os.getuid(),synthetic=True)
                        except (ValueError,OSError):pass
                        else:raise AssertionError("symlink predecessor accepted")
                    finally:
                        target.unlink();target.write_bytes(baseline[existing]);target.chmod(0o640)
                    assert read_baseline(appfd,manifest,os.getuid(),synthetic=True)==baseline
                finally:os.close(appfd)
                assert baseline==Repository.base
                original,new=prepare_plan(manifest,app,baseline)
                must_be_locked(lock)
                journal.prepare(original,new)
                must_be_locked(lock)
                journal.apply()
                must_be_locked(lock)
                assert observed(journal,manifest)==app
                assert journal.rollback()=="rolled_back"
                must_be_locked(lock)
                assert observed(journal,manifest)==baseline
                for name in baseline:
                    assert (jr/"app"/name).stat().st_mode&0o777==0o640
                assert all(not (jr/"app"/name).exists() for name in set(app)-set(baseline))
                assert all((root/"work"/name).is_file() for name in MARKERS)
            with lock.open("rb") as contender:
                fcntl.flock(contender,fcntl.LOCK_EX|fcntl.LOCK_NB)
        finally:
            os.close(fd)
    print("LOCKED_CANDIDATE_BYTES: 155/155 verified; 90 changes applied and rolled back under outer LAB lock; install authorized NO")

if __name__=="__main__":
    if len(sys.argv)!=2:raise SystemExit(2)
    check(sys.argv[1])
