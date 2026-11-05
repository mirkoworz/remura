"""Synthetic-only proof joins: no mutable future COT, no price-only bias.

A 'matching symbol and week' is NOT a causal proof. These tests exercise
the genuine prospective record() coordinator on in-memory SQLite; they never
touch REMURA LIVE, cTrader or the external HMAC CVD private database.
"""
from __future__ import annotations

from datetime import timedelta
import hashlib
import json
import sqlite3
import unittest

from scripts import shark_causal_pair_audit as audit
from scripts import shark_cot_asof_witness as witness
from scripts import shark_signal_evidence as cot
from scripts import shark_price_asof_evidence as price
from scripts import shark_observation_bundle as bundle
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT,NOW,OBSERVED,insert_history,iso


class CausalJointProofTests(unittest.TestCase):
    def setUp(self):
        self.db,self.doc=create()

    def tearDown(self):
        self.db.close()

    def _audit(self,at=None,days=7):
        self.db.execute("PRAGMA query_only=ON")
        try:
            return audit.audit(self.db,as_of=iso(at or NOW+timedelta(seconds=5)),
                               days=days)
        finally:
            self.db.execute("PRAGMA query_only=OFF")

    def _record(self,*,cot_first=True):
        if cot_first:
            witness.witness(self.db,clock=AT)
        with self.db:
            hid=insert_history(self.db)
            result=bundle.record(self.db,history_id=hid,
                                 observed_document=self.doc,clock=NOW)
        return result

    def test_valid_both_local_proofs_are_not_trading_or_cvd_cohorts(self):
        bundle_result=self._record()
        self.assertEqual(bundle_result["state"],"BOTH_LOCAL_PROOFS_PRESENT")
        found=self._audit()
        self.assertEqual(found["observedCotLinks"],1)
        self.assertEqual(found["observedPriceProofs"],1)
        self.assertEqual(found["locallyJoinedCausalPairs"],1)
        self.assertEqual(found["excludedLinks"],0)
        self.assertEqual(found["locallyJoinedPairsWithCompleteTickVolume"],1)
        self.assertEqual(found["priceProofsWithoutUsableCotLink"],0)
        self.assertEqual(found["institutionalPredictiveCohortsAdmissible"],0)
        self.assertEqual(found["netTradingOutcomesAdmissible"],0)
        self.assertFalse(found["cvdProxyEventTimeCausallyJoined"])
        self.assertFalse(found["independentOutOfSampleValidated"])
        self.assertFalse(found["originalSignalDirectionIndependentlyReproduced"])
        self.assertFalse(found["priceDocumentReadFromCurrentCache"])
        self.assertFalse(found["cotValuesReadFromCurrentCache"])
        self.assertEqual(found["brokerCalls"],0)
        raw=json.dumps(found)
        self.assertNotIn("PRIVATE_FAKE_BROKER_IDENTIFIER",raw)
        self.assertNotIn("1.015",raw)
        self.assertNotIn("099741",raw)

    def test_missing_tables_and_empty_proofs_are_not_zero_market_events(self):
        fresh=sqlite3.connect(":memory:")
        try:
            report=audit.audit(fresh,as_of=iso(NOW))
        finally:
            fresh.close()
        self.assertEqual(report["status"],"LOCAL_PROOF_TABLES_INCOMPLETE")
        self.assertIsNone(report["locallyJoinedCausalPairs"])
        self.assertIsNone(report["observedCotLinks"])
        self.assertEqual(report["institutionalPredictiveCohortsAdmissible"],0)
        complete_empty=self._audit()
        self.assertEqual(complete_empty["locallyJoinedCausalPairs"],0)
        self.assertEqual(complete_empty["observedPriceProofs"],0)

    def test_price_only_missing_cot_witness_cannot_be_joined(self):
        result=self._record(cot_first=False)
        self.assertEqual(result["state"],"PARTIAL_LOCAL_PROOFS")
        self.assertEqual(self._audit()["observedPriceProofs"],1)
        self.assertEqual(self._audit()["observedCotLinks"],0)
        self.assertEqual(self._audit()["priceProofsWithoutUsableCotLink"],1)
        self.assertEqual(self._audit()["locallyJoinedCausalPairs"],0)

    def test_cot_without_original_price_proof_not_promoted(self):
        witness.witness(self.db,clock=AT)
        with self.db:
            hid=insert_history(self.db)
            result=cot.capture(self.db,history_id=hid,clock=NOW)
        self.assertEqual(result["status"],"FUTURE_OBSERVATION_CERTIFIED_LOCALLY")
        report=self._audit()
        self.assertEqual(report["locallyJoinedCausalPairs"],0)
        self.assertEqual(report["excludedLinks"],1)
        self.assertEqual(report["exclusionReasons"],
                         {"MISSING_MATCHING_PRICE_PROOF":1})

    def test_pair_cannot_be_seen_before_recorded_at_asof(self):
        self._record()
        early=self._audit(at=OBSERVED+timedelta(seconds=1))
        self.assertEqual(early["observedCotLinks"],1)
        self.assertEqual(early["locallyJoinedCausalPairs"],0)
        self.assertEqual(early["exclusionReasons"],
                         {"COT_LINK_CREATED_AFTER_ASOF":1})

    def test_cross_observation_join_is_not_valid_even_when_week_matches(self):
        self._record()
        self.db.execute("DROP TRIGGER research_price_asof_no_update")
        self.db.execute(f"UPDATE {price.TABLE} SET observed_at=?",
                        (iso(OBSERVED+timedelta(seconds=1)),))
        self.db.execute(
            f"CREATE TRIGGER research_price_asof_no_update "
            f"BEFORE UPDATE ON {price.TABLE} "
            "BEGIN SELECT RAISE(ABORT,'append_only'); END")
        self.db.commit()
        out=self._audit()
        self.assertEqual(out["locallyJoinedCausalPairs"],0)
        self.assertEqual(out["exclusionReasons"],
                         {"PRICE_PROOF_NOT_SAME_OBSERVATION":1})

    def test_later_cot_witness_cannot_requalify_an_original_signal(self):
        self._record()
        self.db.execute("DROP TRIGGER research_cot_asof_no_update")
        self.db.execute(
            f"UPDATE {witness.TABLE} SET witnessed_at=?",
            (iso(OBSERVED+timedelta(minutes=5)),))
        self.db.execute(
            f"CREATE TRIGGER research_cot_asof_no_update "
            f"BEFORE UPDATE ON {witness.TABLE} "
            "BEGIN SELECT RAISE(ABORT,'append_only'); END")
        self.db.commit()
        out=self._audit()
        self.assertEqual(out["locallyJoinedCausalPairs"],0)
        self.assertEqual(out["exclusionReasons"],
                         {"COT_VALUE_VERSION_WITNESS_NOT_MATCHED":1})

    def test_missing_original_history_is_not_a_causal_success(self):
        self._record()
        self.db.execute("DELETE FROM squalincome_history")
        self.db.commit()
        report=self._audit()
        self.assertEqual(report["locallyJoinedCausalPairs"],0)
        self.assertEqual(report["exclusionReasons"],
                         {"ORIGINAL_SIGNAL_ROW_MISSING_OR_DUPLICATED":1})

    def test_tampered_cot_digest_or_missing_immutability_fails_closed(self):
        self._record()
        self.db.execute("DROP TRIGGER research_squalincome_links_no_update")
        with self.assertRaisesRegex(ValueError,"immutability_missing"):
            self._audit()
        self.db.execute(
            f"UPDATE {cot.TABLE} SET evidence_digest=?",
            ("0"*64,))
        self.db.execute(
            f"CREATE TRIGGER research_squalincome_links_no_update "
            f"BEFORE UPDATE ON {cot.TABLE} "
            "BEGIN SELECT RAISE(ABORT,'append_only'); END")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"digest_or_format_corrupt"):
            self._audit()

    def test_no_hidden_sqlite_writes_and_bounded_utc_clock(self):
        self._record()
        before=self.db.execute("PRAGMA total_changes").fetchone() if False else self.db.total_changes
        report=self._audit()
        self.assertEqual(before,self.db.total_changes)
        self.assertEqual(report["locallyJoinedCausalPairs"],1)
        for days in (0,8,True,"7",1.5):
            with self.subTest(days=days):
                with self.assertRaisesRegex(ValueError,"invalid_causal_audit_days"):
                    self._audit(days=days)
        with self.assertRaises(ValueError):
            audit.audit(self.db,as_of="2026-11-04T11:16:02")

if __name__=="__main__":
    unittest.main()
