"""OFFLINE synthetic adversarial tests: atomic ORIGINAL decision, no backfill.

Exercises real price_store ingest+first-seen, real COT witness, genuine
shark_observation_bundle and immutable linked-source research modules.
NO live collector, broker API, trading, OCI, market evidence or PnL.
"""
from __future__ import annotations

import copy
from datetime import timedelta,timezone
import json
import sqlite3
import unittest

from scripts import shark_original_decision_atomic_gate as atomic
from scripts import shark_signal_ingest_decision_link as source_link
from scripts import shark_signal_evidence as cot
from scripts import shark_price_asof_evidence as price
from scripts import shark_ingest_first_seen as first
from scripts import shark_cot_asof_witness as witness
from scripts import shark_cvd_incremental_protocol as frozen
from test_shark_signal_ingest_decision_link import (
    setup_case, NOW, OBS, CLOSE, SECRET
)
from test_shark_signal_evidence import iso


def new_history(db,*,observed=OBS):
    return db.execute(
        "INSERT INTO squalincome_history "
        "(symbol,state,cot_side,price_side,h4_side,h1_side,m15_side,"
        "price_state,report_date,price_time,observed_at,cot_weekly,origin) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("EURUSD","aligned",1,1,1,1,1,"confirmed","2026-10-27",
         iso(CLOSE),iso(observed),5.,"update")
    )


def counts(db):
    return {
        "history":db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],
        "cot":db.execute(f"SELECT count(*) FROM {cot.TABLE}").fetchone()[0],
        "price":db.execute(f"SELECT count(*) FROM {price.TABLE}").fetchone()[0],
        "source":db.execute(f"SELECT count(*) FROM {source_link.TABLE}").fetchone()[0],
        "original_ingests":db.execute(
            f"SELECT count(*) FROM {first.TABLE}").fetchone()[0],
    }


class AtomicOriginalDecisionTests(unittest.TestCase):
    def setUp(self):
        self.db,_,self.doc=setup_case()

    def tearDown(self):
        self.db.close()

    def run_new(self, **kwargs):
        params={"insert_history":new_history,
                "original_document":self.doc,
                "clock":NOW}
        params.update(kwargs)
        return atomic.record_new(self.db,**params)

    def test_three_local_proofs_and_new_history_commit_as_one(self):
        result=self.run_new()
        self.assertEqual(counts(self.db),
                         {"history":1,"cot":1,"price":1,"source":1,
                          "original_ingests":1})
        self.assertTrue(result["wholeTransactionCommittedTogether"])
        self.assertTrue(result["noRetrospectiveAttach"])
        self.assertEqual(result["retailFirstSeen"],"UNKNOWN")
        self.assertEqual(result["cvdCoverage"],"UNKNOWN")
        self.assertFalse(result["brokerReceiptExternallyAuthenticated"])
        self.assertFalse(result["cotFirstSeenIndependentlyAuthenticated"])
        self.assertFalse(result["statisticalEdgeEstablished"])
        self.assertFalse(result["actualProspectiveOutcomesMeasured"])
        self.assertFalse(result["productionObserverWired"])
        self.assertFalse(result["ordersEnabled"])
        self.assertFalse(result["notificationsEnabled"])
        self.assertEqual(result["brokerCalls"],0)
        self.assertFalse(self.db.in_transaction)
        safe=json.dumps(result)+json.dumps(source_link.aggregate(self.db))
        self.assertNotIn(SECRET,safe)
        self.assertNotIn("EURUSD",safe)
        self.assertNotIn("2026-11-09",safe)
        self.assertNotIn("1.01",safe)

    def test_no_cot_version_attestation_is_not_falsely_accepted(self):
        # COT source revision after local first-seen attestation. The
        # original local proof cannot certify its new, later values.
        self.db.execute(
            "UPDATE cot_reports SET second_long=second_long+10 "
            "WHERE dataset='tff' AND code='099741' AND report_date='2026-10-27'")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                        "strict_pilot_requires_both_original_cot_price_proofs"):
            self.run_new()
        self.assertEqual(counts(self.db),
                         {"history":0,"cot":0,"price":0,"source":0,
                          "original_ingests":1})

    def test_original_price_document_changed_rejects_all_new_rows(self):
        bad=copy.deepcopy(self.doc)
        bad["timeframes"]["M15"][0]["c"]+=.000001
        with self.assertRaisesRegex(ValueError,
                      "strict_pilot_requires_both_original_cot_price_proofs"):
            self.run_new(original_document=bad)
        self.assertEqual(counts(self.db)["history"],0)
        self.assertEqual(counts(self.db)["source"],0)
        self.assertEqual(counts(self.db)["cot"],0)
        self.assertEqual(counts(self.db)["price"],0)

    def test_callback_error_after_insert_rolls_back_new_history(self):
        def interrupted(db):
            new_history(db)
            raise RuntimeError("fake_failure_after_insert")
        with self.assertRaisesRegex(RuntimeError,"fake_failure_after_insert"):
            self.run_new(insert_history=interrupted)
        self.assertEqual(counts(self.db)["history"],0)
        self.assertFalse(self.db.in_transaction)

    def test_borrowed_old_cursor_cannot_attach_to_committed_history(self):
        old=new_history(self.db)
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                                    "exactly_one_new_history_insert_required"):
            self.run_new(insert_history=lambda db:old)
        self.assertEqual(counts(self.db)["history"],1)
        self.assertEqual(counts(self.db)["source"],0)
        self.assertFalse(self.db.in_transaction)

    def test_bogus_select_and_insert_ignore_are_not_new_history(self):
        with self.assertRaisesRegex(ValueError,
                                    "exactly_one_new_history_insert_required"):
            self.run_new(insert_history=lambda db:
                         db.execute("SELECT 1"))
        self.assertEqual(counts(self.db)["history"],0)
        new_history(self.db)
        self.db.commit()
        def ignored(db):
            return db.execute(
                "INSERT OR IGNORE INTO squalincome_history "
                "(id,symbol,state,cot_side,price_side,h4_side,h1_side,"
                "m15_side,price_state,report_date,price_time,observed_at,"
                "cot_weekly,origin) VALUES "
                "(1,'EURUSD','aligned',1,1,1,1,1,'confirmed',"
                "'2026-10-27','2026-11-09T12:00:00Z',"
                "'2026-11-09T12:01:00Z',5,'update')"
            )
        with self.assertRaisesRegex(ValueError,
                                    "exactly_one_new_history_insert_required"):
            self.run_new(insert_history=ignored)
        self.assertEqual(counts(self.db)["history"],1)
        self.assertEqual(counts(self.db)["source"],0)

    def test_extra_callback_sql_mutation_is_rejected_and_rolled_back(self):
        def extra(db):
            db.execute("UPDATE cot_reports SET second_long=second_long+3 "
                       "WHERE dataset='tff' AND code='099741'")
            return new_history(db)
        with self.assertRaisesRegex(ValueError,
                                    "exactly_one_new_history_insert_required"):
            self.run_new(insert_history=extra)
        self.assertEqual(counts(self.db)["history"],0)
        self.assertEqual(counts(self.db)["cot"],0)

    def test_explicit_new_transaction_required_and_no_outer_commit(self):
        self.db.execute("BEGIN")
        with self.assertRaisesRegex(ValueError,
                    "fresh_owned_original_observation_transaction_required"):
            self.run_new()
        self.assertTrue(self.db.in_transaction)
        self.db.rollback()
        self.assertEqual(counts(self.db)["history"],0)

    def test_missing_original_ingest_proof_causes_full_atomic_rollback(self):
        self.db.execute(f"DROP TABLE {first.TABLE}")
        self.db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.run_new()
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {cot.TABLE}").fetchone()[0],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {price.TABLE}").fetchone()[0],0)
        # The ingest proof table is INTENTIONALLY absent in this test.
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {source_link.TABLE}").fetchone()[0],0)

    def test_missing_research_link_schema_is_a_hard_sqlite_error(self):
        self.db.execute(f"DROP TABLE {source_link.TABLE}")
        self.db.commit()
        with self.assertRaises(sqlite3.DatabaseError):
            self.run_new()
        self.assertEqual(
            self.db.execute("SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {cot.TABLE}").fetchone()[0],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {price.TABLE}").fetchone()[0],0)
        self.assertEqual(
            self.db.execute(f"SELECT count(*) FROM {first.TABLE}").fetchone()[0],1)
        # The source link table is INTENTIONALLY absent here.

    def test_duplicate_original_signal_refuses_new_research_join(self):
        self.run_new()
        with self.assertRaises(ValueError):
            self.run_new()
        self.assertEqual(counts(self.db)["history"],1)
        self.assertEqual(counts(self.db)["source"],1)
        self.assertFalse(self.db.in_transaction)

    def test_clock_fails_before_attempted_write(self):
        earlier=NOW-timedelta(days=2)
        with self.assertRaisesRegex(ValueError,
                      "frozen_prospective_study_start_or_digest_invalid"):
            self.run_new(clock=earlier)
        with self.assertRaisesRegex(ValueError,
                      "explicit_genuine_utc_observation_clock_required"):
            self.run_new(clock="2026-11-09T12:01:02Z")
        with self.assertRaises(ValueError):
            self.run_new(clock=NOW.astimezone(
                timezone(timedelta(hours=1))))
        self.assertEqual(counts(self.db)["history"],0)

    def test_protocol_fingerprint_unchanged_no_outcomes_created(self):
        self.assertEqual(frozen.protocol_sha256(),
                         frozen.FROZEN_PROTOCOL_SHA256)
        result=self.run_new()
        self.assertFalse(result["actualProspectiveOutcomesMeasured"])
        self.assertFalse(result["statisticalEdgeEstablished"])


if __name__=="__main__":
    unittest.main()
