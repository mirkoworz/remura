# REMURA v0.8.99 LAB — 16/11/2026 14:49 CET
"""Comparative finite Linux CI resource profile; no Oracle or provider access."""
import json,resource,subprocess,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from test_shark_observation_bundle import create
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_incremental_preview_v1 import repage,RollingPreview,PERIOD,M5
from cvd_private_runtime_preview_v1 import plan,preview
from cvd_runtime_private_state_v1 import bucket,digest
import cvd_joint_publication_v1 as plain
import cvd_joint_encrypted_v1 as enc
CYCLES=12
G="c"*32
def cpu_children():
    r=resource.getrusage(resource.RUSAGE_CHILDREN)
    return r.ru_utime+r.ru_stime
def profile(mode):
    assert sys.platform=="linux" and mode in ("plain","encrypted")
    baseline=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    db,_=create();db.execute("PRAGMA query_only=ON")
    before=db.total_changes
    rows=[r for r,_,_ in triples(340,events=(0,14,290),missing=())]
    now=bucket(T0+289*M5)
    assert plan(now)[0][0]==T0 and plan(now)[-1][1]==T0+288*M5
    if mode=="plain":
        custody=plain.JointCustody(G,synthetic=True);name=plain.NAME;cap=plain.MAX_FILE
        def store(root):return plain.open_joint(root,custody,generation=G,synthetic=True)
    else:
        custody=enc.EncryptedCustody(G,synthetic=True);name=enc.NAME;cap=enc.MAX_CIPHER
        def store(root):return enc.open_encrypted_joint(root,custody,generation=G,key=b"\x75"*32,synthetic=True)
    p=custody.latest()
    wall=[];parent_cpu=child_cpu=0;max_file=max_allocated=0
    commitments=[];slots=0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/LOCK).touch(mode=0o600)
            for i in range(CYCLES):
                at=now+i*PERIOD;full=repage(plan(at),rows)
                if i:
                    old=RollingPreview(now=at-PERIOD,windows=repage(plan(at-PERIOD),rows),synthetic=True)
                    incoming=repage(old.next_ranges(at),rows)
                else:incoming=full
                slots+=sum((w["end_ms"]-w["start_ms"])//M5+1 for w in incoming)
                start=time.perf_counter_ns();cpu=time.process_time_ns();child=cpu_children()
                with store(root) as s:
                    if i:p,out=s.cycle(db,expected=p,cutoff=at,windows=incoming)
                    else:p,out=s.bootstrap(db,expected=p,cutoff=at,windows=incoming,cycles=CYCLES)
                wall.append(time.perf_counter_ns()-start)
                parent_cpu+=time.process_time_ns()-cpu
                child_cpu+=cpu_children()-child
                # Outside timed work; equality to the full independent preview.
                assert out["preview"]==preview(db,full,now=at,origin="SYNTHETIC")
                assert out["preview"]["coverage"]["valid_unique_bars"]==289
                assert out["archive"]["cycles_recorded"]==i+1
                assert out["archive"]["slots_observed"]==3*(i+1)
                assert not out["scientific_admission"]
                commitments.append(out["state_digest"])
                st=(root/name).stat()
                max_file=max(max_file,st.st_size)
                max_allocated=max(max_allocated,st.st_blocks*512)
                assert st.st_size<=cap and {n.name for n in root.iterdir()}=={name,LOCK}
                if mode=="encrypted":
                    assert set(json.loads((root/name).read_bytes()))=={"v","nonce","ct","tag"}
            assert db.total_changes==before and slots==322
            assert out["archive"]["complete_schedule_recorded"]
        return {"mode":mode,"cycles":CYCLES,"dense_slots":289,
            "archived_slots":out["archive"]["slots_observed"],"incremental_requested_slots":slots,
            "max_committed_file_bytes":max_file,"max_steady_file_allocated_bytes":max_allocated,
            "conservative_two_file_logical_bound_bytes":2*cap,
            "max_cycle_wall_ms":round(max(wall)/1e6,3),"total_cycle_wall_ms":round(sum(wall)/1e6,3),
            "parent_cycle_cpu_ms":round(parent_cpu/1e6,3),"child_cycle_cpu_ms":round(child_cpu*1000,3),
            "parent_initial_highwater_rss_bytes":baseline,
            "parent_final_highwater_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
            "largest_child_highwater_rss_bytes":resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss*1024,
            "commitment_digest":digest(commitments)}
    finally:db.close()

def main():
    if len(sys.argv)==2:
        print(json.dumps(profile(sys.argv[1]),sort_keys=True));return
    assert len(sys.argv)==1
    results=[]
    for mode in ("plain","encrypted"):
        # Separate process prevents one mode inheriting the other's high-water.
        run=subprocess.run([sys.executable,__file__,mode],stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE,check=True,timeout=100)
        assert 0<len(run.stdout)<=8192
        results.append(json.loads(run.stdout))
    a,b=results
    assert a["commitment_digest"]==b["commitment_digest"]
    # Report no raw row/archive/decision material, even synthetic.
    for x in results:x.pop("commitment_digest")
    print("REMURA_D_JOINT_RESOURCE="+json.dumps({"schema":"remura.tv.joint.synthetic.resource.v1",
        "profiles":results,"all_24_cycles_exact_preview_match":True,"identical_commitments":True,
        "platform":"LINUX_CI_SYNTHETIC","host_capacity_attested":False,
        "simultaneous_parent_child_rss_measured":False,"temporary_peak_measured":False,
        "provider_calls":0,"billed_rows_known":False,"scientific_admission":False},sort_keys=True))
if __name__=="__main__":main()
