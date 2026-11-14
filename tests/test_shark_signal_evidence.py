"""Synthetic tests: future-only Squalincome event ↔ COT witness lineage.

No live SQLite, HTTP, broker, credentials, artificial trading signals or alerts.
The sample 'observations' are created by this test only. Capture MUST be called
inside the SAME transaction as a freshly inserted authentic history row.
"""
from datetime import datetime, timedelta, timezone
import json
import sqlite3
import unittest

from scripts import shark_cot_asof_witness as witness
from scripts import shark_signal_evidence as evidence

UTC=timezone.utc
AT=datetime(2026,11,4,11,0,tzinfo=UTC)
OBSERVED=datetime(2026,11,4,11,16,tzinfo=UTC)
CLOSE=datetime(2026,11,4,11,0,tzinfo=UTC)
NOW=OBSERVED+timedelta(seconds=2)
CURRENT="2026-10-27"
PRIOR="2026-10-20"


def iso(value):
    return value.astimezone(UTC).isoformat().replace("+00:00","Z")


def fixture():
    db=sqlite3.connect(":memory:")
    db.executescript("""
      CREATE TABLE cot_reports(
        dataset TEXT NOT NULL,code TEXT NOT NULL,report_date TEXT NOT NULL,
        oi REAL NOT NULL,first_long REAL NOT NULL,first_short REAL NOT NULL,
        second_long REAL NOT NULL,second_short REAL NOT NULL,
        PRIMARY KEY(dataset,code,report_date));
      CREATE TABLE cot_first_seen(
        dataset TEXT,code TEXT,report_date TEXT,first_seen_at TEXT,
        PRIMARY KEY(dataset,code,report_date));
      CREATE TABLE squalincome_history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        symbol TEXT NOT NULL,state TEXT,cot_side INTEGER,price_side INTEGER,
        h4_side INTEGER,h1_side INTEGER,m15_side INTEGER,price_state TEXT,
        report_date TEXT,price_time TEXT,observed_at TEXT,
        cot_weekly REAL,origin TEXT);
    """)
    # Mapped COT legs for EURUSD, EURJPY and XAUUSD.
    # Prior net exposure: 1% for each series.
    # New net exposures: EUR +5.0%, JPY +1.5%, XAU +5.0%
    for dataset,code,change in (
        ("tff","099741",50), ("tff","097741",15),
        ("disagg","088691",50)
    ):
        for week in (PRIOR,CURRENT):
            increased=change if week==CURRENT else 0
            db.execute("INSERT INTO cot_reports VALUES(?,?,?,?,?,?,?,?)",
                       (dataset,code,week,1000.,100.+increased,90.,
                        120.+increased,110.))
    db.commit()
    witness.ensure_schema(db)
    evidence.ensure_schema(db)
    return db


def insert_history(db,*,symbol="EURUSD",side=1,price_side=1,h4=1,h1=1,
                   m15=1,price_state="confirmed",weekly=None,
                   observed=OBSERVED,closed=CLOSE,report=CURRENT,
                   origin="update"):
    if weekly is None:
        weekly={"EURUSD":5.0,"EURJPY":3.5,"XAUUSD":5.0,"USDJPY":-1.5}.get(symbol,5.0)
    cur=db.execute(
        "INSERT INTO squalincome_history "
        "(symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (symbol,"aligned" if side==price_side else "divergent",
         side,price_side,h4,h1,m15,price_state,report,iso(closed),
         iso(observed),weekly,origin))
    return cur.lastrowid


class SignalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.db=fixture()

    def tearDown(self):
        self.db.close()

    def capture(self,**kwargs):
        clock=kwargs.pop("clock",NOW)
        with self.db:
            hid=insert_history(self.db,**kwargs)
            return evidence.capture(self.db,history_id=hid,clock=clock)

    def test_future_legacy_cot_is_locally_observed_then_linked(self):
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM cot_first_seen").fetchone()[0],0)
        witness.witness(self.db,clock=AT)
        result=self.capture()
        self.assertEqual(result["status"],"FUTURE_OBSERVATION_CERTIFIED_LOCALLY")
        self.assertEqual(result["cotReportsVersionedForSignal"],2)
        self.assertFalse(result["historicalH1QualityIndependentlyAttested"])
        self.assertFalse(result["realAggressorVolumeKnown"])
        self.assertEqual(result["tradingEdge"],"NOT_ESTABLISHED")
        self.assertEqual(result["brokerCalls"],0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM cot_first_seen").fetchone()[0],0)
        row=self.db.execute(
            "SELECT source_version_evidence,evidence_digest FROM "
            "research_squalincome_cot_links").fetchone()
        proof=json.loads(row[0])
        self.assertEqual(len(proof),2)
        self.assertEqual({x["week"] for x in proof},{PRIOR,CURRENT})
        self.assertEqual(len(row[1]),64)
        safe=json.dumps(result)+json.dumps(evidence.summarize(self.db))
        self.assertNotIn("1000.0",safe)
        self.assertNotIn("2026-11-04T11:16",safe)
        self.assertFalse(evidence.summarize(self.db)["notificationsEnabled"])

    def test_crosses_require_all_four_versioned_contract_weeks(self):
        witness.witness(self.db,clock=AT)
        result=self.capture(symbol="EURJPY")
        self.assertEqual(result["cotReportsVersionedForSignal"],4)
        self.assertEqual(evidence.summarize(self.db)["marketsWithEvidence"],1)
        stored=self.db.execute(
            "SELECT source_version_evidence FROM research_squalincome_cot_links"
        ).fetchone()[0]
        self.assertEqual(len(json.loads(stored)),4)

    def test_witness_after_observation_never_authenticates_legacy_event(self):
        witness.witness(self.db,clock=OBSERVED+timedelta(seconds=5))
        with self.assertRaisesRegex(ValueError,"cot_value_witness_is_future"):
            self.capture()
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(evidence.summarize(self.db)["total"],0)

    def test_optional_capture_preserves_authentic_observation_without_proof(self):
        # A future release must NOT disable existing Squalincome observations
        # just because COT lineage is absent. Evidence remains strictly N/D.
        with self.db:
            hid=insert_history(self.db)
            result=evidence.capture_optional(self.db,history_id=hid,clock=NOW)
            self.assertEqual(result["status"],"COT_PROVENANCE_NOT_VERIFIABLE")
            self.assertFalse(result["originalSignalValuesMatched"])
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],1)
        self.assertEqual(evidence.summarize(self.db)["total"],0)
        self.assertFalse(result["notificationsEnabled"])
        self.assertEqual(result["brokerCalls"],0)

    def test_optional_capture_records_real_evidence_after_prior_witness(self):
        witness.witness(self.db,clock=AT)
        with self.db:
            hid=insert_history(self.db)
            result=evidence.capture_optional(self.db,history_id=hid,clock=NOW)
        self.assertEqual(result["status"],"FUTURE_OBSERVATION_CERTIFIED_LOCALLY")
        self.assertEqual(evidence.summarize(self.db)["total"],1)

    def test_database_failures_are_not_masked_as_missing_provenance(self):
        witness.witness(self.db,clock=AT)
        self.db.execute("DROP TABLE research_cot_asof_attestations")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            with self.db:
                hid=insert_history(self.db)
                evidence.capture_optional(self.db,history_id=hid,clock=NOW)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_cot_revision_must_be_attested_before_new_signal(self):
        witness.witness(self.db,clock=AT)
        self.db.execute(
            "UPDATE cot_reports SET second_long=second_long+10 "
            "WHERE code='099741' AND report_date=?", (CURRENT,))
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"matching_cot_witness_missing"):
            self.capture()
        # Rewitness the new current source values (without any CFTC API).
        witness.witness(self.db,clock=AT+timedelta(minutes=10))
        with self.assertRaisesRegex(ValueError,"original_signal_does_not_match_present_cot"):
            self.capture(weekly=5.)
        new=self.capture(weekly=6.)
        self.assertTrue(new["originalSignalValuesMatched"])

    def test_only_newly_inserted_event_before_commit_and_30_seconds(self):
        witness.witness(self.db,clock=AT)
        with self.assertRaisesRegex(ValueError,"live_observation_transaction_required"):
            evidence.capture(self.db,history_id=1,clock=NOW)
        with self.assertRaisesRegex(ValueError,"signal_observation_not_new"):
            self.capture(clock=NOW+timedelta(minutes=1))
        self.assertEqual(evidence.summarize(self.db)["total"],0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)

    def test_do_not_duplicate_witness_or_retroactively_relabel(self):
        witness.witness(self.db,clock=AT)
        self.capture()
        with self.assertRaisesRegex(ValueError,"observation_evidence_already_recorded"):
            with self.db:
                self.db.execute("BEGIN")  # SELECT alone does not open a transaction
                hid=self.db.execute(
                    "SELECT id FROM squalincome_history LIMIT 1").fetchone()[0]
                evidence.capture(self.db,history_id=hid,clock=NOW)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("UPDATE research_squalincome_cot_links SET cot_side=-1")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute("DELETE FROM research_squalincome_cot_links")
        self.assertEqual(evidence.summarize(self.db)["total"],1)

    def test_watch_m15_can_be_neutral_without_fake_confirmation(self):
        witness.witness(self.db,clock=AT)
        result=self.capture(m15=0,price_state="watch")
        self.assertTrue(result["originalSignalValuesMatched"])
        with self.assertRaisesRegex(ValueError,"signal_observation_not_new_or_invalid"):
            self.capture(m15=0,price_state="confirmed")

    def test_price_and_h1_are_strictly_gated_even_after_track_a_audit(self):
        witness.witness(self.db,clock=AT)
        for values in (
            {"h1":0}, {"h4":-1}, {"m15":-1,"price_state":"confirmed"},
            {"closed":OBSERVED+timedelta(minutes=15)},
            {"closed":CLOSE-timedelta(hours=4)},
            {"closed":CLOSE+timedelta(minutes=1)},
            {"price_state":"invented"}
        ):
            with self.subTest(values=values):
                with self.assertRaises(ValueError):
                    self.capture(**values)
        self.assertEqual(evidence.summarize(self.db)["total"],0)

    def test_cot_direction_and_weekly_value_must_match_live_algorithm(self):
        witness.witness(self.db,clock=AT)
        with self.assertRaisesRegex(ValueError,"original_signal_does_not_match_present_cot"):
            self.capture(weekly=12.)
        with self.assertRaisesRegex(ValueError,"original_signal_does_not_match_present_cot"):
            self.capture(side=-1,price_side=-1,h1=-1,h4=-1,m15=-1)
        with self.assertRaisesRegex(ValueError,"cot_report_not_recent"):
            self.capture(report=PRIOR)

    def test_no_previous_week_or_missing_leg_is_rejected(self):
        self.db.execute("DELETE FROM cot_reports WHERE report_date=?", (PRIOR,))
        self.db.commit()
        witness.witness(self.db,clock=AT)
        with self.assertRaisesRegex(ValueError,"cot_prior_week_not_present"):
            self.capture(symbol="EURJPY")
        self.assertEqual(evidence.summarize(self.db)["total"],0)

    def test_invalid_origins_and_symbols_do_not_create_a_link(self):
        witness.witness(self.db,clock=AT)
        for info in ({"origin":"retroactively_generated"},
                     {"symbol":"GER30"}):
            with self.assertRaises(ValueError):
                self.capture(**info)
        self.assertEqual(evidence.summarize(self.db)["total"],0)

    def test_database_limit_is_fail_closed_and_keeps_transaction_atomic(self):
        from unittest.mock import patch
        witness.witness(self.db,clock=AT)
        with patch.object(evidence,"MAX_LINKS",0):
            with self.assertRaisesRegex(ValueError,"evidence_capacity_exceeded"):
                self.capture()
        self.assertEqual(evidence.summarize(self.db)["total"],0)

    def test_naive_clock_and_preexisting_history_are_not_proof(self):
        witness.witness(self.db,clock=AT)
        with self.assertRaises(ValueError):
            self.capture(clock=datetime(2026,11,4,11,16))
        with self.db:
            history_id=insert_history(self.db)
        with self.assertRaisesRegex(ValueError,"live_observation_transaction_required"):
            evidence.capture(self.db,history_id=history_id,clock=NOW)
        self.assertEqual(evidence.summarize(self.db)["total"],0)


if __name__=="__main__":
    unittest.main()
