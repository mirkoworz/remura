# REMURA Retail v0.6 — ONLY new receipt lifecycle / custody cases.
import copy
import unittest
from provenance_receipt_ledger_v06_lab import (
    ReceiptError, start, append, audit, assess_at_decision,
)

T0 = "2026-11-23T01:01:00Z"
T1 = "2026-11-23T01:02:00Z"
T2 = "2026-11-23T01:03:00Z"
T3 = "2026-11-23T01:04:00Z"
SHA = "a" * 64
COMMIT = "b" * 40

def event(key, kind, authority, *, happened=T0, recorded=T1):
    return {"event_id": key, "kind": kind, "authority": authority,
            "event_at_utc": happened, "recorded_at_utc": recorded,
            "reference": "offline-fixture-v06", "response_sha256": SHA}

def ledger():
    return start(content_commit=COMMIT, content_sha256=SHA)

class ReceiptLedgerTests(unittest.TestCase):
    def test_01_empty_future_ledger_remains_unknown(self):
        state = assess_at_decision(ledger(), T2)
        self.assertEqual(state["independent_first_seen"], "UNKNOWN")
        self.assertEqual(state["provider_publication_time"], "UNKNOWN")
        self.assertEqual(state["public_page_availability"], "UNKNOWN")

    def test_02_append_is_nonmutating(self):
        first = ledger()
        second = append(first, event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"))
        self.assertEqual(first["events"], [])
        self.assertEqual(audit(second)["records"], 1)

    def test_03_hash_chain_continuity(self):
        a = append(ledger(), event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"))
        b = append(a, event("snapshot-1", "SNAPSHOT_WRITTEN", "LOCAL_COLLECTOR"))
        self.assertEqual(b["events"][1]["prev_sha256"], a["head_sha256"])
        self.assertEqual(audit(b)["head_sha256"], b["head_sha256"])

    def test_04_tampered_observation_detected(self):
        x = append(ledger(), event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"))
        changed = copy.deepcopy(x)
        changed["events"][0]["event"]["event_at_utc"] = T2
        with self.assertRaisesRegex(ReceiptError, "record_hash_mismatch"):
            audit(changed)

    def test_05_tampered_head_detected(self):
        x = append(ledger(), event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"))
        changed = {**x, "head_sha256": SHA}
        with self.assertRaisesRegex(ReceiptError, "ledger_head_mismatch"):
            audit(changed)

    def test_06_duplicate_event_rejected(self):
        a = append(ledger(), event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"))
        with self.assertRaisesRegex(ReceiptError, "duplicate_event_id"):
            append(a, event("collector-1", "SNAPSHOT_WRITTEN", "LOCAL_COLLECTOR"))

    def test_07_recorded_clock_reordering_rejected(self):
        a = append(ledger(), event("collector-1", "COLLECTOR_API_RETURN", "LOCAL_COLLECTOR",
                                   recorded=T2))
        with self.assertRaisesRegex(ReceiptError, "retroactive_recording_order"):
            append(a, event("snapshot-1", "SNAPSHOT_WRITTEN", "LOCAL_COLLECTOR",
                            recorded=T1))

    def test_08_reported_github_event_cannot_be_claimed_independent(self):
        with self.assertRaisesRegex(ReceiptError, "event_authority_mismatch"):
            append(ledger(), event("run-1", "GITHUB_ACTIONS_EVENT", "WITNESS_REPORTED"))

    def test_09_noncanonical_offset_and_impossible_date_rejected(self):
        for invalid in ("2026-11-23T02:02:00+01:00", "2026-02-30T01:02:00Z"):
            with self.subTest(invalid=invalid), self.assertRaises(ReceiptError):
                append(ledger(), event("bad", "SNAPSHOT_WRITTEN", "LOCAL_COLLECTOR",
                                       happened=invalid))

    def test_10_no_arbitrary_fields_even_verification_boolean(self):
        x = event("witness-1", "INDEPENDENT_RECEIPT", "WITNESS_REPORTED")
        x["is_verified"] = True
        with self.assertRaisesRegex(ReceiptError, "event_schema_invalid"):
            append(ledger(), x)

    def test_11_witness_claim_does_not_promote_independent_receipt(self):
        x = append(ledger(), event("witness-1", "INDEPENDENT_RECEIPT", "WITNESS_REPORTED"))
        state = assess_at_decision(x, T2)
        self.assertEqual(state["independent_first_seen"], "CLAIM_ONLY_UNATTESTED")
        self.assertFalse(state["cryptographic_attestation_verified"])
        self.assertEqual(state["status"], "NO_GO_SCIENTIFIC_ADMISSION")

    def test_12_future_witness_and_recorded_late_flagged(self):
        x = append(ledger(), event("witness-1", "INDEPENDENT_RECEIPT", "WITNESS_REPORTED",
                                   happened=T2, recorded=T3))
        out = assess_at_decision(x, T1)
        self.assertEqual(out["post_decision_witness_claim_ids"], ["witness-1"])
        self.assertIn("WITNESS_CLAIM_AFTER_DECISION", out["blocking_reasons"])

    def test_13_venue_publication_and_pages_are_distinct(self):
        x = append(ledger(), event("pages-1", "PAGES_DEPLOYMENT_COMPLETED", "GITHUB_REPORTED"))
        state = assess_at_decision(x, T2)
        self.assertEqual(state["public_page_availability"], "GITHUB_REPORTED_UNATTESTED")
        self.assertEqual(state["provider_publication_time"], "UNKNOWN")

    def test_14_all_claimed_sources_still_no_go_without_signature(self):
        x = ledger()
        for idx, (kind, auth) in enumerate((
            ("COLLECTOR_API_RETURN", "LOCAL_COLLECTOR"),
            ("GIT_CONTENT_COMMIT", "GIT_CONTENT"),
            ("PROVIDER_PUBLICATION", "PROVIDER_REPORTED"),
            ("INDEPENDENT_RECEIPT", "WITNESS_REPORTED"),
        )):
            x = append(x, event("source-" + str(idx), kind, auth))
        out = assess_at_decision(x, T2)
        self.assertFalse(out["decision_admission_allowed"])
        self.assertIn("RECEIPT_AUTHENTICITY_NOT_VERIFIED_OFFLINE", out["blocking_reasons"])
        self.assertFalse(audit(x)["hash_chain_externally_pinned"])

if __name__ == "__main__":
    unittest.main()
