"""Track C C2c-c: original CFTC collector transaction + pinned B witness.

All data, price/volumes, report rows and clock samples are SYNTHETIC.
Temporary SQLite only; no provider API, Oracle, live collector or backfill.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
B_ROOT = ROOT / "track-b-pinned"
if not (B_ROOT / "scripts/shark_cot_asof_witness.py").is_file():
    raise RuntimeError("pinned_original_b_checkout_required")
sys.path.insert(0, str(B_ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(B_ROOT))

import cot_monitor as collector  # C's default-off modified original collector
from price_store import connect
from scripts import track_c_cot_atomic_b_witness as bridge
from scripts import shark_cot_asof_witness as witness

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)
PRIOR = "2026-10-27"
CURRENT = "2026-11-03"
CLOCKS = [NOW+dt.timedelta(seconds=i) for i in (1,3,5,6,8,10)]


def synthetic(dataset):
    config = collector.DATASETS[dataset]
    return [
        {"report_date_as_yyyy_mm_dd": day+"T00:00:00",
         "cftc_contract_market_code": code,
         "open_interest_all": "1000",
         **{key: str(101 if day == PRIOR else 121)
            for key in config["keys"]}}
        for day in (PRIOR,CURRENT) for code in config["codes"]
    ]


class C2cTrueAtomicOriginalWitnessTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="track-c-atomic-")
        self.path = Path(self.temp.name) / bridge.FILE_NAME
        db = connect(self.path)
        collector.ensure_table(db)
        witness.ensure_schema(db)
        db.close()
        self.requests=[]

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self,dataset,as_of):
        self.requests.append(dataset)
        self.assertEqual(as_of,NOW)
        return synthetic(dataset)

    def run_collector(self, **opts):
        settings={
            "db_path":self.path,
            "now":NOW,
            "fetch":self.fetch,
            "research_atomic_witness":bridge.OriginalBAtomicWitness(mode=bridge.MODE),
        }
        settings.update(opts)
        return collector.collect_once(**settings)

    def count(self, table, where="", args=()):
        db=connect(self.path)
        try:
            return db.execute(f"SELECT count(*) FROM {table} {where}",args).fetchone()[0]
        finally:
            db.close()

    def test_real_original_b_witness_committed_with_original_source(self):
        with patch.object(collector,"utcnow",side_effect=CLOCKS) as clock:
            out=self.run_collector()
        self.assertEqual(out["errors"],{})
        self.assertEqual(out["saved"],{"tff":22,"disagg":6})
        self.assertEqual(self.requests,["tff","disagg"])
        self.assertEqual(clock.call_count,6)
        self.assertEqual(self.count("cot_reports"),28)
        self.assertEqual(self.count(witness.TABLE),28)
        self.assertEqual(self.count("cot_first_seen"),28)
        db=connect(self.path)
        try:
            for kind, expected in (("tff",CLOCKS[2]),("disagg",CLOCKS[5])):
                seen=db.execute(
                    f"SELECT DISTINCT witnessed_at FROM {witness.TABLE} "
                    "WHERE dataset=?", (kind,)).fetchall()
                self.assertEqual(len(seen),1)
                self.assertEqual(witness._parse(seen[0][0]),expected)
            # It was NOT available to an original decision prior to witness.
            before=witness.readiness(db,as_of=(NOW+dt.timedelta(seconds=2)).isoformat())
            after=witness.readiness(db,as_of=(NOW+dt.timedelta(seconds=11)).isoformat())
            self.assertEqual(before["marketsWithTwoWeeksAttested"],0)
            self.assertGreaterEqual(after["marketsWithTwoWeeksAttested"],2)
            self.assertEqual(db.execute(
                "SELECT DISTINCT first_seen_at FROM cot_first_seen").fetchall(),
                [(NOW.isoformat(),)])
        finally:
            db.close()

    def test_off_mode_no_science_or_extra_calls(self):
        with patch.object(collector,"utcnow",
                          side_effect=AssertionError("default_do_not_sample_utcnow")):
            out=self.run_collector(research_atomic_witness=None)
        self.assertEqual(out["errors"],{})
        self.assertEqual(self.requests,["tff","disagg"])
        self.assertEqual(self.count("cot_reports"),28)
        self.assertEqual(self.count(witness.TABLE),0)

    def test_missing_explicit_b_migration_fails_both_datasets(self):
        db=connect(self.path)
        with db:
            db.execute(f"DROP TABLE {witness.TABLE}")
        db.close()
        with patch.object(collector,"utcnow",side_effect=CLOCKS):
            out=self.run_collector()
        self.assertEqual(out["errors"],{"tff":"unavailable","disagg":"unavailable"})
        self.assertEqual(self.count("cot_reports"),0)
        self.assertEqual(self.count("cot_first_seen"),0)

    def test_b_failure_on_second_dataset_rolls_back_only_second_source(self):
        db=connect(self.path)
        with db:
            db.execute(f"""CREATE TRIGGER block_synthetic_disagg_before_witness
                BEFORE INSERT ON {witness.TABLE}
                WHEN NEW.dataset='disagg'
                BEGIN SELECT RAISE(ABORT,'synthetic_research_witness_failure'); END""")
        db.close()
        with patch.object(collector,"utcnow",side_effect=CLOCKS):
            out=self.run_collector()
        self.assertEqual(out["errors"],{"disagg":"unavailable"})
        self.assertEqual(out["saved"],{"tff":22})
        self.assertEqual(self.count("cot_reports"),22)
        self.assertEqual(self.count(witness.TABLE),22)
        self.assertEqual(self.count("cot_first_seen"),22)
        self.assertEqual(self.count("cot_reports","WHERE dataset='disagg'"),0)

    def test_changed_sqlite_after_upsert_rolls_back_source_and_proof(self):
        db=connect(self.path)
        with db:
            db.execute("""CREATE TRIGGER synthetic_corrupt_original AFTER INSERT
                ON cot_reports WHEN NEW.dataset='tff'
                BEGIN UPDATE cot_reports SET first_long=first_long+1
                      WHERE dataset=NEW.dataset AND code=NEW.code
                      AND report_date=NEW.report_date; END""")
        db.close()
        with patch.object(collector,"utcnow",side_effect=CLOCKS):
            out=self.run_collector()
        self.assertEqual(out["errors"],{"tff":"unavailable"})
        self.assertEqual(out["saved"],{"disagg":6})
        self.assertEqual(self.count("cot_reports","WHERE dataset='tff'"),0)
        self.assertEqual(self.count(witness.TABLE,"WHERE dataset='tff'"),0)

    def test_future_local_attestation_blocks_tff_transaction(self):
        clocks=[CLOCKS[0],CLOCKS[1],NOW+dt.timedelta(seconds=60),*CLOCKS[3:]]
        with patch.object(collector,"utcnow",side_effect=clocks):
            out=self.run_collector()
        self.assertEqual(out["errors"],{"tff":"unavailable"})
        self.assertEqual(self.count("cot_reports","WHERE dataset='tff'"),0)
        self.assertEqual(self.count(witness.TABLE,"WHERE dataset='tff'"),0)

    def test_revised_value_after_original_proof_cannot_requalify_asof(self):
        with patch.object(collector,"utcnow",side_effect=CLOCKS):
            self.run_collector()
        db=connect(self.path)
        try:
            with db:
                db.execute(
                    "UPDATE cot_reports SET first_long=999 "
                    "WHERE dataset='tff' AND code='099741' AND report_date=?",
                    (CURRENT,))
            review=witness.readiness(
                db,as_of=(NOW+dt.timedelta(seconds=11)).isoformat())
            self.assertGreater(
                review["blockerCounts"]["source_values_not_yet_witnessed"],0)
            self.assertEqual(self.count(witness.TABLE),28)
        finally:db.close()

    def test_explicit_offline_only_never_call_from_live_file(self):
        with self.assertRaisesRegex(ValueError,"explicit_offline_rehearsal_mode"):
            bridge.OriginalBAtomicWitness()
        db=sqlite3.connect(":memory:")
        try:
            with db:
                db.execute("CREATE TABLE placeholder(n INTEGER)")
                db.execute("INSERT INTO placeholder VALUES (1)")
                with self.assertRaisesRegex(ValueError,
                          "only_synthetic_temporary_sqlite"):
                    bridge.OriginalBAtomicWitness(mode=bridge.MODE)(
                        db,"tff",*CLOCKS[:3],(("tff","099741",CURRENT,1000.,1.,1.,1.,1.),))
        finally:db.close()


if __name__=="__main__":
    unittest.main()
