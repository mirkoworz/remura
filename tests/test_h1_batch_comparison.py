"""Offline-only proof of exact v1.62 candidate H1 common-clock pairing."""
import copy
import datetime as dt
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import h1_batch_comparison as p

FULL = "2026-11-03T16:16:44Z"
INGEST = "2026-11-03T16:16:48Z"
POST = "2026-11-03T16:16:49Z"


def frame(closed, bars=60):
    return {"H1": {"lastClosedAt": closed, "bars": bars,
                    "ageMinutes": 999, "secret": "PRIVATE_OHLC"}}


def fixture():
    symbols = [f"M{i:03}" for i in range(32)] + ["EURUSD", "XAUUSD"]
    markets = [{"symbol": name, "timeframes": frame("2026-11-03T15:00:00Z")}
               for name in symbols]
    markets[-2]["timeframes"] = frame("2026-11-03T14:00:00Z")
    old = {"lastScanAt": FULL, "markets": markets,
           "secrets": ["PRIVATE_TOKEN", "BROKER_ACCOUNT"]}
    post = {"EURUSD": frame("2026-11-03T15:00:00Z"),
            "XAUUSD": frame("2026-11-03T15:00:00Z")}
    return old, post


def run(full=None, updated=None, ingest=INGEST, now=POST):
    if full is None or updated is None:
        f,u=fixture()
        full = f if full is None else full
        updated = u if updated is None else updated
    return p.compare_paired_h1(full, updated,
                               post_scan_utc=now, ingest_returned_utc=ingest)


class PairedH1Test(unittest.TestCase):
    def test_common_utc_time_recovery_and_pure_no_secret_output(self):
        baseline, updated = fixture()
        old = copy.deepcopy(baseline)
        new = copy.deepcopy(updated)
        result = run(baseline, updated)
        self.assertEqual(result["state"], "COMPARABLE")
        self.assertEqual(result["compared"], 2)
        self.assertEqual(result["fullScanH1ReadyAtSameUtc"], 1)
        self.assertEqual(result["postIngestH1ReadyAtSameUtc"], 2)
        self.assertEqual(result["staleToReady"], 1)
        self.assertEqual(result["freshestH1Advanced"], 1)
        self.assertEqual(result["unchangedH1"], 1)
        self.assertEqual(result["fullScanAgeSeconds"], 5)
        self.assertIn("NOT_PROOF_OF_INGEST_CAUSALITY", result["interpretation"])
        self.assertEqual(baseline, old)
        self.assertEqual(updated, new)
        content = str(result)
        for secret in ("EURUSD", "XAUUSD", "PRIVATE_TOKEN", "PRIVATE_OHLC",
                       "BROKER_ACCOUNT", "2026-11-03T16:16:49Z"):
            self.assertNotIn(secret, content)

    def test_fails_closed_for_missing_ambiguous_or_tampered_fullscan(self):
        base,updated=fixture()
        corruptions = [
            ({"markets": base["markets"]}, "INVALID_CLOCKS"),
            ({**base, "markets": []}, "INCOMPLETE_FULL_SCAN"),
            ({**base, "markets": base["markets"][:-1]}, "INCOMPLETE_FULL_SCAN"),
            ({**base, "markets": base["markets"]+[base["markets"][0]]},
             "INVALID_FULL_SCAN"),
            ({**base, "markets": "PRIVATE"}, "INVALID_FULL_SCAN"),
            ({**base, "lastScanAt": "2026-11-03T16:16:44"}, "INVALID_CLOCKS"),
            ({**base, "lastScanAt": "SECRET"}, "INVALID_CLOCKS"),
        ]
        for item,reason in corruptions:
            with self.subTest(reason=reason, variant=str(item)[:12]):
                result=run(item,updated)
                self.assertEqual(result["state"],reason)
                self.assertIsNone(result["compared"])
                self.assertIsNone(result["postIngestH1ReadyAtSameUtc"])
                self.assertNotIn("PRIVATE",str(result))
        self.assertEqual(run(base, {} )["state"],"MISSING_OR_UNBOUNDED")
        self.assertEqual(run(base, {"ABC": frame("2026-11-03T15:00:00Z")})["state"],
                         "INCOMPLETE_FULL_SCAN")
        self.assertEqual(run(base, {"secret/token": frame("2026-11-03T15:00:00Z")})["state"],
                         "INVALID_TARGETS")

    def test_fails_closed_for_clock_skew_expiry_and_late_postscan(self):
        base, updated=fixture()
        variants=[
            ({"ingest":"2026-11-03T16:16:40Z"}, "NON_COMPARABLE_CLOCKS"),
            ({"now":"2026-11-03T16:16:45Z"}, "NON_COMPARABLE_CLOCKS"),
            ({"now":"2026-11-03T17:00:00Z"}, "NON_COMPARABLE_CLOCKS"),
            ({"now":"2026-11-03T16:20:00Z"}, "NON_COMPARABLE_CLOCKS"),
            ({"ingest":"2026-11-03T16:16:48"}, "INVALID_CLOCKS"),
            ({"now":"TOKEN"}, "INVALID_CLOCKS"),
        ]
        for kw, reason in variants:
            with self.subTest(kw=kw):
                self.assertEqual(run(base,updated,**kw)["state"],reason)

    def test_prevents_future_h1_regression_and_unverifiable_bars(self):
        base, updated=fixture()
        versions=[
            ({"EURUSD":frame("2026-11-03T13:00:00Z"),"XAUUSD":updated["XAUUSD"]},
             "REGRESSED_H1"),
            ({"EURUSD":frame("2026-11-03T16:30:00Z"),"XAUUSD":updated["XAUUSD"]},
             "INCOMPLETE_H1"),
            ({"EURUSD":frame("2026-11-03T15:00:00Z",bars=54),
              "XAUUSD":updated["XAUUSD"]}, "INCOMPLETE_H1"),
            ({"EURUSD":frame("2026-11-03T15:00:00Z",bars=True),
              "XAUUSD":updated["XAUUSD"]}, "INCOMPLETE_H1"),
            ({"EURUSD":frame("2026-11-03T15:00:00"),
              "XAUUSD":updated["XAUUSD"]}, "INCOMPLETE_H1"),
        ]
        for doc, reason in versions:
            with self.subTest(reason=reason):
                output=run(base, doc)
                self.assertEqual(output["state"],reason)
                self.assertIsNone(output["staleToReady"])

    def test_two_hour_boundary_in_utc_not_local_rome(self):
        # At exactly 120m, the H1 is still allowed; a second later it is stale.
        full, updated = fixture()
        full["lastScanAt"]="2026-11-03T16:00:00Z"
        full["markets"][-2]["timeframes"]=frame("2026-11-03T14:00:00Z")
        updated["EURUSD"]=frame("2026-11-03T14:00:00Z")
        updated["XAUUSD"]=frame("2026-11-03T15:00:00Z")
        a=run(full,updated,ingest="2026-11-03T16:00:00Z",
              now="2026-11-03T16:00:00Z")
        b=run(full,updated,ingest="2026-11-03T16:00:01Z",
              now="2026-11-03T16:00:01Z")
        self.assertEqual(a["state"],"COMPARABLE")
        self.assertEqual(a["fullScanH1ReadyAtSameUtc"],2)
        self.assertEqual(b["state"],"COMPARABLE")
        self.assertEqual(b["fullScanH1ReadyAtSameUtc"],1)
        self.assertEqual(b["postIngestH1ReadyAtSameUtc"],1)

    def test_bounded_targets_and_no_network_calls(self):
        full, post = fixture()
        for n in (0,6,30):
            with self.subTest(n=n):
                doc={f"Q{i:03}":frame("2026-11-03T15:00:00Z")
                     for i in range(n)}
                self.assertEqual(run(full,doc)["state"],
                                 "MISSING_OR_UNBOUNDED")
        self.assertFalse(hasattr(p,"urllib"))
        self.assertFalse(hasattr(p,"sqlite3"))
        self.assertEqual(p.SCHEMA,"remura-h1-paired-readiness-research-v1")


if __name__=="__main__":
    unittest.main()
