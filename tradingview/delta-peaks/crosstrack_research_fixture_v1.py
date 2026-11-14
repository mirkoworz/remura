#!/usr/bin/env python3
# REMURA v0.8.56 LAB — 14/11/2026 CET — uses the pinned B synthetic fixture.
# Run ONLY from offline CI with separate B checkout on PYTHONPATH.
from datetime import timedelta
import json
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,CLOSE,insert_history,iso
from test_volume_features_v1 import fixture,changed
from research_dossier_preview_v1 import dossier
from research_dashboard_preview_v1 import render,notification_preview

def run():
    db,doc=create()
    try:
        observed=CLOSE+timedelta(seconds=60)
        now=observed+timedelta(seconds=2)
        witness.witness(db,clock=AT)
        with db:
            hid=insert_history(db,observed=observed,closed=CLOSE)
            b=bundle.record(db,history_id=hid,observed_document=doc,clock=now)
        assert b["state"]=="BOTH_LOCAL_PROOFS_PRESENT"
        close=int(CLOSE.timestamp()*1000)
        def coherent(p):
            p["quality"].update(lower_tf="1",daily_anchor="HL2")
            p["signed_result_atr"]=(p["ohlc"]["close"]-p["ohlc"]["open"])/p["ohlc"]["atr14"]
            p["efficiency"]=p["signed_result_atr"]/p["effort"]
            p["footprint"]["delta_pct"]=100*250/3550
        rows=[changed(fixture(close),coherent)]
        db.execute("PRAGMA query_only=ON")
        before=db.total_changes
        r=dossier(db,rows,as_of_utc=iso(now+timedelta(seconds=3)),origin="SYNTHETIC")
        assert r["b_local_pairs"]==1 and r["pair_counts"]=={"DESCRIPTIVE_CANDIDATE_ONLY":1},r["pair_counts"]
        assert r["relations"]["cot_vs_intrabar_delta"]=={"ALIGNED":1}
        assert db.total_changes==before
        # Real pinned B proof fixture predates the TEST CVD deployment:
        # ensure it cannot be backfilled by the new adapter.
        cvd=dossier(db,rows,as_of_utc=iso(now+timedelta(seconds=3)),origin="SYNTHETIC",cvd_rows=[])
        assert cvd["tv_cvd_join"]["pair_counts"]=={"BEFORE_CVD_DEPLOYMENT":1}
        assert db.total_changes==before
        assert not r["predictive_admission"] and not notification_preview(r)["sent"]
        page=render(r)
        assert "DATI SINTETICI" in page and "PRIVATE_FAKE_BROKER_IDENTIFIER" not in page
        print("REMURA_D_B_CROSS_TRACK_SYNTHETIC=PASS; NO_LIVE_DB; NO_ORDERS; NO_SEND")
    finally:
        db.close()
def run_cvd():
    from test_shark_cvd_cot_price_triage import TripleCausalTriageTests,SECRET,OBSERVED,NOW
    from aux_source_coverage_preview_v1 import coverage
    t=TripleCausalTriageTests()
    t.setUp()
    try:
        t._proof()
        t._cvd()
        for db in (t.main,t.private):
            db.execute("PRAGMA query_only=ON")
        before=(t.main.total_changes,t.private.total_changes)
        r=coverage(t.main,t.private,as_of_utc=iso(NOW+timedelta(seconds=5)),days=1,secret=SECRET)
        assert r["validLocalCotPricePairs"]==1 and r["distinctSignalsWithExactCVD"]==1
        assert not r["same_tv_decision_proven"] and not r["orders_enabled"]
        assert before==(t.main.total_changes,t.private.total_changes)
        print("REMURA_B_CVD_COVERAGE_SYNTHETIC=PASS; SEPARATE_DENOMINATOR; NO_LIVE_DB")
    finally:
        t.tearDown()

def run_aux():
    from test_shark_cvd_cot_price_triage import TripleCausalTriageTests,SECRET,NOW
    from test_shark_retail_crossdb_predecision import PredecisionCrossDbTests,AUTHORIZED,NOW as RETAIL_NOW
    from cvd_auxiliary_same_decision_preview_v1 import audit
    t=TripleCausalTriageTests(); t.setUp()
    try:
        t._proof(); t._cvd()
        for db in (t.main,t.private): db.execute("PRAGMA query_only=ON")
        before=(t.main.total_changes,t.private.total_changes)
        r=audit(t.main,t.private,[],as_of_utc=iso(NOW+timedelta(seconds=5)),secret=SECRET)
        assert r["counts"]["CT_EXACT_ALIGNED"]==1 and r["counts"]["TV_B_CLOCK_OUTSIDE_TV_HANDOFF"]==1
        assert r["counts"]["RETAIL_UNKNOWN"]==1
        dossier_ct=dossier(t.main,[],as_of_utc=iso(NOW+timedelta(seconds=5)),origin="SYNTHETIC",cvd_rows=[],
                           auxiliary=True,private_cvd_db=t.private,cvd_secret=SECRET)
        assert notification_preview(dossier_ct)["auxiliary_summary"]["ct_exact_known"]==1
        assert "CT_EXACT_ALIGNED" in render(dossier_ct)
        assert "ALL_LOCAL_PROOF_TYPES_SAME_B_DECISION" not in r["counts"]
        assert before==(t.main.total_changes,t.private.total_changes)
        wrong=audit(t.main,t.private,[],as_of_utc=iso(NOW+timedelta(seconds=5)),secret=b"other-authorized-private-secret!!")
        assert wrong["counts"]["CT_EXACT_UNKNOWN"]==1
    finally:
        t.tearDown()
    t=PredecisionCrossDbTests(); t.setUp()
    try:
        t.original(t.prepare()); t.core.execute("PRAGMA query_only=ON")
        before=t.core.total_changes
        r=audit(t.core,None,[],as_of_utc=iso(RETAIL_NOW+timedelta(seconds=5)),retail_root=t.folder,authorized_at=AUTHORIZED)
        assert r["counts"]["RETAIL_LOCAL_ORIGINAL_PIN_VERIFIED"]==1,r
        assert r["counts"]["CT_EXACT_UNKNOWN"]==1 and t.core.total_changes==before
        dossier_retail=dossier(t.core,[],as_of_utc=iso(RETAIL_NOW+timedelta(seconds=5)),origin="SYNTHETIC",
                               cvd_rows=[],auxiliary=True,retail_root=t.folder,retail_authorized_at=AUTHORIZED)
        assert notification_preview(dossier_retail)["auxiliary_summary"]["retail_pin_verified"]==1
        assert "RETAIL_LOCAL_ORIGINAL_PIN_VERIFIED" in render(dossier_retail)
        (t.folder/"retail-000001.sqlite3").unlink() # disposable synthetic fixture only
        r=audit(t.core,None,[],as_of_utc=iso(RETAIL_NOW+timedelta(seconds=5)),retail_root=t.folder,authorized_at=AUTHORIZED)
        assert r["counts"]["RETAIL_UNKNOWN"]==1
    finally:
        t.tearDown()
    print("REMURA_D_AUX_SAME_B_DECISION_SYNTHETIC=PASS; EXACT_CT_AND_RETAIL_SEPARATE_FIXTURES; NO_LIVE_DB")

def run_runtime():
    import sys
    from pathlib import Path
    sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
    from cvd_private_runtime_preview_v1 import preview,plan,MIN_CLOSE_MS
    db,doc=create()
    try:
        observed=CLOSE+timedelta(seconds=60)
        witness.witness(db,clock=AT)
        with db:
            hid=insert_history(db,observed=observed,closed=CLOSE)
            b=bundle.record(db,history_id=hid,observed_document=doc,clock=observed+timedelta(seconds=2))
        assert b["state"]=="BOTH_LOCAL_PROOFS_PRESENT"
        db.execute("PRAGMA query_only=ON")
        before=db.total_changes
        now=MIN_CLOSE_MS+120000
        windows=[{"start_ms":a,"end_ms":z,"rows":[]} for a,z in plan(now)]
        result=preview(db,windows,now=now,origin="SYNTHETIC")
        assert "DATI SINTETICI" in result["html"]
        assert result["coverage"]["valid_unique_bars"]==0 and result["notice"]["sent"] is False
        assert db.total_changes==before
        print("REMURA_D_PRIVATE_RUNTIME_SYNTHETIC=PASS; NO_NETWORK; NO_RAW_OUTPUT")
    finally:
        db.close()


def run_one_shot():
    # Pinned B real implementation, synthetic detached export, mock D1 transport.
    import sqlite3,tempfile
    from pathlib import Path
    import sys
    from hashlib import sha256
    from unittest.mock import patch
    sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
    import cvd_runtime_one_shot_v1 as o
    import cvd_staged_runtime_preflight_v1 as p
    import cvd_guarded_collection_v2 as c
    from cvd_runtime_singleflight_v1 import NAME
    from cvd_private_runtime_preview_v1 import MIN_CLOSE_MS
    from test_cvd_runtime_resource_gate_v1 import fixture as evidence
    from test_cvd_batch_nonoverlap_preview_v1 import response
    db,doc=create()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/"core.sqlite3"
            dest=sqlite3.connect(path)
            try:db.backup(dest)
            finally:dest.close()
            path.chmod(0o600);(root/NAME).touch(mode=0o600)
            raw=path.read_bytes()
            host,budget=evidence();now=MIN_CLOSE_MS+120000
            host["observed_ms"]=budget["observed_ms"]=now
            with patch.object(o.time,"time_ns",return_value=now*1000000),patch.object(o,"sample_host",return_value=host),patch.object(p,"sample_host",return_value=host),patch.object(c,"require_account_id",return_value="account"),patch.object(c,"require_account_token",return_value="token"),patch.object(c,"inspect_verified_inventory",return_value={c.MAIN_DB:"main",c.TEST_DB:"test"}),patch.object(c,"api_request",return_value={}) as api,patch.object(c,"fetch_page",return_value=response([],{"rows_read":1,"rows_written":0})) as page:
                r=o.run_once(root,{"core.sqlite3":sha256(raw).hexdigest()},root,"","",budget=budget,explicit=True,origin="SYNTHETIC")
            assert api.call_count==1 and page.call_count==len(c.plan(now))
            assert "DATI SINTETICI" in r["preview"]["html"] and not r["preview"]["notice"]["sent"]
            assert path.read_bytes()==raw and not r["orders_enabled"]
            print("REMURA_D_STAGED_ONE_SHOT_SYNTHETIC=PASS; PINNED_B; MOCK_D1; NO_LIVE_DB")
    finally:db.close()


def run_persisted():
    import sqlite3,tempfile,sys
    from pathlib import Path
    from hashlib import sha256
    from unittest.mock import patch
    sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
    import cvd_runtime_one_shot_v2 as o
    import cvd_staged_runtime_preflight_v1 as p
    import cvd_guarded_collection_v2 as c
    from cvd_runtime_singleflight_v1 import NAME
    from cvd_runtime_private_state_v1 import bucket,NAME as STATE
    from cvd_private_dashboard_reader_v1 import read_dashboard
    from cvd_private_runtime_preview_v1 import MIN_CLOSE_MS
    from test_cvd_runtime_resource_gate_v1 import fixture as evidence
    from test_cvd_batch_nonoverlap_preview_v1 import response
    db,doc=create()
    try:
        observed=CLOSE+timedelta(seconds=60)
        witness.witness(db,clock=AT)
        with db:
            hid=insert_history(db,observed=observed,closed=CLOSE)
            proof=bundle.record(db,history_id=hid,observed_document=doc,clock=observed+timedelta(seconds=2))
        assert proof["state"]=="BOTH_LOCAL_PROOFS_PRESENT"
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp); path=root/"core.sqlite3"
            dest=sqlite3.connect(path)
            try:db.backup(dest)
            finally:dest.close()
            path.chmod(0o600);(root/NAME).touch(mode=0o600)
            raw=path.read_bytes()
            host,budget=evidence();now=bucket(MIN_CLOSE_MS+900000)
            host["observed_ms"]=budget["observed_ms"]=now
            with patch.object(o.time,"time_ns",return_value=now*1000000),patch.object(o,"sample_host",return_value=host),patch.object(p,"sample_host",return_value=host),patch.object(c,"require_account_id",return_value="account"),patch.object(c,"require_account_token",return_value="token"),patch.object(c,"inspect_verified_inventory",return_value={c.MAIN_DB:"main",c.TEST_DB:"test"}),patch.object(c,"api_request",return_value={}) as api,patch.object(c,"fetch_page",return_value=response([],{"rows_read":1,"rows_written":0})) as page:
                args=(root,{"core.sqlite3":sha256(raw).hexdigest()},root,"","")
                r=o.run_once(*args,budget=budget,explicit=True,origin="SYNTHETIC")
                before=(api.call_count,page.call_count)
                duplicate=o.run_once(*args,budget=budget,explicit=True,origin="SYNTHETIC")
                assert before==(api.call_count,page.call_count)==(1,len(c.plan(now)))
            assert r["status"]=="LOCAL_PREVIEW_SAVED" and duplicate["status"]=="ALREADY_CLAIMED_NO_COLLECTION"
            saved=(root/STATE).read_bytes()
            view=read_dashboard(root,now=now,origin="SYNTHETIC",explicit=True)
            assert view["status"]=="CURRENT_EMPTY" and "DATI SINTETICI" in view["html"]
            assert read_dashboard(root,now=now+900000,origin="SYNTHETIC",explicit=True)["status"]=="OLDER_RESULT"
            assert (root/STATE).read_bytes()==saved and path.read_bytes()==raw and not view["orders_enabled"]
            print("REMURA_D_PERSISTED_DASHBOARD_SYNTHETIC=PASS; PINNED_B; MOCK_D1; DUPLICATE_ZERO_IO")
    finally:db.close()


def run_missing_b():
    # Main does not currently carry the pinned B proof modules. This fixture
    # models absent B tables, not a claim about the actual live DB schema.
    import sqlite3,sys
    from pathlib import Path
    from test_cvd_squalincome_asof_preview_v1 import coherent
    from test_cvd_telemetry_preview_v1 import T0
    from test_research_dossier_preview_v1 import stamp
    from cvd_archive_preview_v1 import validate_windows
    from cvd_radar_preview_v1 import aggregate_radar
    sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
    from cvd_private_runtime_preview_v1 import preview,plan
    db=sqlite3.connect(":memory:")
    try:
        db.execute("CREATE TABLE squalincome_history(id INTEGER PRIMARY KEY)")
        db.execute("PRAGMA query_only=ON")
        before=db.total_changes
        now=T0+120000; row=coherent()
        r=dossier(db,[],as_of_utc=stamp(now),origin="SYNTHETIC",cvd_rows=[row],auxiliary=True)
        assert r["b_audit_status"]=="LOCAL_PROOF_TABLES_INCOMPLETE"
        assert r["b_local_pairs"] is None and r["tv_cvd_join"] is None
        n=notification_preview(r)
        assert n["state"]=="B_PROOFS_UNAVAILABLE" and n["candidate_count"] is None and n["tv_cvd_match_count"] is None
        w=[{"start_ms":a,"end_ms":z,"rows":[row] if a<=T0<=z else []} for a,z in plan(now)]
        valid,stats=validate_windows(w,as_of_ms=now)
        radar=aggregate_radar(valid,as_of_ms=now)
        assert stats["valid_unique_bars"]==1 and radar["counts"]["OBSERVATION_ONLY"]==1
        out=preview(db,w,now=now,origin="SYNTHETIC")
        assert out["coverage"]["valid_unique_bars"]==1 and out["notice"]["tv_cvd_match_count"] is None
        assert "prove causali B non disponibili" in out["html"] and "Coppie CVD descrittive: N/D" in out["html"]
        assert db.total_changes==before and not out["orders_enabled"] and not out["notice"]["sent"]
        print("REMURA_D_MISSING_B_SYNTHETIC=PASS; UNKNOWN_NOT_ZERO; RADAR_INDEPENDENT; NO_LIVE_DB")
    finally:db.close()

if __name__=="__main__":
    run()
    run_cvd()
    run_aux()
    run_runtime()
    run_one_shot()
    run_persisted()
    run_missing_b()
