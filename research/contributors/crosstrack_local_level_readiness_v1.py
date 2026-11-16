# REMURA Contributors v0.38 LAB — 16/11/2026 17:23 CET
import json,unittest
from copy import deepcopy
from datetime import datetime,timezone
from test_level_local_probe_batch_v1 import row,T
from level_local_probe_v1 import parse
from test_level_confluence_v1 import manual
from local_level_readiness_v1 import readiness,utc

def fixture():
    snapshot=row();raw=json.dumps(snapshot);d=parse(raw);week=snapshot["levels"][3]
    m=manual()
    m["data"].update(provider="FX",anchor_utc=utc(week["period_start_ms"]),observed_utc=utc(T))
    m["received_utc"]=utc(T+2000);m["history"]=[{"action":"APPROVED","at_utc":utc(T+3000)}]
    m["data"]["note"]="private-note"
    return raw,{"entry":m,"declared":dict(calendar=snapshot["calendar"],timezone=snapshot["timezone"],
        session=snapshot["session"],method=week["method"],rank=1,period_end_ms=week["period_end_ms"],
        configuration_digest=d["configuration_digest"],known_utc=utc(T+2000))}
def run(raw,m,cutoff=T+5000):
    return readiness(raw,m,asof_utc=utc(cutoff),synthetic=True)
class LocalLevelReadiness(unittest.TestCase):
    def test_declared_match_never_admits_comparison(self):
        raw,m=fixture();out=run(raw,[m])
        self.assertEqual(out["declared_match_pairs"],1)
        self.assertEqual(out["automatic_present_slots"],4)
        self.assertEqual(out["status"],"BLOCKED_UNATTESTED_METADATA")
        for k in ("price_comparison_performed","receipt_authenticated","source_equivalence_attested","scientific_admission","operational_signal"):
            self.assertFalse(out[k])
    def test_different_feed_label_not_equivalent(self):
        raw,m=fixture();m["entry"]["data"]["provider"]="FXCM"
        out=run(raw,[m]);self.assertEqual(out["declared_match_pairs"],0)
        self.assertEqual(out["mismatch_pair_counts"]["DECLARED_LABEL_MISMATCH"],4)
    def test_method_calendar_and_config_not_interchangeable(self):
        for k,v,reason in (("method","OTHER","METHOD_DECLARATION_MISMATCH"),
            ("timezone","America/New_York","CALENDAR_DECLARATION_MISMATCH"),
            ("configuration_digest","different","CONFIG_DECLARATION_MISMATCH"),
            ("period_end_ms",T,"PERIOD_BOUNDS_MISMATCH")):
            raw,m=fixture();m["declared"][k]=v;out=run(raw,[m])
            self.assertEqual(out["declared_match_pairs"],0);self.assertGreater(out["mismatch_pair_counts"][reason],0)
    def test_previous_observed_month_not_previous_month(self):
        raw,m=fixture();m["entry"]["data"]["period"]="PREVIOUS_MONTH"
        self.assertEqual(run(raw,[m])["declared_match_pairs"],0)
    def test_cutoffs_for_review_metadata_and_sender(self):
        raw,m=fixture();self.assertEqual(run(raw,[m],T+1000)["status"],"D_CLAIM_AFTER_CUTOFF")
        self.assertEqual(run(raw,[m],T+2000)["manual_review_excluded"],1)
        m["declared"]["known_utc"]=utc(T+6000)
        self.assertEqual(run(raw,[m])["manual_metadata_late"],1)
        self.assertEqual(run(raw,[m])["declared_match_pairs"],0)
    def test_private_content_and_nonmutation(self):
        raw,m=fixture();before=deepcopy(m);out=run(raw,[m]);self.assertEqual(m,before)
        for x in ("private-note","friend-a","1.08530","1.085301","manual_id"):
            self.assertNotIn(x,str(out))
    def test_synthetic_and_realtime_only(self):
        raw,m=fixture()
        with self.assertRaises(ValueError):readiness(raw,[m],asof_utc=utc(T+5000))
        p=json.loads(raw);p["mode"]="HISTORICAL_RECONSTRUCTION"
        with self.assertRaises(ValueError):run(json.dumps(p),[m])
if __name__=="__main__":unittest.main()
