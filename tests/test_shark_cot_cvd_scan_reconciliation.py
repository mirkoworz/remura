"""Synthetic only: exact ORIGINAL COT+OHLC ↔ private CVD M15 attempts.

No copied LIVE data, external network, broker calls, orders or trading claims.
"""
from datetime import timedelta
import copy
import json
import sqlite3
import unittest

from scripts import shark_cot_asof_witness as witness
from scripts import shark_cot_cvd_scan_reconciliation as join
from scripts import shark_cvd_scan_coverage as scans
from scripts import shark_observation_bundle as bundle
from test_shark_observation_bundle import create
from test_shark_signal_evidence import AT, CLOSE, NOW, OBSERVED, iso, insert_history
from test_shark_cvd_ledger import SECRET


class CvdSignalScanJoinTests(unittest.TestCase):
    def setUp(self):
        self.main, self.doc = create()
        self.private = sqlite3.connect(":memory:")
        scans.ensure_schema(self.private)

    def tearDown(self):
        self.main.close()
        self.private.close()

    def prove(self, *, observed=OBSERVED, capture_prefix=False):
        witness.witness(self.main, clock=AT)
        with self.main:
            hid = insert_history(self.main, observed=observed)
            result = bundle.record(
                self.main, history_id=hid,
                observed_document=self.doc, clock=observed+timedelta(seconds=2),
                capture_cvd_prefix=capture_prefix)
        self.assertEqual(result["state"], "BOTH_LOCAL_PROOFS_PRESENT")

    def record(self, doc=None, *, at=CLOSE+timedelta(minutes=1)):
        return scans.record(
            self.private, symbol="EURUSD", slot_closed_at=iso(CLOSE),
            source_document=self.doc if doc is None else doc,
            clock=at, secret=SECRET)

    def record_window(self, *, missing=(), unavailable=(),
                      altered_latest=False, late_latest=False,
                      mutate_earlier=None):
        """Seven genuine detector invocations, each from its OWN past slice.

        The earlier snapshots have different complete-document SHA values;
        do not reuse the eventual 11:00 source for older M15 closes.
        """
        for distance in range(join.WINDOW_PRIOR_SLOTS, -1, -1):
            if distance in missing:
                continue
            closed = CLOSE - timedelta(minutes=15*distance)
            earlier = copy.deepcopy(self.doc)
            if distance:
                earlier["timeframes"]["M15"] = earlier[
                    "timeframes"]["M15"][:-distance]
                earlier["lastComplete"] = earlier["timeframes"]["M15"][-1]["t"]
                for frame, span in (
                        ("H1", timedelta(hours=1)),
                        ("H4", timedelta(hours=4))):
                    earlier["timeframes"][frame] = [
                        bar for bar in earlier["timeframes"][frame]
                        if witness._parse(bar["t"])+span <= closed]
            if distance == 0 and altered_latest:
                earlier["timeframes"]["H1"][-1]["h"] += 0.001
            if distance == mutate_earlier:
                # Corrupt a prior CVD source's existing original M15 tick
                # volume without editing the later main observation. Each
                # scan remains technically evaluable, but historical M15
                # provenance must no longer match.
                earlier["timeframes"]["M15"][-12]["v"] += 1
            at = closed + timedelta(minutes=2 if
                                    (distance == 0 and late_latest) else 1)
            result = scans.record(
                self.private, symbol="EURUSD", slot_closed_at=iso(closed),
                source_document=None if distance in unavailable else earlier,
                clock=at, secret=SECRET)
            self.assertEqual(
                result["status"],
                "NOT_EVALUABLE" if distance in unavailable else "EVALUATED")

    def audit(self, *, at=NOW+timedelta(seconds=5)):
        before = self.main.total_changes, self.private.total_changes
        result = join.audit(self.main, self.private, as_of=iso(at),
                            days=1, secret=SECRET)
        self.assertEqual(before,
                         (self.main.total_changes, self.private.total_changes))
        return result

    def test_original_paired_signal_and_exact_source_scan_zero_is_not_negative(self):
        self.prove()
        self.assertEqual(self.record()["status"], "EVALUATED")
        out = self.audit()
        self.assertEqual(out["validOriginalCotPricePairs"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 1)
        self.assertEqual(sum(out["joinedScanGroups"].values()), 1)
        self.assertFalse(out["zeroNewTechnicalConfirmationsProveNoPriorCvd"])
        self.assertFalse(out["noLocalScanIsAnInstitutionalNegative"])
        self.assertEqual(out["institutionalNegativeControlsAdmissible"], 0)
        self.assertEqual(out["netOutcomesAdmissible"], 0)
        self.assertEqual(out["edge"], "NOT_ESTABLISHED")
        self.assertNotIn(self.doc["providerSymbol"], json.dumps(out))
        self.assertNotIn("1.015", json.dumps(out))

    def test_seven_consecutive_real_detector_invocations_are_only_local_coverage(self):
        self.prove()
        self.record_window()
        out = self.audit()
        groups = out["preSignalWindowGroups"]
        self.assertEqual(out["preSignalWindowM15Slots"], 7)
        self.assertEqual(out["preSignalWindowSpanMinutes"], 90)
        self.assertEqual(sum(groups.values()), 1)
        self.assertEqual(groups[
            "WINDOW_ALL_7_LOCALLY_EVALUATED_EARLIER_SOURCES_UNLINKED"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 1)
        self.assertFalse(out["windowEarlierSourcesCryptographicallyLinked"])
        self.assertFalse(out["windowFullEvaluationProvesNoHistoricalDivergence"])
        self.assertFalse(out["windowIsCompleteTradingNegativeControl"])
        self.assertFalse(out["independentBrokerClockVerified"])
        self.assertEqual(out["institutionalNegativeControlsAdmissible"], 0)
        self.assertNotIn(self.doc["providerSymbol"], json.dumps(out))

    def test_seven_private_prefixes_match_original_main_price_history(self):
        self.prove(capture_prefix=True)
        self.record_window()
        result = self.audit()
        groups = result["preSignalWindowGroups"]
        self.assertEqual(sum(groups.values()), 1)
        self.assertEqual(
            groups["WINDOW_ALL_7_M15_PREFIXES_VERIFIED_LOCAL_ONLY"], 1)
        self.assertEqual(
            groups["WINDOW_ALL_7_LOCALLY_EVALUATED_EARLIER_SOURCES_UNLINKED"], 0)
        self.assertFalse(result["windowFullEvaluationProvesNoHistoricalDivergence"])
        self.assertFalse(result["windowFullOHLCAndBrokerCollectionTimeIndependentlyVerified"])
        self.assertEqual(result["institutionalNegativeControlsAdmissible"], 0)
        self.assertEqual(result["netOutcomesAdmissible"], 0)

    def test_one_mutated_earlier_m15_tick_is_not_a_matching_window(self):
        self.prove(capture_prefix=True)
        self.record_window(mutate_earlier=3)
        result = self.audit()
        self.assertEqual(
            result["preSignalWindowGroups"]["UNKNOWN_WINDOW_PREFIX_MISMATCH"], 1)
        self.assertEqual(
            result["preSignalWindowGroups"][
                "WINDOW_ALL_7_M15_PREFIXES_VERIFIED_LOCAL_ONLY"], 0)
        self.assertEqual(result["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 1)
        self.assertEqual(result["institutionalNegativeControlsAdmissible"], 0)

    def test_missing_immutable_main_prefix_table_does_not_invent_match(self):
        self.prove()
        self.record_window()
        result = self.audit()
        self.assertEqual(
            result["preSignalWindowGroups"][
                "WINDOW_ALL_7_LOCALLY_EVALUATED_EARLIER_SOURCES_UNLINKED"], 1)
        self.assertEqual(
            result["preSignalWindowGroups"][
                "WINDOW_ALL_7_M15_PREFIXES_VERIFIED_LOCAL_ONLY"], 0)

    def test_one_missing_older_m15_invalidates_pre_signal_window_only(self):
        self.prove()
        self.record_window(missing=(3,))
        out = self.audit()
        self.assertEqual(out["preSignalWindowGroups"][
            "UNKNOWN_WINDOW_MISSING_ATTEMPT"], 1)
        # The terminal single-slot proof is still valid; earlier history
        # CANNOT be declared complete just because the terminal one matches.
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 1)
        self.assertEqual(out["institutionalNegativeControlsAdmissible"], 0)

    def test_one_explicit_not_evaluable_m15_invalidates_window(self):
        self.prove()
        self.record_window(unavailable=(3,))
        out = self.audit()
        self.assertEqual(out["preSignalWindowGroups"][
            "UNKNOWN_WINDOW_NOT_EVALUABLE"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 1)

    def test_last_m15_source_mutation_invalidates_window_without_changing_clocks(self):
        self.prove()
        self.record_window(altered_latest=True)
        out = self.audit()
        self.assertEqual(out["preSignalWindowGroups"][
            "UNKNOWN_WINDOW_LAST_SOURCE_MISMATCH"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "UNKNOWN_DIFFERENT_PRICE_SOURCE"], 1)

    def test_one_late_scan_cannot_create_pre_signal_window_retroactively(self):
        early = CLOSE + timedelta(minutes=1)
        self.prove(observed=early)
        self.record_window(late_latest=True)
        out = self.audit()
        self.assertEqual(out["preSignalWindowGroups"][
            "UNKNOWN_WINDOW_LATE_ATTEMPT"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL"], 1)

    def test_no_pilot_window_without_scans_is_never_a_negative(self):
        self.prove()
        out = self.audit()
        self.assertEqual(out["preSignalWindowGroups"][
            "UNKNOWN_WINDOW_MISSING_ATTEMPT"], 1)
        self.assertEqual(out["institutionalNegativeControlsAdmissible"], 0)
        self.assertEqual(out["netOutcomesAdmissible"], 0)

    def test_no_scan_is_unknown_not_negative(self):
        self.prove()
        out = self.audit()
        self.assertEqual(out["joinedScanGroups"]["UNKNOWN_MISSING_ATTEMPT"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 0)

    def test_recorded_unavailable_scan_is_unknown_not_zero(self):
        self.prove()
        scans.record(
            self.private, symbol="EURUSD", slot_closed_at=iso(CLOSE),
            source_document=None, clock=CLOSE+timedelta(minutes=1),
            secret=SECRET)
        out = self.audit()
        self.assertEqual(out["joinedScanGroups"][
            "UNKNOWN_ATTEMPT_NOT_EVALUABLE"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 0)

    def test_same_market_same_slot_different_source_cannot_match(self):
        self.prove()
        alternate = copy.deepcopy(self.doc)
        alternate["timeframes"]["H1"][-1]["h"] += 0.001
        self.record(alternate)
        out = self.audit()
        self.assertEqual(out["joinedScanGroups"][
            "UNKNOWN_DIFFERENT_PRICE_SOURCE"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "MATCHED_EVALUATION_ZERO_NEW_LOCAL_CVD"], 0)

    def test_scan_after_original_observation_not_backdated_as_known(self):
        # Main observation occurs 1m after the M15 closes. The CVD attempt
        # was actually 2m after the close, while still a valid scan slot.
        early_observation = CLOSE + timedelta(minutes=1)
        self.prove(observed=early_observation)
        self.record(at=CLOSE+timedelta(minutes=2))
        out = self.audit()
        self.assertEqual(out["validOriginalCotPricePairs"], 1)
        self.assertEqual(out["joinedScanGroups"][
            "UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL"], 1)

    def test_future_scan_in_historical_asof_remains_unknown(self):
        observed = CLOSE + timedelta(minutes=1)
        self.prove(observed=observed)
        self.record(at=CLOSE+timedelta(minutes=2))
        before = self.audit(at=CLOSE+timedelta(minutes=1,seconds=5))
        self.assertEqual(before["joinedScanGroups"][
            "UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL"], 1)
        later = self.audit(at=NOW+timedelta(seconds=5))
        self.assertEqual(later["joinedScanGroups"][
            "UNKNOWN_ATTEMPT_NOT_YET_KNOWN_AT_SIGNAL"], 1)

    def test_missing_price_or_cot_proof_has_no_signal_denominator(self):
        witness.witness(self.main, clock=AT)
        with self.main:
            hid = insert_history(self.main)
            bundle.record(self.main, history_id=hid,
                          observed_document=self.doc, clock=NOW)
        # This has already become a valid witness pair. To test a genuine
        # missing COT witness, use another pristine fixture instead.
        other, source = create()
        try:
            with other:
                hid = insert_history(other)
                bundle.record(other, history_id=hid,
                              observed_document=source, clock=NOW)
            result = join.audit(other, self.private, as_of=iso(NOW+timedelta(seconds=5)),
                                secret=SECRET)
            self.assertEqual(result["validOriginalCotPricePairs"], 0)
            self.assertEqual(sum(result["joinedScanGroups"].values()), 0)
            self.assertEqual(result["institutionalNegativeControlsAdmissible"], 0)
        finally:
            other.close()

    def test_missing_scan_schema_unavailable_not_fake_empty(self):
        self.prove()
        empty = sqlite3.connect(":memory:")
        try:
            result = join.audit(self.main, empty, as_of=iso(NOW+timedelta(seconds=5)),
                                secret=SECRET)
            self.assertEqual(result["status"],
                             "CVD_SCAN_ATTEMPT_EVIDENCE_UNAVAILABLE")
            self.assertEqual(result["validOriginalCotPricePairs"], 1)
            self.assertIsNone(result["joinedScanGroups"])
        finally:
            empty.close()

    def test_wrong_secret_and_tampered_immutability_rejected(self):
        self.prove()
        self.record()
        wrong = join.audit(
            self.main, self.private, as_of=iso(NOW+timedelta(seconds=5)),
            secret=b"another-incorrect-private-testing-key")
        self.assertEqual(wrong["joinedScanGroups"][
            "UNKNOWN_DIFFERENT_PRICE_SOURCE"], 1)
        with self.assertRaisesRegex(ValueError, "stable_private_hmac"):
            join.audit(self.main, self.private, as_of=iso(NOW), secret=b"short")
        self.private.execute("DROP TRIGGER research_cvd_scan_no_delete")
        self.private.commit()
        with self.assertRaisesRegex(ValueError,
                                    "cvd_attempt_immutability_triggers_missing"):
            self.audit()

    def test_readonly_on_existing_transactions_preserves_caller_snapshot(self):
        self.prove()
        self.record()
        self.main.execute("BEGIN")
        self.private.execute("BEGIN")
        try:
            result = self.audit()
            self.assertEqual(result["validOriginalCotPricePairs"], 1)
            self.assertTrue(self.main.in_transaction)
            self.assertTrue(self.private.in_transaction)
        finally:
            self.main.rollback()
            self.private.rollback()


if __name__ == "__main__":
    unittest.main()
