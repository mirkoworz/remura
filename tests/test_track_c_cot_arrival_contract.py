"""Track C C2c: original pinned B CFTC normalizer + post-response witness.

All reports and timestamps are synthetic. No real provider, broker, VPS,
positions, quotes, secrets, file-based databases or HTTP.
"""
from __future__ import annotations

import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
B_ROOT = ROOT / "track-b-pinned"
if not (B_ROOT / "scripts/shark_cot_asof_witness.py").is_file():
    raise RuntimeError("original_B_checkout_required_for_track_c_cot_contract")
sys.path.insert(0, str(B_ROOT / "scripts"))
sys.path.insert(0, str(B_ROOT))
from scripts import track_c_cot_arrival_contract as arrival
from scripts import cot_monitor
from scripts import shark_cot_asof_witness as witness

UTC = timezone.utc
BASE = datetime(2026, 11, 9, 12, tzinfo=UTC)
LATEST = "2026-11-03"
PRIOR = "2026-10-27"


def sample():
    events = []
    for i, (dataset, code) in enumerate((
            ("tff", "099741"), ("disagg", "088691"))):
        cfg = cot_monitor.DATASETS[dataset]
        records = []
        for week in (PRIOR, LATEST):
            record = {
                "report_date_as_yyyy_mm_dd": week,
                "cftc_contract_market_code": code,
                "open_interest_all": 1000,
            }
            record.update({name: 100 if week == PRIOR else 120
                           for name in cfg["keys"]})
            records.append(record)
        events.append({
            "dataset": dataset,
            "request_started_at": BASE + timedelta(seconds=4*i),
            "response_received_at": BASE + timedelta(seconds=4*i+3),
            "records": records,
        })
    return events


class C2cOriginalBPostResponseTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        cot_monitor.ensure_table(self.db)
        witness.ensure_schema(self.db)

    def tearDown(self):
        self.db.close()

    def invoke(self, events=None, **values):
        opts = {
            "arrivals": sample() if events is None else events,
            "write_at": BASE + timedelta(seconds=12),
            "decision_at": BASE + timedelta(seconds=20),
            "mode": arrival.MODE,
        }
        opts.update(values)
        return arrival.rehearse(self.db, **opts)

    def count(self, table):
        return self.db.execute(f"SELECT count(*) FROM {table}").fetchone()[0]

    def test_real_b_normalizer_and_witness_after_response(self):
        out = self.invoke()
        self.assertEqual(out["researchValueWitnesses"], 4)
        self.assertEqual(self.count("cot_reports"), 4)
        self.assertEqual(self.count(witness.TABLE), 4)
        self.assertEqual(self.count("cot_first_seen"), 0)
        self.assertFalse(out["realProviderReceiptAuthenticated"])
        self.assertFalse(out["realMarketObservations"])
        self.assertFalse(out["liveCollectorWired"])
        self.assertFalse(out["tradingEdgeEstablished"])
        self.assertEqual(out["newExternalAPICalls"], 0)
        proof_times = self.db.execute(
            f"SELECT DISTINCT witnessed_at FROM {witness.TABLE}").fetchall()
        self.assertEqual(len(proof_times), 1)
        self.assertEqual(witness._parse(proof_times[0][0]),
                         BASE + timedelta(seconds=12))
        before = witness.readiness(
            self.db, as_of=(BASE + timedelta(seconds=11)).isoformat())
        self.assertEqual(before["marketsWithTwoWeeksAttested"], 0)
        after = witness.readiness(
            self.db, as_of=(BASE + timedelta(seconds=20)).isoformat())
        self.assertGreaterEqual(after["marketsWithTwoWeeksAttested"], 2)
        public = json.dumps(out)
        for secret in (LATEST, PRIOR, "1000", "099741", "088691"):
            self.assertNotIn(secret, public)

    def test_pre_request_legacy_stamp_not_backfilled(self):
        self.db.execute(
            "INSERT INTO cot_first_seen VALUES (?,?,?,?)",
            ("tff", "099741", PRIOR, (BASE-timedelta(seconds=10)).isoformat()))
        self.db.commit()
        self.invoke()
        self.assertEqual(self.count("cot_first_seen"), 1)
        self.assertEqual(witness._parse(
            self.db.execute("SELECT first_seen_at FROM cot_first_seen").fetchone()[0]),
            BASE-timedelta(seconds=10))
        self.assertEqual(self.count(witness.TABLE), 4)

    def test_future_or_before_request_clocks_rejected(self):
        for typ, bad in (
                ("start", BASE+timedelta(seconds=4)),
                ("receive", BASE+timedelta(seconds=80)),
                ("postwrite", BASE+timedelta(seconds=6))):
            data = sample()
            if typ == "start":
                data[0]["request_started_at"] = bad
            elif typ == "receive":
                data[0]["response_received_at"] = bad
            else:
                data[1]["response_received_at"] = BASE + timedelta(seconds=14)
            with self.assertRaisesRegex(ValueError,
                                        "post_response_receive_clock"):
                self.invoke(events=data)
        self.assertEqual(self.count("cot_reports"), 0)

    def test_future_data_cannot_validate_earlier_decision(self):
        with self.assertRaisesRegex(ValueError,
                                    "noncausal_persistence_decision_clock"):
            self.invoke(decision_at=BASE + timedelta(seconds=10))
        with self.assertRaisesRegex(ValueError,
                                    "noncausal_persistence_decision_clock"):
            self.invoke(write_at=BASE + timedelta(minutes=7))
        self.assertEqual(self.count("cot_reports"), 0)

    def test_old_or_naive_clock_not_accepted(self):
        events = sample()
        events[0]["request_started_at"] = (
            datetime(2026,11,9,12,0))
        with self.assertRaisesRegex(ValueError, "explicit_utc_runtime_clock"):
            self.invoke(events=events)
        with self.assertRaisesRegex(ValueError,
                                    "explicit_utc_runtime_clock"):
            self.invoke(write_at=datetime(2026,11,9,12,0))
        self.assertEqual(self.count("cot_reports"), 0)

    def test_missing_response_or_wrong_contract_rejected(self):
        with self.assertRaisesRegex(ValueError, "exact_two_original"):
            self.invoke(events=sample()[:1])
        data = sample()
        data[0]["records"][0]["cftc_contract_market_code"] = "096742"
        with self.assertRaisesRegex(ValueError,
                                    "exact_pilot_contract_two_weeks"):
            self.invoke(events=data)
        data = sample()
        data[1]["dataset"] = "tff"
        with self.assertRaisesRegex(ValueError,
                                    "unexpected_cot_dataset_order"):
            self.invoke(events=data)
        self.assertEqual(self.count("cot_reports"), 0)

    def test_missing_week_and_week_misalignment(self):
        data = sample()
        del data[0]["records"][0]
        with self.assertRaisesRegex(ValueError,
                                    "exact_pilot_contract_two_weeks"):
            self.invoke(events=data)
        data = sample()
        data[1]["records"][0]["report_date_as_yyyy_mm_dd"] = "2026-10-20"
        with self.assertRaises(ValueError):
            self.invoke(events=data)
        self.assertEqual(self.count("cot_reports"), 0)

    def test_second_contract_insert_failure_rolls_back(self):
        self.db.execute("""CREATE TRIGGER reject_gold_cot BEFORE INSERT
            ON cot_reports WHEN NEW.dataset='disagg'
            BEGIN SELECT RAISE(ABORT,'synthetic_second_contract_failure'); END""")
        self.db.commit()
        with self.assertRaisesRegex(sqlite3.IntegrityError,
                                     "synthetic_second_contract_failure"):
            self.invoke()
        self.assertEqual(self.count("cot_reports"), 0)
        self.assertEqual(self.count(witness.TABLE), 0)
        self.assertFalse(self.db.in_transaction)

    def test_no_backfill_or_replay_and_no_empty_schema_autocreate(self):
        self.invoke()
        with self.assertRaisesRegex(ValueError, "synthetic_cot_database_must_be_empty"):
            self.invoke()
        self.db.execute(f"DROP TABLE {witness.TABLE}")
        self.db.commit()
        with self.assertRaisesRegex(ValueError, "explicit_pinned_b_research_schema"):
            self.invoke()

    def test_original_cot_revision_after_receipt_is_unknown(self):
        self.invoke()
        self.db.execute(
            "UPDATE cot_reports SET first_long=123 WHERE dataset='tff' "
            "AND code='099741' AND report_date=?", (LATEST,))
        self.db.commit()
        report = witness.readiness(
            self.db, as_of=(BASE + timedelta(seconds=20)).isoformat())
        self.assertGreater(
            report["blockerCounts"]["source_values_not_yet_witnessed"], 0)
        self.assertEqual(self.count(witness.TABLE), 4)

    def test_fail_closed_disk_and_unknown_mode(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline_synthetic_mode"):
            self.invoke(mode=None)
        with tempfile.TemporaryDirectory() as directory:
            disk=sqlite3.connect(str(Path(directory) / "vps-mimic.sqlite"))
            try:
                with self.assertRaisesRegex(ValueError,"live_or_attached_sqlite"):
                    arrival.rehearse(
                        disk,arrivals=sample(),write_at=BASE+timedelta(seconds=12),
                        decision_at=BASE+timedelta(seconds=20),mode=arrival.MODE)
            finally:
                disk.close()
        self.assertEqual(self.count("cot_reports"),0)


if __name__ == "__main__":
    unittest.main()
