# REMURA v0.8.131 LAB — 17/11/2026 12:05 CET
"""Isolated actual A/B/C candidate compile, structural checks and offline regressions.
Never run private_server.main, installer, collector, real credentials or remote services.
"""
import hashlib,json,os,shutil,subprocess,sys,tempfile
from pathlib import Path
HERE=Path(__file__).resolve().parent
SOURCES={"main":"30de2987fe28ee73044448817e66ac60391e3357","A":"2288bcc12e8548ec52b437ff4a14c621be307fd5","B":"8dc51e8a199dc1cfd45e4cd2e7b339510af2eb2b","C":"69886bc1d1db0ad0bd74918e5146f79b223f4fe4"}
CHECKOUTS={"main":"_remura_abc_main","A":"_remura_abc_a","B":"_remura_b_reference","C":"_remura_abc_c"}
OVERLAYS={"A":[{"path":"scripts/collector_watchdog.py","status":"added"},{"path":"scripts/watchdog_cadence_guard.py","status":"added"},{"path":"scripts/watchdog_crosspr_contract.py","status":"added"},{"path":"scripts/watchdog_release_blueprint.py","status":"added"},{"path":"scripts/watchdog_release_gate.py","status":"added"},{"path":"scripts/watchdog_staging_rehearsal.py","status":"added"}],"B":[{"path":"scripts/cvd_benchmark.py","status":"added"},{"path":"scripts/cvd_divergence.py","status":"added"},{"path":"scripts/cvd_session_replay.py","status":"added"},{"path":"scripts/price_store.py","status":"modified"},{"path":"scripts/shark_causal_pair_audit.py","status":"added"},{"path":"scripts/shark_cot_asof_witness.py","status":"added"},{"path":"scripts/shark_cot_cvd_scan_reconciliation.py","status":"added"},{"path":"scripts/shark_cot_paired_baseline.py","status":"added"},{"path":"scripts/shark_cot_robustness.py","status":"added"},{"path":"scripts/shark_ctrader_ingest_handoff.py","status":"added"},{"path":"scripts/shark_cvd_cot_price_triage.py","status":"added"},{"path":"scripts/shark_cvd_full_denominator_audit.py","status":"added"},{"path":"scripts/shark_cvd_incremental_protocol.py","status":"added"},{"path":"scripts/shark_cvd_ledger.py","status":"added"},{"path":"scripts/shark_cvd_missingness_bounds.py","status":"added"},{"path":"scripts/shark_cvd_prefix_lineage.py","status":"added"},{"path":"scripts/shark_cvd_same_source_adapter.py","status":"added"},{"path":"scripts/shark_cvd_same_source_preflight.py","status":"added"},{"path":"scripts/shark_cvd_scan_coverage.py","status":"added"},{"path":"scripts/shark_cvd_shard_backup.py","status":"added"},{"path":"scripts/shark_cvd_shard_resource_probe.py","status":"added"},{"path":"scripts/shark_cvd_sharded_ledger.py","status":"added"},{"path":"scripts/shark_cvd_source_lineage.py","status":"added"},{"path":"scripts/shark_cvd_storage_gate.py","status":"added"},{"path":"scripts/shark_data_readiness.py","status":"added"},{"path":"scripts/shark_digest_ab_benchmark.py","status":"added"},{"path":"scripts/shark_first_invocation.py","status":"added"},{"path":"scripts/shark_ingest_first_seen.py","status":"added"},{"path":"scripts/shark_market_regime_context.py","status":"added"},{"path":"scripts/shark_observation_bundle.py","status":"added"},{"path":"scripts/shark_oracle_capacity_readonly.py","status":"added"},{"path":"scripts/shark_oracle_cvd_coload_gate.py","status":"added"},{"path":"scripts/shark_oracle_staging_gate.py","status":"added"},{"path":"scripts/shark_original_decision_atomic_gate.py","status":"added"},{"path":"scripts/shark_p0_go_no_go.py","status":"added"},{"path":"scripts/shark_p0b_passive_observer.py","status":"added"},{"path":"scripts/shark_p0b_window_census.py","status":"added"},{"path":"scripts/shark_prefix_cost_probe.py","status":"added"},{"path":"scripts/shark_price_asof_evidence.py","status":"added"},{"path":"scripts/shark_price_only_compact.py","status":"added"},{"path":"scripts/shark_price_only_universe.py","status":"added"},{"path":"scripts/shark_price_regime_atomic_gate.py","status":"added"},{"path":"scripts/shark_prospective_coverage.py","status":"added"},{"path":"scripts/shark_regime_cvd_cohort_audit.py","status":"added"},{"path":"scripts/shark_regime_first_seen.py","status":"added"},{"path":"scripts/shark_research_census.py","status":"added"},{"path":"scripts/shark_research_local_archive.py","status":"added"},{"path":"scripts/shark_research_probe.py","status":"added"},{"path":"scripts/shark_resource_probe.py","status":"added"},{"path":"scripts/shark_retail_actual_scan_handoff.py","status":"added"},{"path":"scripts/shark_retail_capsule_index.py","status":"added"},{"path":"scripts/shark_retail_crossdb_predecision.py","status":"added"},{"path":"scripts/shark_retail_evidence_capsule.py","status":"added"},{"path":"scripts/shark_retail_first_seen.py","status":"added"},{"path":"scripts/shark_retail_numeric_features.py","status":"added"},{"path":"scripts/shark_retail_preregistered_protocol.py","status":"added"},{"path":"scripts/shark_retail_prospective_validation.py","status":"added"},{"path":"scripts/shark_retail_retention_readiness.py","status":"added"},{"path":"scripts/shark_retail_scan_inbox.py","status":"added"},{"path":"scripts/shark_retail_segment_readiness.py","status":"added"},{"path":"scripts/shark_retail_segment_writer.py","status":"added"},{"path":"scripts/shark_sample_admission.py","status":"added"},{"path":"scripts/shark_scan_failures.py","status":"added"},{"path":"scripts/shark_science_gate.py","status":"added"},{"path":"scripts/shark_signal_evidence.py","status":"added"},{"path":"scripts/shark_signal_ingest_decision_link.py","status":"added"},{"path":"scripts/shark_universe_lineage.py","status":"added"},{"path":"scripts/shark_universe_probe.py","status":"added"},{"path":"scripts/shark_walkforward.py","status":"added"},{"path":"scripts/signals_monitor.py","status":"modified"}],"C":[{"path":"scripts/storage_cache_v165.py","status":"added"},{"path":"scripts/storage_inventory_v165.py","status":"added"}]}
BASE={"scripts/private_server.py":"0853194762f3f0340451a69c9ed8b4e0261db42d","scripts/price_store.py":"96375ed6319fc917a8bfd76cdc538fa1d911d23a","scripts/signals_monitor.py":"0c4769e81ff2d1e0c9065dccc2bb9bd67e322ddd"}
def blob(path):
    b=path.read_bytes();return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()
def need(x):
    if not x:raise RuntimeError("ABC_OFFLINE_GATE_FAILED")
def run():
    workspace=HERE.parents[1]
    roots={k:workspace/v for k,v in CHECKOUTS.items()}
    for k,p in roots.items():
        need(subprocess.check_output(["git","-C",str(p),"rev-parse","HEAD"],text=True).strip()==SOURCES[k])
    for p,h in BASE.items():need(blob(roots["main"]/p)==h)
    with tempfile.TemporaryDirectory(prefix="remura-abc-lab-") as tmp:
        dest=Path(tmp);shutil.copytree(roots["main"]/"scripts",dest/"scripts")
        (dest/"tests").mkdir();(dest/"home").mkdir()
        for k in ("B","A","C"):
            for item in OVERLAYS[k]:
                path=item["path"];target=dest/path
                need(path.startswith("scripts/") and path.endswith(".py") and "/" not in path[len("scripts/"):])
                if item["status"]=="added":need(not target.exists())
                else:need(item["status"]=="modified" and path in BASE and blob(target)==BASE[path])
                shutil.copyfile(roots[k]/path,target)
        candidate=(HERE/"abc_private_server_candidate_v1.txt").read_text()
        (dest/"scripts/private_server.py").write_text(candidate)
        sys.path.insert(0,str(dest/"scripts"))
        from watchdog_crosspr_contract import inspect_candidate
        from watchdog_cadence_guard import inspect_cadence
        sha=hashlib.sha256(candidate.encode()).hexdigest()
        x=inspect_candidate(candidate,sha);y=inspect_cadence(candidate)
        need(x["state"]=="STRUCTURAL_REVIEW_REQUIRED" and not x["missing"] and x["release_authorized"] is False)
        need(y["state"]=="STATIC_REVIEW_REQUIRED" and not y["violations"] and y["release_authorized"] is False)
        compile(candidate,"isolated_private_server.py","exec")
        for name in ("test_collector_watchdog.py","test_collector_watchdog_http.py"):
            shutil.copyfile(roots["A"]/"tests"/name,dest/"tests"/name)
        shutil.copyfile(HERE/"abc_runtime_regression_fixture_v1.py",dest/"tests"/"test_abc_runtime_fixture.py")
        env={"PATH":os.environ["PATH"],"HOME":str(dest/"home"),"PYTHONPATH":str(dest),"PYTHONDONTWRITEBYTECODE":"1","PYTHONNOUSERSITE":"1","LANG":"C.UTF-8"}
        subprocess.run([sys.executable,"-m","unittest","discover","-s","tests","-p","test_*.py","-v"],cwd=dest,env=env,check=True,timeout=90)
        print(json.dumps({"status":"ABC_OFFLINE_CANDIDATE_CHECKED","sha256":sha,"static_contracts":True,"cadence_guard":True,"release_authorized":False,"real_installation_tested":False,"main_executed":False}))
if __name__=="__main__":run()
