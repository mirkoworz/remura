# REMURA Contributors v0.36 LAB — 16/11/2026 16:27 CET
import unittest
from copy import deepcopy
from datetime import datetime
from test_explicit_level_contract_lab_v1 import man
from test_level_confluence_v1 import ASOF,OBS,REC,FUTURE,ANCHOR
import explicit_pine_wire_lab_v1 as w

def ms(s):
    return int(datetime.fromisoformat(s.replace("Z","+00:00")).timestamp()*1000)

def payload(**kw):
    row=dict(zip(("market","provider","ticker","product","contract"),w.INSTRUMENT))
    row.update(schema=w.WIRE,cohort=w.COHORT,symbol=w.CONFIG["symbol"],timeframe="5",
        method=w.METHOD,period_policy=w.POLICY,effort_result_method=w.CONFIG["effort_result_method"],
        config_id=w.CONFIG_ID,id="auto-1",period="WEEK",kind="DELTA_PEAK",
        price="1.08540",anchor_ms=ms(ANCHOR),observed_ms=ms(OBS),bar_close_ms=ms(OBS))
    row.update(kw)
    return row

def run(p=None,receipt=REC,manual=None,cutoff=ASOF):
    return w.handoff([dict(man(),config_id=w.CONFIG_ID)] if manual is None else manual,
          [{"payload":payload() if p is None else p,"received_ms":ms(receipt)}],
          asof_utc=cutoff,synthetic=True)

class WireTests(unittest.TestCase):
    def test_positive_uses_existing_e_comparator(self):
        result=run()
        self.assertEqual(result["near_pair_count"],1)
        self.assertEqual(result["automatic_status_counts"],{"NEAR":1})
        self.assertEqual(result["config_id"],w.CONFIG_ID)
        self.assertFalse(result["config_attested"])
        self.assertFalse(result["scientific_admission"])
        self.assertFalse(result["operational_signal"])
    def test_wrong_feed_or_config_rejected(self):
        for change in ({"symbol":"FX:EURUSD"},{"provider":"OANDA"},{"contract":"X"},
                       {"config_id":"wrong"},{"method":"OTHER"},{"effort_result_method":"OTHER"}):
            with self.assertRaises(ValueError):run(payload(**change))
    def test_manual_config_required(self):
        with self.assertRaises(ValueError):run(manual=[dict(man(),config_id="wrong")])
        with self.assertRaises(ValueError):run(manual=[man()])
    def test_receipt_is_external_and_late_excluded(self):
        result=run(receipt=FUTURE)
        self.assertEqual(result["automatic_late"],1)
        self.assertFalse(result["price_comparison_performed"])
        with self.assertRaises(ValueError):run(payload(available_utc=REC))
    def test_bad_clock_or_anchor(self):
        for change in ({"anchor_ms":ms(OBS)},{"observed_ms":ms(FUTURE)},
                       {"bar_close_ms":ms(REC)},{"bar_close_ms":True}):
            with self.assertRaises(ValueError):run(payload(**change))
        with self.assertRaises(ValueError):run(receipt="2026-11-14T19:59:00Z")
    def test_distinct_no_match_and_missing_manual(self):
        self.assertEqual(run(payload(price="1.08600"))["automatic_status_counts"],{"DISTANT":1})
        self.assertEqual(run(manual=[])["automatic_status_counts"],{"NO_COMPARABLE_MANUAL":1})
    def test_no_private_prices_or_mutation(self):
        p=payload();before=deepcopy(p)
        result=run(p)
        self.assertEqual(p,before)
        for term in ("1.08540","1.08530","friend-a","auto-1"):
            self.assertNotIn(term,str(result))
    def test_synthetic_opt_in_and_exact_schema(self):
        with self.assertRaises(ValueError):w.decode_wire(payload(),received_ms=ms(REC))
        p=payload();del p["period_policy"]
        with self.assertRaises(ValueError):run(p)
        with self.assertRaises(ValueError):run(payload(price=1.0854))
