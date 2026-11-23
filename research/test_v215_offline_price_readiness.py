"""REMURA A V21.5 — new offline-only real-receipt / PRIVATE copy readiness tests.

Market bars in this file are SYNTHETIC, the V20.3 receipt proof is the existing
authenticated GitHub aggregate. Not evidence of actual broker price coverage.
"""
from __future__ import annotations
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from v215_offline_price_readiness import probe, SCHEMA, VERSION

UTC=timezone.utc
START=datetime(2026,11,23,4,45,tzinfo=UTC)

def sample(count=112,miss=None,provider="ctrader"):
    rows=[]
    for k in range(count):
        t=START+timedelta(minutes=15*k)
        if t==miss:continue
        rows.append({"t":t.strftime("%Y-%m-%dT%H:%M:%SZ"),
                     "o":1.1,"h":1.101,"l":1.099,"c":1.1001})
    return {"symbol":"EURUSD","provider":provider,
            "providerSymbol":"LOCAL_SYNTHETIC_ONLY",
            "timeframes":{"M15":rows}}

def create_copy(tmp,payload):
    dest=Path(tmp)/"offline-remura-copy.sqlite3"
    with sqlite3.connect(dest) as conn:
        conn.execute("CREATE TABLE prices(symbol TEXT PRIMARY KEY,payload TEXT NOT NULL)")
        conn.execute("INSERT INTO prices VALUES (?,?)",("EURUSD",json.dumps(payload)))
    return dest

class TestA215OneCommandReadiness(unittest.TestCase):
    def test_no_copy_fail_closed_counts_only_no_signal(self):
        x=probe(None,as_of=datetime(2026,11,23,21,0,tzinfo=UTC))
        self.assertEqual(x["schema"],SCHEMA)
        self.assertEqual(x["version"],VERSION)
        self.assertEqual(x["status"],"AWAITING_LOCAL_PRIVATE_SQLITE_COPY")
        self.assertEqual(x["existingRealCvdTestReceipts"],12)
        self.assertEqual(x["independentTestReceiptM15EntryCohorts"],4)
        self.assertEqual(x["numberOfAdmittedProspectiveDecisions"],0)
        self.assertTrue(x["allTestReceiptsObservationOnly"])
        self.assertFalse(x["futureDirectionalReturnsComputed"])
        self.assertFalse(x["realCostsObserved"])
        self.assertEqual(x["networkCalls"],0)
        self.assertEqual(x["filesWritten"],0)

    def test_only_existing_local_snapshot_read_60m_and_4h(self):
        with tempfile.TemporaryDirectory() as folder:
            p=create_copy(folder,sample())
            before=p.read_bytes()
            result=probe(p,as_of=datetime(2026,11,23,12,0,tzinfo=UTC))
            self.assertEqual(result["status"],"COVERAGE_FOUND_DIRECTION_NOT_ATTESTED")
            self.assertEqual(result["horizons"]["60m"]["coverageCompleteM15Cohorts"],4)
            self.assertEqual(result["horizons"]["4h"]["coverageCompleteM15Cohorts"],4)
            self.assertEqual(result["horizons"]["24h"]["notYetMatureCohorts"],4)
            self.assertEqual(p.read_bytes(),before)
            s=json.dumps(result)
            for forbidden in ("LOCAL_SYNTHETIC_ONLY","1.1001",str(p)):
                self.assertNotIn(forbidden,s)

    def test_next_day_24h_maturity_requires_full_96_bar_windows(self):
        with tempfile.TemporaryDirectory() as folder:
            p=create_copy(folder,sample())
            result=probe(p,as_of=datetime(2026,11,24,9,0,tzinfo=UTC))
            self.assertEqual(result["horizons"]["24h"]["coverageCompleteM15Cohorts"],4)
            self.assertEqual(result["horizons"]["24h"]["notYetMatureCohorts"],0)
            self.assertFalse(result["alphaVerified"])

    def test_missing_broker_bar_never_interpolated(self):
        with tempfile.TemporaryDirectory() as folder:
            p=create_copy(folder,sample(miss=START+timedelta(minutes=15)))
            result=probe(p,as_of=datetime(2026,11,23,12,0,tzinfo=UTC))
            self.assertEqual(result["horizons"]["60m"]["coverageCompleteM15Cohorts"],2)
            self.assertEqual(result["horizons"]["60m"]["closedButPriceMissingCohorts"],2)
            self.assertEqual(result["horizons"]["4h"]["coverageCompleteM15Cohorts"],2)

    def test_wrong_provider_or_missing_offline_file_never_returns_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            p=create_copy(folder,sample(provider="tv"))
            with self.assertRaises(ValueError):
                probe(p,as_of=datetime(2026,11,23,12,0,tzinfo=UTC))
            with self.assertRaises(FileNotFoundError):
                probe(Path(folder)/"missing.sqlite3",
                      as_of=datetime(2026,11,23,12,0,tzinfo=UTC))

    def test_cli_default_zero_cost_and_requires_confirmed_offline_copy(self):
        script=Path(__file__).with_name("v215_offline_price_readiness.py")
        x=subprocess.run([sys.executable,str(script),
                          "--as-of-utc","2026-11-23T21:00:00Z"],
                         capture_output=True,text=True,check=True)
        self.assertEqual(json.loads(x.stdout)["status"],"AWAITING_LOCAL_PRIVATE_SQLITE_COPY")
        with tempfile.TemporaryDirectory() as folder:
            p=create_copy(folder,sample())
            x=subprocess.run([sys.executable,str(script),"--offline-sqlite",str(p),
                              "--as-of-utc","2026-11-23T21:00:00Z"],
                             capture_output=True,text=True)
            self.assertNotEqual(x.returncode,0)
            self.assertNotIn(str(p),x.stderr)
            self.assertIn("offline SQLite copy",x.stderr)
            x=subprocess.run([sys.executable,str(script),"--offline-sqlite",str(p),
                              "--confirm-offline-copy",
                              "--as-of-utc","2026-11-23T21:00:00Z"],
                             capture_output=True,text=True,check=True)
            self.assertEqual(json.loads(x.stdout)["horizons"]["60m"]["coverageCompleteM15Cohorts"],4)

if __name__=="__main__":
    unittest.main()
