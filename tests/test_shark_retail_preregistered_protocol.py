"""Frozen prospective retail protocol: synthetic scheduling and adversarial splits."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import copy
import unittest
from unittest.mock import patch

from scripts import shark_retail_preregistered_protocol as p

UTC = timezone.utc
APPROVAL = datetime(2026, 11, 2, tzinfo=UTC)
ASOF = datetime(2027, 8, 1, tzinfo=UTC)
START = datetime(2026, 11, 9, tzinfo=UTC)


def observation(ident=1, *, observed=None, evaluated=None, week=None,
                receipt=None, retail_state="COMPLETE_RETAIL_AT_FIRST_SEEN"):
    observed = observed or START + timedelta(days=2)
    week = week or (observed - timedelta(days=observed.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0)
    return {
        "event_id": ident, "symbol": "EURUSD",
        "observed_at": observed,
        "evaluated_at": evaluated if evaluated is not None
            else observed + timedelta(hours=4),
        "source_recorded_at": observed - timedelta(minutes=15),
        "source_linked_at": observed + timedelta(seconds=2),
        "cot_week_monday": week,
        "cot_current_receipts": [receipt or f"{ident:064x}"],
        "retail_state": retail_state,
    }


class FrozenRetailProtocolTests(unittest.TestCase):
    def run_audit(self, rows, *, as_of=ASOF, approval=APPROVAL):
        return p.audit_synthetic_metadata(rows, authorized_at=approval, as_of=as_of)

    def test_immutable_policy_and_separate_from_cvd(self):
        self.assertEqual(
            p.fingerprint(),
            "6c4413a9851233e0785cb86eb30a03a22e8fa0a20efd4385c22638cba2ba4f6e")
        self.assertEqual(p.fingerprint(), p.FROZEN_RULES_SHA256)
        from scripts import shark_cvd_incremental_protocol as cvd
        self.assertEqual(cvd.protocol_sha256(), cvd.FROZEN_PROTOCOL_SHA256)
        self.assertTrue(p.FROZEN_RULES["cvd_protocol_unchanged"])
        self.assertEqual(p.FROZEN_RULES["additional_retail_features"],
                         ["lPct", "sPct", "lLots", "sLots", "lPos", "sPos"])

    def test_no_approval_is_no_calendar_and_never_authorizes_live(self):
        b = self.run_audit([observation()], approval=None)
        self.assertEqual(b["status"], "BLOCKED_NO_AUTHORIZED_RETAIL_START")
        self.assertEqual(b["metadataRowsProcessed"], 0)
        self.assertFalse(b["releaseAuthorized"])
        self.assertNotIn("trainStartUtc", b)
        self.assertFalse(p.frozen_calendar(None)["liveEnabled"])

    def test_fixed_calendar_after_explicit_hypothetical_approval(self):
        d = p.frozen_calendar(APPROVAL)
        self.assertEqual(d["trainStartUtc"], "2026-11-09T00:00:00Z")
        self.assertEqual(d["validationStartUtc"], "2027-02-01T00:00:00Z")
        self.assertEqual(d["testStartUtc"], "2027-03-29T00:00:00Z")
        self.assertEqual(d["testEndUtc"], "2027-05-24T00:00:00Z")
        self.assertFalse(d["actualAuthorizationVerified"])
        self.assertFalse(d["testOutcomesUnblinded"])

    def test_monday_rule_does_not_start_before_full_7_days(self):
        late = APPROVAL + timedelta(hours=1)
        self.assertEqual(p.frozen_calendar(late)["trainStartUtc"],
                         "2026-11-16T00:00:00Z")

    def test_a_single_clean_original_decision_is_not_statistical_evidence(self):
        a = self.run_audit([observation()])
        self.assertEqual(a["folds"]["train"]["pairedCompleteMetadata"], 1)
        self.assertEqual(a["folds"]["train"]["distinctCotPublicationWeeksUpperBound"], 1)
        self.assertFalse(a["folds"]["train"]["minimumDesignCountsSatisfied"])
        self.assertEqual(a["independentSamplesProven"], 0)
        self.assertEqual(a["outcomeValuesRead"], 0)
        self.assertEqual(a["trainedModels"], 0)
        self.assertFalse(a["realEdgeEstablished"])
        self.assertNotIn("EURUSD", str(a))
        self.assertNotIn("COT_RETURN", str(a))

    def test_missing_and_partial_are_not_imputed_as_zero_or_negative(self):
        rows = [observation(1, retail_state="UNKNOWN_MISSING"),
                observation(2, retail_state="PARTIAL_OR_MISSING_AGGREGATES")]
        a = self.run_audit(rows)
        self.assertEqual(a["folds"]["train"]["denominatorOriginalDecisions"], 2)
        self.assertEqual(a["folds"]["train"]["pairedCompleteMetadata"], 0)
        self.assertEqual(a["exclusions"]["UNKNOWN_MISSING"], 1)
        self.assertEqual(a["exclusions"]["PARTIAL_OR_MISSING_AGGREGATES"], 1)

    def test_future_and_duplicate_events_cannot_inflate_counts(self):
        a = self.run_audit([observation(1), observation(1),
                            observation(3, observed=ASOF+timedelta(days=1))])
        self.assertEqual(a["folds"]["train"]["pairedCompleteMetadata"], 1)
        self.assertEqual(a["exclusions"]["REJECTED_DUPLICATE_OR_INVALID_EVENT"], 1)
        self.assertEqual(a["exclusions"]["UNKNOWN_FUTURE_OBSERVATION_ASOF"], 1)

    def test_receipt_and_original_link_clocks_reject_leakage(self):
        bad = observation()
        bad["source_recorded_at"] = bad["observed_at"]+timedelta(seconds=1)
        a = self.run_audit([bad])
        self.assertEqual(a["exclusions"]["REJECTED_RETAIL_TIMING"], 1)
        bad2 = observation()
        bad2["source_linked_at"] = bad2["observed_at"]+timedelta(minutes=20)
        self.assertEqual(self.run_audit([bad2])["exclusions"]["REJECTED_RETAIL_TIMING"], 1)

    def test_outcome_clock_only_for_purge_no_outcome_values(self):
        train_end = datetime(2027, 2, 1, tzinfo=UTC)
        row = observation(observed=train_end-timedelta(days=3),
                          evaluated=train_end-timedelta(hours=1))
        a = self.run_audit([row])
        self.assertEqual(a["exclusions"]["PURGED_OR_EMBARGOED_REAL_EVALUATION_TIME"], 1)
        self.assertEqual(a["outcomeValuesRead"], 0)
        with self.assertRaisesRegex(ValueError, "exact_non_sensitive_metadata_schema_required"):
            self.run_audit([dict(observation(), real_net_pnl=999999)])

    def test_unknown_future_outcome_maturity_is_not_zero_or_loss(self):
        row = observation(evaluated=datetime(2027, 1, 9, tzinfo=UTC))
        a = self.run_audit([row], as_of=datetime(2026, 12, 1, tzinfo=UTC))
        self.assertEqual(a["exclusions"]["UNKNOWN_OUTCOME_NOT_MATURE_ASOF"], 1)
        row["evaluated_at"] = None
        self.assertEqual(self.run_audit([row])["exclusions"]["UNKNOWN_EVALUATION_CLOCK"], 1)

    def test_embargo_and_cot_week_boundaries_fail_closed(self):
        valid_start = datetime(2027, 2, 1, tzinfo=UTC)
        row = observation(observed=valid_start+timedelta(hours=3))
        self.assertEqual(self.run_audit([row])["exclusions"]["EMBARGO_AFTER_BOUNDARY"], 1)
        row["observed_at"] = valid_start + timedelta(days=1)
        row["source_recorded_at"] = row["observed_at"]-timedelta(minutes=15)
        row["source_linked_at"] = row["observed_at"]+timedelta(seconds=2)
        row["cot_week_monday"] = valid_start - timedelta(days=7)
        self.assertEqual(
            self.run_audit([row])["exclusions"]["QUARANTINED_COT_WEEK_SPANS_FOLD"], 1)

    def test_shared_current_cot_release_between_folds_quarantines_both(self):
        a = observation(1, observed=datetime(2027, 1, 18, 12, tzinfo=UTC),
                        receipt="a"*64)
        b = observation(2, observed=datetime(2027, 2, 8, 12, tzinfo=UTC),
                        receipt="a"*64)
        out = self.run_audit([a, b])
        self.assertEqual(out["exclusions"]["QUARANTINED_COT_RELEASE_CROSS_FOLD"], 2)
        self.assertEqual(out["folds"]["train"]["pairedCompleteMetadata"], 0)
        self.assertEqual(out["folds"]["validation"]["pairedCompleteMetadata"], 0)

    def test_no_outcome_or_numeric_raw_row_and_no_model_calls(self):
        row = observation()
        for extra in ("lPct", "retail_json", "broker_account", "net_return",
                      "live_price", "result"):
            with self.assertRaisesRegex(ValueError, "exact_non_sensitive_metadata_schema_required"):
                self.run_audit([dict(row, **{extra: 1})])
        with patch.object(p, "FROZEN_RULES_SHA256", "f"*64):
            with self.assertRaisesRegex(ValueError, "retail_protocol_fingerprint_modified"):
                p.frozen_calendar(APPROVAL)


if __name__ == "__main__":
    unittest.main()
