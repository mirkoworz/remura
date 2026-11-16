# REMURA v0.8.93 LAB — 16/11/2026 13:17 CET
"""Fixed finite synthetic resource profile for CI Linux, not Oracle capacity proof."""
import json,os,resource,sys,tempfile,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
from test_shark_observation_bundle import create
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_incremental_persistence_v1 import NAME,FILE_BYTES,open_store
from cvd_incremental_preview_v1 import repage,RollingPreview,PERIOD,M5
from cvd_private_runtime_preview_v1 import plan,preview
from cvd_runtime_private_state_v1 import bucket

def main():
    assert sys.platform=="linux"
    baseline=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024
    db,_=create()
    db.execute("PRAGMA query_only=ON")
    before=db.total_changes
    rows=[r for r,_,_ in triples(340,events=(0,14,290),missing=())]
    cycles=12
    now=bucket(T0+287*M5+300000)
    max_file=0; max_dir=0; peak_allocated=0
    wall=[];cpu=[];reference_wall=[];incremental_slots=0;full_slots=0
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/LOCK).touch(mode=0o600)
            for i in range(cycles):
                cutoff=now+i*PERIOD
                full=repage(plan(cutoff),rows)
                full_slots+=sum((w["end_ms"]-w["start_ms"])//M5+1 for w in full)
                if i:
                    prev=RollingPreview(now=cutoff-PERIOD,windows=repage(plan(cutoff-PERIOD),rows),synthetic=True)
                    incoming=repage(prev.next_ranges(cutoff),rows)
                else:incoming=full
                incremental_slots+=sum((w["end_ms"]-w["start_ms"])//M5+1 for w in incoming)
                start=time.perf_counter_ns();cstart=time.process_time_ns()
                with open_store(root,synthetic=True) as s:
                    if i:assert s.claim(cutoff)
                    else:s.initialize(cutoff)
                    result=s.complete(db,cutoff=cutoff,windows=incoming)
                wall.append(time.perf_counter_ns()-start);cpu.append(time.process_time_ns()-cstart)
                start=time.perf_counter_ns()
                reference=preview(db,full,now=cutoff,origin="SYNTHETIC")
                reference_wall.append(time.perf_counter_ns()-start)
                assert result["preview"]==reference
                assert reference["coverage"]["valid_unique_bars"]==289
                assert not result["scientific_admission"]
                st=(root/NAME).stat()
                max_file=max(max_file,st.st_size)
                assert st.st_size<=FILE_BYTES and set(p.name for p in root.iterdir())=={NAME,LOCK}
                max_dir=max(max_dir,sum(p.stat().st_size for p in root.iterdir()))
                peak_allocated=max(peak_allocated,sum(p.stat().st_blocks*512 for p in root.iterdir()))
            assert db.total_changes==before
        assert incremental_slots==289+3*(cycles-1) and full_slots==289*cycles
        result={"schema":"remura.tv.incremental.synthetic.resource.v1",
                "cycles":cycles,"dense_slots":289,"incremental_requested_slots":incremental_slots,
                "full_requested_slots":full_slots,"max_committed_file_bytes":max_file,
                "max_steady_directory_logical_bytes":max_dir,"max_steady_directory_allocated_bytes":peak_allocated,
                "conservative_two_file_logical_bound_bytes":2*FILE_BYTES,
                "process_initial_highwater_rss_bytes":baseline,
                "process_final_highwater_rss_bytes":resource.getrusage(resource.RUSAGE_SELF).ru_maxrss*1024,
                "max_store_wall_ms":round(max(wall)/1e6,3),
                "total_store_wall_ms":round(sum(wall)/1e6,3),
                "total_store_cpu_ms":round(sum(cpu)/1e6,3),
                "total_reference_preview_wall_ms":round(sum(reference_wall)/1e6,3),
                "platform":"LINUX_CI_SYNTHETIC","host_capacity_attested":False,
                "temporary_peak_measured":False,"no_network_calls":True,
                "billed_rows_known":False,"scientific_admission":False}
        print("REMURA_D_INCREMENTAL_RESOURCE="+json.dumps(result,sort_keys=True))
    finally:db.close()
if __name__=="__main__":main()
