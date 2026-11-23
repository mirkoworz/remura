"""V20.5: ONLY new offline Git history reconstruction guard tests (synthetic inputs)."""
from __future__ import annotations
import json
import unittest
from v205_public_git_retention_recovery import merge_public_revisions, parse_history

A="a"*40
B="b"*40
C="c"*40


def rec(t,l=70):
    return {"t":t,"lPct":l,"sPct":100-l,"lLots":123,"sLots":45,"lPos":10,"sPos":4,
            "avgL":1.1,"avgS":1.2}


def pack(*rows,symbol="EURUSD"):
    return json.dumps({"symbol":symbol,"source":"Myfxbook Community Outlook",
                       "sampling":"observed at recorded timestamps","records":rows}).encode()


T1="2026-10-16T19:50:39Z"
T2="2026-10-24T04:23:44Z"
T3="2026-11-23T02:55:17Z"
R1=("2026-10-20T00:00:00+00:00")
R2=("2026-10-30T00:00:00+00:00")
R3=("2026-11-23T03:00:00+00:00")


class RealHistoryArchiveGuards(unittest.TestCase):
    def test_old_rows_restored_without_touching_current(self):
        rev=[(A,R1,pack(rec(T1))),(B,R2,pack(rec(T1),rec(T2))),
             (C,R3,pack(rec(T2),rec(T3)))]
        stats,rows=merge_public_revisions("EURUSD",rev)
        self.assertEqual(stats["recoverable_unconflicted_rows"],3)
        self.assertEqual(stats["current_rolling_rows"],2)
        self.assertEqual(stats["recovered_not_in_current_rolling_window"],1)
        self.assertEqual([x["row"]["t"] for x in rows],[T1,T2,T3])
        self.assertEqual(rows[0]["first_visible_in_local_git_revision"]["revision_sha"],A)

    def test_conflicting_timestamp_quarantined_never_repaired(self):
        rev=[(A,R1,pack(rec(T1,70),rec(T2,60))),
             (B,R2,pack(rec(T1,71),rec(T2,60),rec(T3,50)))]
        s,rows=merge_public_revisions("EURUSD",rev)
        self.assertEqual(s["conflicting_timestamp_rows_excluded"],1)
        self.assertEqual(s["snapshot_recovery_status"],"CONFLICTS_EXCLUDED_REVIEW")
        self.assertEqual([z["row"]["t"] for z in rows],[T2,T3])

    def test_reject_duplicate_or_reverse_timestamp_within_commit(self):
        for rows in [(rec(T1),rec(T1)),(rec(T2),rec(T1))]:
            with self.subTest(rows=rows),self.assertRaisesRegex(ValueError,"order"):
                parse_history(pack(*rows),"EURUSD")

    def test_reject_invalid_sentiment_and_nonfinite_metric(self):
        for n in (-1,101,float("nan")):
            with self.subTest(n=n),self.assertRaises(ValueError):
                parse_history(pack(rec(T1,n)),"EURUSD")

    def test_reject_wrong_symbol_missing_timezone_and_noncanonical_version(self):
        with self.assertRaisesRegex(ValueError,"symbol"):
            parse_history(pack(rec(T1),symbol="CADJPY"),"EURUSD")
        with self.assertRaisesRegex(ValueError,"utc_z_required"):
            parse_history(pack(rec("2026-10-16T19:50:39+01:00")),"EURUSD")
        with self.assertRaisesRegex(ValueError,"bad_commit"):
            merge_public_revisions("EURUSD",[("notasha",R1,pack(rec(T1)))])

    def test_reject_nonmonotone_git_committer_order_and_invalid_shape(self):
        with self.assertRaisesRegex(ValueError,"nonmonotonic_git"):
            merge_public_revisions("EURUSD",[(A,R2,pack(rec(T1))),(B,R1,pack(rec(T2)))])
        with self.assertRaises(ValueError):
            parse_history(json.dumps({"symbol":"EURUSD","records":"not array"}).encode(),"EURUSD")


if __name__=="__main__":
    unittest.main()
