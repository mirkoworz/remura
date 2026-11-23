"""V20.6: ONLY NEW tests for the privacy-safe two-retail snapshot audit."""
from __future__ import annotations
import copy
import json
import unittest

from v206_two_retail_snapshot_audit import audit

MSTAMP="2026-11-23T02:55:17Z"
CSTAMP="2026-11-23T02:53:02Z"
SYMS=[f"FX{i:03d}" for i in range(1,31)]


def fixture():
    my={s:{"t":MSTAMP,"lPct":70,"sPct":30} for s in SYMS}
    capital={s:{"t":CSTAMP,"lPct":60.0,"sPct":40.0,"metric":"client_positions"}
             for s in SYMS[:29]}
    capital["CF031"]={"t":CSTAMP,"lPct":60.0,"sPct":40.0,"metric":"client_positions"}
    capital["CF032"]={"t":CSTAMP,"lPct":60.0,"sPct":40.0,"metric":"client_positions"}
    return (
        {"status":"ok","source":"Myfxbook Community Outlook",
         "updatedAt":MSTAMP,"symbols":my},
        {"status":"ok","source":"Capital.com Client Sentiment",
         "environment":"demo","metric":"client_positions",
         "updatedAt":CSTAMP,"symbols":capital}
    )


class V206NewGuards(unittest.TestCase):
    def test_only_29_shared_symbols_and_no_private_names_exported(self):
        a,c=fixture()
        r=audit(a,c)
        self.assertEqual(r["overlap_market_count"],29)
        self.assertEqual(r["capital_markets_not_in_public_myfxbook"],2)
        self.assertEqual(r["majority_orientation"]["agree"],29)
        self.assertEqual(r["mean_absolute_long_percentage_point_difference"],10.0)
        self.assertEqual(r["snapshot_gap_seconds"],135)
        data=json.dumps(r)
        self.assertNotIn("FX001",data)
        self.assertNotIn("CF031",data)
        self.assertFalse(r["per_market_values_or_names_exported"])
        self.assertFalse(r["directional_alpha_established"])

    def test_opposite_and_neutral_majorities_are_separate(self):
        a,c=fixture()
        c["symbols"]["FX001"]["lPct"]=30
        c["symbols"]["FX001"]["sPct"]=70
        c["symbols"]["FX002"]["lPct"]=50
        c["symbols"]["FX002"]["sPct"]=50
        r=audit(a,c)
        self.assertEqual(r["majority_orientation"],{"agree":27,"opposite":1,"neutral":1})
        self.assertEqual(r["bucket_counts"]["abs_diff_ge_30pp"],1)
        self.assertEqual(r["bucket_counts"]["opposite_extreme_ge_70_le_30"],1)

    def test_reject_future_mismatched_individual_record(self):
        a,c=fixture()
        c["symbols"]["FX001"]["t"]="2026-11-23T04:00:00Z"
        with self.assertRaisesRegex(ValueError,"misaligned"):
            audit(a,c)

    def test_reject_noncontemporaneous_snapshots(self):
        a,c=fixture()
        c["updatedAt"]="2026-11-22T02:53:02Z"
        with self.assertRaisesRegex(ValueError,"contemporaneous"):
            audit(a,c)

    def test_reject_wrong_metric_source_and_demo_identity(self):
        for k,v in (("metric","investor_cash"),("environment","live"),("source","Fiction")):
            a,c=fixture()
            c[k]=v
            with self.subTest(k=k),self.assertRaisesRegex(ValueError,"feed_identity"):
                audit(a,c)

    def test_reject_broken_complement_and_invalid_numbers(self):
        for value in (float("nan"),-1,101,True):
            a,c=fixture()
            c["symbols"]["FX001"]["lPct"]=value
            with self.subTest(value=value),self.assertRaises(ValueError):
                audit(a,c)
        a,c=fixture()
        c["symbols"]["FX001"]["lPct"]=65
        with self.assertRaisesRegex(ValueError,"complement"):
            audit(a,c)


if __name__=="__main__":
    unittest.main()
