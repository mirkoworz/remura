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

if __name__=="__main__":
    run()
    run_cvd()
