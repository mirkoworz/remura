# REMURA Contributors v0.34 LAB — 16/11/2026 15:59 CET
"""Cross-track synthetic fixtures: actual pinned D code, E privacy-safe gate."""
import unittest
from datetime import datetime,timezone
from test_cvd_telemetry_preview_v1 import fixture,T0
from test_level_confluence_v1 import manual
from tv_confluence_compatibility_v1 import bridge

def utc(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def entry(i=1,provider="OANDA"):
    m=manual(i,price="1.110")
    m["data"].update(provider=provider,observed_utc=utc(T0-120000),anchor_utc=utc(T0-86400000))
    m["received_utc"]=utc(T0-60000)
    m["history"]=[{"action":"APPROVED","at_utc":utc(T0-1000)}]
    return m

def run(m,**kw):
    args=dict(received_ms=T0+5000,manual=m,asof_utc=utc(T0+10000),synthetic=True)
    args.update(kw)
    return bridge(fixture(),**args)

class CrossTrackCompatibilityTests(unittest.TestCase):
    def test_equal_price_not_equal_instrument(self):
        out=run([entry(),entry(2,"FXCM")])
        self.assertEqual(out["source_symbol"],"FX:EURUSD")
        self.assertEqual(out["manual_approved_asof"],2)
        self.assertEqual(out["manual_provider_counts"],{"FXCM":1,"OANDA":1})
        self.assertEqual(len(out["automatic_levels"]),3)
        self.assertEqual(out["status"],"COMPATIBILITY_BLOCKED")
        self.assertFalse(out["price_comparison_performed"])
        self.assertEqual(out["descriptive_near_count"],0)
        self.assertFalse(out["operational_signal"])
    def test_same_prefix_still_not_attested(self):
        out=run([entry(provider="FX")])
        self.assertEqual(out["manual_approved_asof"],1)
        self.assertTrue(all("PERIOD_ANCHOR_NOT_ATTESTED" in x["reasons"] for x in out["automatic_levels"]))
        self.assertFalse(out["source_equivalence_attested"])
    def test_future_receipt_not_visible(self):
        out=run([entry()],asof_utc=utc(T0+4000))
        self.assertEqual(out["status"],"D_NOT_KNOWN_AT_CUTOFF")
        self.assertEqual(out["automatic_levels"],[])
        self.assertIsNone(out["radar_status"])
    def test_late_approval_and_revocation(self):
        m=entry();m["history"][0]["at_utc"]=utc(T0+20000)
        self.assertEqual(run([m])["manual_approved_asof"],0)
        m=entry();m["history"].append({"action":"REVOKED","at_utc":utc(T0+1000)});m["status"]="REVOKED"
        self.assertEqual(run([m])["manual_excluded"],1)
    def test_validate_wrong_cohort_and_receipt(self):
        p=fixture();p["snapshot"]["symbol"]="OANDA:EURUSD"
        with self.assertRaises(ValueError):bridge(p,manual=[],received_ms=T0+5000,asof_utc=utc(T0+10000),synthetic=True)
        with self.assertRaises(ValueError):run([],received_ms=T0-1000)
    def test_no_private_content(self):
        m=entry();m["subject"]="secret-subject";m["data"]["note"]="private-note"
        out=str(run([m]))
        for s in ("secret-subject","private-note","manual_id","1.110","raw_json"):
            self.assertNotIn(s,out)
    def test_explicit_synthetic_only(self):
        with self.assertRaises(ValueError):run([],synthetic=False)

if __name__=="__main__":unittest.main()
