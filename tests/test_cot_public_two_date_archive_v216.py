"""REMURA B V21.6: targeted 28-real-row public archive, NO network tests.

All CFTC response rows below are SYNTHETIC TEST DATA. The code under test
is a guarded real-data fetcher, never invoked over HTTP by this test suite.
"""
from __future__ import annotations
import copy
import datetime as dt
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
import urllib.parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from cot_public_official_audit import CONFIG
from cot_public_two_date_archive_v216 import (
    DATES, CONFIRM, assemble, official_query,
)
from cot_intelligence_parity import validate, PUBLIC_SOURCE, reconcile

NOW = dt.datetime(2026, 11, 23, 22, 0, tzinfo=dt.timezone.utc)


def rows(ds: str) -> list[dict]:
    out = []
    cols = CONFIG[ds]["cols"]
    for day in DATES:
        for i, code in enumerate(CONFIG[ds]["codes"]):
            record = {
                "report_date_as_yyyy_mm_dd": day + "T00:00:00.000",
                "cftc_contract_market_code": code,
                "open_interest_all": str(100000 + i * 1000),
            }
            for j, key in enumerate(cols):
                record[key] = str(1000 + 25 * i + 30 * j + (8 if day == DATES[1] else 0))
            out.append(record)
    return out


def fetcher(overrides=None, calls=None):
    overrides = overrides or {}
    def _fetch(ds):
        if calls is not None:
            calls.append(ds)
        return copy.deepcopy(overrides.get(ds, rows(ds)))
    return _fetch


class B216PublicOfficialTwoDateArchiveTests(unittest.TestCase):
    def test_two_bounded_official_queries_only_requested_dates_and_expected_contracts(self):
        for ds, expected_rows in (("tff", 22), ("disagg", 6)):
            with self.subTest(dataset=ds):
                url=official_query(ds)
                x=urllib.parse.urlparse(url)
                self.assertEqual(x.scheme, "https")
                self.assertEqual(x.hostname, "publicreporting.cftc.gov")
                self.assertEqual(x.path, "/resource/" + CONFIG[ds]["id"] + ".json")
                q=urllib.parse.parse_qs(x.query)
                self.assertIn("$select", q)
                self.assertIn("$where", q)
                self.assertEqual(q["$limit"], [str(expected_rows + 1)])
                for day in DATES:
                    self.assertIn(day+"T00:00:00",q["$where"][0])
                self.assertNotIn("2026-11-03",q["$where"][0])
                self.assertNotIn("T00:00:00' OR 1=1",q["$where"][0])
        with self.assertRaises(ValueError):
            official_query("legacy")

    def test_no_http_when_no_confirmation_or_when_bad_confirmation(self):
        script=Path(__file__).resolve().parents[1] / "scripts/cot_public_two_date_archive_v216.py"
        default=subprocess.run([sys.executable,str(script)],
                               capture_output=True,text=True,check=True)
        output=json.loads(default.stdout)
        self.assertEqual(output["status"], "PUBLIC_CFTC_FETCH_NOT_AUTHORIZED")
        self.assertEqual(output["actualPublicGetRequests"], 0)
        self.assertEqual(output["filesWritten"], 0)
        self.assertEqual(output["expectedRows"], 28)
        wrong=subprocess.run([sys.executable,str(script),"--confirmation","BAD"],
                             capture_output=True,text=True)
        self.assertNotEqual(wrong.returncode,0)
        self.assertIn("Explicit exact confirmation",wrong.stderr)
        self.assertNotIn("http",default.stderr.lower())

    def test_with_injected_synthetic_responses_exactly_two_fetches_and_parity_compatible(self):
        calls=[]
        result=assemble(now=NOW,fetch=fetcher(calls=calls))
        self.assertEqual(calls,["tff","disagg"])
        self.assertEqual(result["rowCount"],28)
        self.assertEqual(result["schema"],"remura-cot-intelligence-snapshot-v1")
        self.assertFalse(result["truncated"])
        self.assertEqual(result["reportDates"],list(DATES))
        self.assertEqual(result["captureClock"],"public_api_read_at_not_official_publication")
        self.assertFalse(result["historicFirstSeenAttested"])
        self.assertFalse(result["officialReleaseTimestampAttested"])
        self.assertEqual(result["publicApiRequests"],2)
        self.assertEqual(result["privateProviderOrBrokerCalls"],0)
        raw=json.dumps(result["rows"],sort_keys=True,separators=(",",":"),
                       ensure_ascii=True,allow_nan=False).encode()
        self.assertEqual(result["dataSha256"],hashlib.sha256(raw).hexdigest())
        idx,read=validate(result,PUBLIC_SOURCE,NOW)
        self.assertEqual(len(idx),28)
        self.assertEqual(read,NOW)

    def test_missing_contradictory_or_duplicate_key_fails_without_fake_completion(self):
        missing=rows("tff")[:-1]
        with self.assertRaisesRegex(ValueError,"NOT_COMPLETE"):
            assemble(now=NOW,fetch=fetcher({"tff":missing}))
        duplicate=rows("tff")
        duplicate[-1]=copy.deepcopy(duplicate[0])
        with self.assertRaisesRegex(ValueError,"NOT_COMPLETE"):
            assemble(now=NOW,fetch=fetcher({"tff":duplicate}))
        conflicting=rows("tff")
        conflicting[-1]=copy.deepcopy(conflicting[0])
        conflicting[-1]["open_interest_all"]="999999"
        with self.assertRaisesRegex(ValueError,"CONFLICTING_PUBLIC_CFTC_DUPLICATE"):
            assemble(now=NOW,fetch=fetcher({"tff":conflicting}))

    def test_future_date_and_timestamp_guards_reject(self):
        with self.assertRaisesRegex(ValueError,"BEFORE_LAST"):
            assemble(now=dt.datetime(2026,11,16,tzinfo=dt.timezone.utc),
                     fetch=fetcher())
        with self.assertRaisesRegex(ValueError,"UTC_NOW_REQUIRED"):
            assemble(now=dt.datetime(2026,11,23,22,0),fetch=fetcher())
        future=rows("disagg")
        future[0]["report_date_as_yyyy_mm_dd"]="2026-11-24T00:00:00.000"
        with self.assertRaises(ValueError):
            assemble(now=NOW,fetch=fetcher({"disagg":future}))

    def test_not_a_substitute_for_private_first_seen_or_publication_time(self):
        result=assemble(now=NOW,fetch=fetcher())
        self.assertTrue(all(r["first_seen_at"] is None for r in result["rows"]))
        self.assertTrue(result["publicDataMayHaveBeenRevisedAfterPrivateCapture"])
        self.assertFalse(result["ordersOrSignalsEnabled"])
        self.assertEqual(set(result["datasetIds"]),{"tff","disagg"})
        for source in result["sourceReference"].values():
            self.assertTrue(source.startswith("https://publicreporting.cftc.gov/"))


if __name__=="__main__":
    unittest.main()
