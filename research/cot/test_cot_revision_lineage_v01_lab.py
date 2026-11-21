# REMURA COT revision LAB — only NEW tests, using the actual frozen collector with synthetic responses.
import datetime as dt
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"scripts"))
import cot_monitor
from price_store import connect
from cot_revision_lineage_v01_lab import (
    OfflineRevisionLedger, RevisionError, ALLOWED, SCHEMA
)

T1="2026-11-20T12:00:00Z"
T2="2026-11-20T18:00:00Z"
T3="2026-11-21T00:00:00Z"
KEY=("tff","112741","2026-11-17")
KEY_B=("tff","092741","2026-11-17")
VALUES=(1000.0,50.0,50.0,50.0,50.0)
REVISED=(1000.0,85.0,50.0,50.0,50.0)

def official_fixture(dataset, changed=False):
    spec=cot_monitor.DATASETS[dataset]
    return [
        {
            "report_date_as_yyyy_mm_dd":"2026-11-17T00:00:00",
            "cftc_contract_market_code":code,
            "open_interest_all":"1000",
            **{field:str(85 if changed and dataset=="tff" and
                           code=="112741" and field=="asset_mgr_positions_long"
                           else 50)
               for field in spec["keys"]}
        }
        for code in spec["codes"]
    ]

class NewRevisionLineageTests(unittest.TestCase):
    def setUp(self):
        self.ledger=OfflineRevisionLedger(synthetic=True)
    def tearDown(self):
        self.ledger.close()

    def test_01_actual_collector_overwrites_prior_report_without_replacing_original_first_seen(self):
        first=dt.datetime(2026,11,20,12,0,tzinfo=dt.timezone.utc)
        later=first+dt.timedelta(hours=6)
        with tempfile.TemporaryDirectory() as temp:
            db_path=Path(temp)/"private"/"cot.sqlite3"
            collect=lambda dataset, now:official_fixture(dataset,changed=now==later)
            a=cot_monitor.collect_once(db_path,first,collect)
            self.assertEqual(a["saved"],{"tff":11,"disagg":3})
            db=connect(db_path)
            try:
                old=db.execute(
                    "SELECT first_long FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",KEY
                ).fetchone()[0]
                observed=db.execute(
                    "SELECT first_seen_at FROM cot_first_seen WHERE dataset=? AND code=? AND report_date=?",KEY
                ).fetchone()[0]
            finally:db.close()
            b=cot_monitor.collect_once(db_path,later,collect)
            self.assertEqual(b["errors"],{})
            db=connect(db_path)
            try:
                new=db.execute(
                    "SELECT first_long FROM cot_reports WHERE dataset=? AND code=? AND report_date=?",KEY
                ).fetchone()[0]
                old_timestamp=db.execute(
                    "SELECT first_seen_at FROM cot_first_seen WHERE dataset=? AND code=? AND report_date=?",KEY
                ).fetchone()[0]
            finally:db.close()
        self.assertEqual((old,new),(50.0,85.0))
        self.assertEqual(observed,old_timestamp)
        self.assertEqual(old_timestamp,first.isoformat())
        # Proof of CODE CAPABILITY, not evidence of an actual correction in Oracle.

    def test_02_candidate_allowlist_agrees_with_real_main_collector(self):
        self.assertEqual(ALLOWED, {k:frozenset(v["codes"]) for k,v in cot_monitor.DATASETS.items()})
    def test_03_first_explicit_local_capture_creates_version_one_only(self):
        r=self.ledger.capture({KEY:VALUES},at_utc=T1)
        self.assertEqual((r["fresh_versions"],r["revisions"],r["unchanged"]),(1,0,0))
        self.assertEqual(self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T1)["version"],1)
    def test_04_unchanged_repeat_does_not_inflate_version_history(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        r=self.ledger.capture({KEY:VALUES},at_utc=T2)
        self.assertEqual((r["fresh_versions"],r["revisions"],r["unchanged"]),(0,0,1))
    def test_05_changed_report_creates_second_append_only_version(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        r=self.ledger.capture({KEY:REVISED},at_utc=T2)
        self.assertEqual(r["revisions"],1)
        a=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T1)
        b=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T2)
        self.assertNotEqual(a["content_sha256"],b["content_sha256"])
        self.assertEqual((a["version"],b["version"]),(1,2))
    def test_06_decision_before_initial_capture_remains_unknown(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        r=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc="2026-11-20T11:59:59Z")
        self.assertEqual(r["status"],"UNKNOWN_NO_VERSION_AT_DECISION")
        self.assertIsNone(r["content_sha256"])
    def test_07_asof_between_two_captures_returns_only_original_digest(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        old=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc="2026-11-20T14:00:00Z")
        self.ledger.capture({KEY:REVISED},at_utc=T2)
        between=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc="2026-11-20T14:00:00Z")
        self.assertEqual(between["version"],1)
        self.assertEqual(between["content_sha256"],old["content_sha256"])
    def test_08_after_revision_asof_uses_second_version_only(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        self.ledger.capture({KEY:REVISED},at_utc=T2)
        self.assertEqual(self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T3)["version"],2)
    def test_09_immutable_ledger_direct_update_rejected_by_sql_trigger(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_version"):
            self.ledger._db.execute("UPDATE captured_versions SET captured_at='2020-01-01T00:00:00Z'")
    def test_10_immutable_ledger_direct_delete_rejected_by_sql_trigger(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        with self.assertRaisesRegex(sqlite3.DatabaseError,"immutable_version"):
            self.ledger._db.execute("DELETE FROM captured_versions")
    def test_11_old_collector_first_seen_is_never_backfilled_to_candidate(self):
        # Candidate is EMPTY until fresh future observations are independently handled.
        r=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T3)
        self.assertEqual(r["status"],"UNKNOWN_NO_VERSION_AT_DECISION")
    def test_12_changed_content_with_reused_capture_time_fails_closed(self):
        self.ledger.capture({KEY:VALUES},at_utc=T1)
        with self.assertRaisesRegex(RevisionError,"revision_clock_not_strictly_later"):
            self.ledger.capture({KEY:REVISED},at_utc=T1)
        r=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T3)
        self.assertEqual(r["version"],1)
    def test_13_invalid_tracked_code_and_future_reference_rejected(self):
        with self.assertRaises(RevisionError):
            self.ledger.capture({("tff","999999",KEY[2]):VALUES},at_utc=T1)
        with self.assertRaises(RevisionError):
            self.ledger.capture({("tff",KEY[1],"2027-01-01"):VALUES},at_utc=T1)
    def test_14_negative_or_boolean_or_nan_values_rejected(self):
        for val in ((1000.0,True,0.0,0.0,0.0),
                    (1000.0,float("nan"),0.0,0.0,0.0),
                    (-1.0,50.0,50.0,50.0,50.0)):
            with self.assertRaises(RevisionError):
                self.ledger.capture({KEY:val},at_utc=T1)
    def test_15_distinct_market_code_cannot_inherit_another_codes_revision(self):
        self.ledger.capture({KEY:VALUES,KEY_B:VALUES},at_utc=T1)
        self.ledger.capture({KEY:REVISED},at_utc=T2)
        unchanged=self.ledger.as_of(dataset=KEY_B[0],code=KEY_B[1],report_date=KEY_B[2],decision_utc=T3)
        revised=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T3)
        self.assertEqual((unchanged["version"],revised["version"]),(1,2))
    def test_16_no_external_provenance_or_deploy_claim_even_with_version_history(self):
        r=self.ledger.capture({KEY:VALUES},at_utc=T1)
        proof=self.ledger.as_of(dataset=KEY[0],code=KEY[1],report_date=KEY[2],decision_utc=T3)
        self.assertEqual(r["schema"],SCHEMA)
        self.assertFalse(r["external_clock_verified"])
        self.assertFalse(r["official_cftc_publication_verified"])
        self.assertFalse(r["live_deploy_allowed"])
        self.assertFalse(proof["external_first_seen_verified"])
        self.assertFalse(proof["prospective_holdout_admission"])
        self.assertFalse(proof["institutional_edge_established"])
        self.assertEqual(proof["oracle_or_cloudflare_calls"],0)

if __name__=="__main__":
    unittest.main()
