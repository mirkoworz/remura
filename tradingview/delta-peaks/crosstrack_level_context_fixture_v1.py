# REMURA v0.8.105 LAB — 16/11/2026 16:27 CET
"""Actual pinned B and E, original B decision cutoff, no live input."""
from datetime import timedelta
from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,CLOSE,insert_history,iso
from test_explicit_level_contract_lab_v1 import man, automatic, meta
from explicit_level_contract_lab_v1 import anchor
from research_dossier_preview_v1 import dossier
from research_dashboard_preview_v1 import render

def run():
    db,doc=create()
    try:
        decision=CLOSE+timedelta(seconds=60)
        audit=decision+timedelta(seconds=60)
        witness.witness(db,clock=AT)
        with db:
            hid=insert_history(db,observed=decision,closed=CLOSE)
            proof=bundle.record(db,history_id=hid,observed_document=doc,clock=decision+timedelta(seconds=2))
        assert proof["state"]=="BOTH_LOCAL_PROOFS_PRESENT"
        db.execute("PRAGMA query_only=ON")
        before=db.total_changes
        obs=iso(CLOSE-timedelta(minutes=5))
        receipt=iso(CLOSE)
        anch=anchor("WEEK",obs).strftime("%Y-%m-%dT%H:%M:%SZ")
        manual=man()
        manual["entry"]["data"].update(observed_utc=obs,anchor_utc=anch)
        manual["entry"]["received_utc"]=receipt
        manual["entry"]["history"][0]["at_utc"]=iso(CLOSE+timedelta(seconds=10))
        manual["metadata"]=meta(known_utc=receipt)
        auto=automatic(observed_utc=obs,anchor_utc=anch,available_utc=receipt,metadata=meta(known_utc=receipt))
        def result(m,a):
            r=dossier(db,[],as_of_utc=iso(audit),origin="SYNTHETIC",
                level_evidence={"manual":m,"automatic":a})
            assert r["b_local_pairs"]==1 and not r["predictive_admission"]
            assert not r["orders_enabled"] and db.total_changes==before
            return r
        r=result([manual],[auto])
        assert r["level_context"]["decision_counts"]=={"CANDIDATE_NEAR_CONTEXT":1},r["level_context"]
        assert "confluenza candidata" in render(r) and "0.8.106" in render(r)
        assert "1.08530" not in render(r) and "friend-a" not in render(r)
        late=dict(auto,available_utc=iso(decision+timedelta(seconds=10)))
        assert result([manual],[late])["level_context"]["decision_counts"]=={"AUTOMATIC_LATE":1}
        assert result([], [auto])["level_context"]["decision_counts"]=={"MANUAL_NOT_AVAILABLE_ASOF":1}
        assert result([manual],[])["level_context"]["decision_counts"]=={"AUTOMATIC_MISSING":1}
        assert result([manual],[dict(auto,provider="FXCM")])["level_context"]["decision_counts"]=={"INCOMPATIBLE_METADATA_PRESENT":1}
        print("REMURA_D_B_E_LEVEL_CONTEXT_SYNTHETIC=PASS; ORIGINAL_CUTOFF; NO_FEED_EQUIVALENCE; NO_EDGE")
        # Actual v0.36 E wire evaluator, not a copied comparator. Same B proof.
        from explicit_pine_wire_lab_v1 import CONFIG_ID
        from test_explicit_pine_wire_lab_v1 import payload,ms
        wmanual=dict(manual,config_id=CONFIG_ID)
        wire=payload(observed_ms=ms(obs),bar_close_ms=ms(obs),anchor_ms=ms(anch))
        def wire_result(m,envelopes):
            r=dossier(db,[],as_of_utc=iso(audit),origin="SYNTHETIC",
                level_evidence={"manual":m,"envelopes":envelopes})
            assert r["b_local_pairs"]==1 and db.total_changes==before
            assert not r["predictive_admission"] and not r["orders_enabled"]
            assert r["level_context"]["transport"]=="SYNTHETIC_WIRE_V1"
            return r
        e={"payload":wire,"received_ms":ms(receipt)}
        r=wire_result([wmanual],[e])
        assert r["level_context"]["decision_counts"]=={"CANDIDATE_NEAR_CONTEXT":1},r
        assert r["level_context"]["coverage_counts"]=={"NEAR_PRESENT":1}
        assert "Trasporto Pine sintetico" in render(r)
        assert "1.08530" not in render(r) and "auto-1" not in render(r)
        late=dict(e,received_ms=ms(iso(decision+timedelta(seconds=10))))
        assert wire_result([wmanual],[late])["level_context"]["decision_counts"]=={"AUTOMATIC_LATE":1}
        distant=dict(e,payload=dict(wire,id="auto-2",price="1.08600"))
        r=wire_result([wmanual],[e,distant])
        assert r["level_context"]["coverage_counts"]=={"DISTANT_PRESENT":1,"NEAR_PRESENT":1}
        assert "Distanza presente" in render(r)
        from copy import deepcopy
        m=deepcopy(wmanual)
        m["entry"]["history"][0]["at_utc"]=iso(decision+timedelta(seconds=10))
        assert wire_result([m],[e])["level_context"]["decision_counts"]=={"MANUAL_NOT_AVAILABLE_ASOF":1}
        for bad in (dict(wire,provider="FXCM"),dict(wire,config_id="wrong")):
            try:
                wire_result([wmanual],[dict(e,payload=bad)])
            except ValueError:
                pass
            else:
                raise AssertionError("invalid wire admitted")
        print("REMURA_D_B_E_WIRE_SYNTHETIC=PASS; ORIGINAL_CUTOFF; NEAR_AND_DISTANT_VISIBLE; NO_EDGE")
    finally:
        db.close()

if __name__=="__main__":
    run()
