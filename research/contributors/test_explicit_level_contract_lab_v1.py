# REMURA Contributors v0.35 LAB — 16/11/2026 16:17 CET
import unittest
from copy import deepcopy
from test_level_confluence_v1 import manual,auto,ASOF,OBS,REC,FUTURE
import explicit_level_contract_lab_v1 as m
def meta(**kw):
    return dict(dict(method=m.METHOD,period_policy=m.POLICY,known_utc=REC),**kw)
def man(i=1,price="1.08530",**kw):
    row=manual(i,price=price);row["data"].update(provider="LABFX")
    row["data"].update(kw)
    return {"entry":row,"metadata":meta()}
def automatic(**kw):
    return dict(dict(auto(provider="LABFX"),schema=m.SCHEMA,metadata=meta()),**kw)
def run(ms,aa=None,**kw):
    return m.evaluate(ms,[automatic()] if aa is None else aa,asof_utc=ASOF,synthetic=True,**kw)
class ExplicitContractTests(unittest.TestCase):
    def test_positive_and_negative_distance(self):
        out=run([man(),man(2,"1.08529")])
        self.assertEqual(out["near_pair_count"],1)
        self.assertEqual(out["automatic_status_counts"],{"NEAR":1})
        self.assertEqual(out["automatic_compared"],1)
        self.assertFalse(out["operational_signal"])
        self.assertFalse(out["source_equivalence_attested"])
        out=run([man(price="1.08529")])
        self.assertEqual(out["automatic_status_counts"],{"DISTANT":1})
        self.assertTrue(out["price_comparison_performed"])
    def test_wrong_instrument_or_anchor(self):
        for e in (man(provider="OANDA"),man(provider="FXCM"),man(anchor_utc="2026-11-08T00:00:00Z")):
            out=run([e]);self.assertEqual(out["manual_metadata_blocked"],1)
            self.assertFalse(out["price_comparison_performed"])
        for a in (automatic(provider="FX"),automatic(anchor_utc="2026-11-08T00:00:00Z")):
            out=run([man()],[a]);self.assertEqual(out["automatic_metadata_blocked"],1)
    def test_method_and_calendar_mismatch(self):
        for md in (meta(method="OTHER"),meta(period_policy="OTHER")):
            e=man();e["metadata"]=md
            self.assertFalse(run([e])["price_comparison_performed"])
            self.assertEqual(run([man()],[automatic(metadata=md)])["automatic_metadata_blocked"],1)
    def test_late_evidence_and_review(self):
        e=man();e["metadata"]=meta(known_utc=FUTURE)
        self.assertEqual(run([e])["manual_metadata_blocked"],1)
        e=man();e["entry"]["history"][0]["at_utc"]=FUTURE
        self.assertEqual(run([e])["manual_review_excluded"],1)
        for a in (automatic(available_utc=FUTURE),automatic(metadata=meta(known_utc=FUTURE))):
            self.assertEqual(run([man()],[a])["automatic_late"],1)
    def test_period_anchors(self):
        self.assertEqual(m.anchor("DAY",OBS).strftime("%Y-%m-%d"),"2026-11-14")
        self.assertEqual(m.anchor("WEEK",OBS).strftime("%Y-%m-%d"),"2026-11-09")
        self.assertEqual(m.anchor("CURRENT_MONTH",OBS).strftime("%Y-%m-%d"),"2026-11-01")
        self.assertEqual(m.anchor("PREVIOUS_MONTH","2027-01-10T00:00:00Z").strftime("%Y-%m-%d"),"2026-12-01")
    def test_private_fields_and_determinism(self):
        rows=[man(),man(2,"1.08535")]
        rows[0]["entry"]["data"]["note"]="private-note"
        before=deepcopy(rows)
        out=run(rows)
        self.assertEqual(out,run(rows[::-1]));self.assertEqual(rows,before)
        for text in ("private-note","friend-a","manual_id","1.08530","auto-1"):
            self.assertNotIn(text,str(out))
    def test_duplicates_and_unknown_schema(self):
        with self.assertRaises(ValueError):run([man(),man()])
        with self.assertRaises(ValueError):run([man()],[automatic(),automatic()])
        with self.assertRaises(ValueError):run([man()],[automatic(schema="remura.tv.flow.cvd.preview.v1")])
        with self.assertRaises(ValueError):m.evaluate([],[],asof_utc=ASOF)
    def test_missing_metadata_and_impossible_clock(self):
        e=man();e["metadata"]={}
        with self.assertRaises(ValueError):run([e])
        with self.assertRaises(ValueError):run([man()],[automatic(metadata=meta(known_utc="2026-11-14T19:59:00Z"))])
        with self.assertRaises(ValueError):run([man()],[automatic(available_utc="2026-11-14T19:59:00Z")])
