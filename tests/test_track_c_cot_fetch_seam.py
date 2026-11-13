"""Track C: actual COT collector boundary clocks, synthetic fetch only.

The optional research callback is off by default. Test only the original
collector with a fake source; never call CFTC or touch the LIVE database.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import cot_monitor as cot
from price_store import connect

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 9, 12, 0, 0, tzinfo=UTC)


def rows(dataset):
    cfg = cot.DATASETS[dataset]
    result=[]
    for code in cfg["codes"]:
        result.append({
            "report_date_as_yyyy_mm_dd": "2026-11-03T00:00:00",
            "cftc_contract_market_code": code,
            "open_interest_all": "1000",
            **{key: "100" for key in cfg["keys"]},
        })
    return result


class CotTrueResponseSeamTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name) / "synthetic-cot.sqlite3"

    def tearDown(self):
        self.temp.cleanup()

    def fetch(self, ds, started_at):
        self.assertEqual(started_at, NOW)
        self.called.append(ds)
        return rows(ds)

    def test_two_original_response_clocks_after_fetch_and_no_extra_request(self):
        self.called=[]
        observed=[]
        clocks=[NOW+dt.timedelta(seconds=k) for k in (1,3,4,8)]
        def callback(ds,started,received,frozen):
            self.assertEqual(self.called[-1],ds)  # fetch already RETURNED
            self.assertIsInstance(frozen, tuple)
            self.assertTrue(all(isinstance(row,tuple) for row in frozen))
            self.assertTrue(all(len(row)==8 for row in frozen))
            # Attempt to mutate the research copy cannot poison the DB.
            with self.assertRaises(TypeError):
                frozen[0][3]=float("nan")
            observed.append((ds,started,received))
        with patch.object(cot,"utcnow",side_effect=clocks) as mocked:
            result=cot.collect_once(self.path,now=NOW,fetch=self.fetch,
                                   research_response_observer=callback)
        self.assertEqual(result["errors"],{})
        self.assertEqual(self.called,["tff","disagg"])
        self.assertEqual(mocked.call_count,4)
        self.assertEqual(observed,[
            ("tff",clocks[0],clocks[1]),
            ("disagg",clocks[2],clocks[3]),
        ])
        db=connect(self.path)
        try:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM cot_reports").fetchone()[0], 14)
            # The old legacy timestamp is still the BEFORE-fetch clock.
            stamp=db.execute(
                "SELECT DISTINCT first_seen_at FROM cot_first_seen").fetchall()
            self.assertEqual(stamp,[(NOW.isoformat(),)])
        finally:
            db.close()

    def test_default_mode_never_samples_new_clock_or_callback(self):
        self.called=[]
        with patch.object(cot,"utcnow",
                          side_effect=AssertionError("research clock used")):
            out=cot.collect_once(self.path,now=NOW,fetch=self.fetch)
        self.assertEqual(out["errors"],{})
        self.assertEqual(self.called,["tff","disagg"])

    def test_bad_hook_rejected_before_api_or_database(self):
        with self.assertRaisesRegex(ValueError,
                                    "explicit_callable_research_response"):
            cot.collect_once(self.path,now=NOW,fetch=lambda *_:None,
                             research_response_observer=True)
        self.assertFalse(self.path.exists())

    def test_observer_refusal_blocks_that_dataset_before_persistence(self):
        self.called=[]
        callbacks=[]
        def reject_tff(ds,start,end,rows_immutable):
            callbacks.append(ds)
            if ds=="tff":
                raise ValueError("research_no_go")
        clocks=[NOW+dt.timedelta(seconds=k) for k in (1,3,4,8)]
        with patch.object(cot,"utcnow",side_effect=clocks):
            out=cot.collect_once(self.path,now=NOW,fetch=self.fetch,
                                 research_response_observer=reject_tff)
        self.assertEqual(self.called,["tff","disagg"])
        self.assertEqual(callbacks,["tff","disagg"])
        self.assertEqual(out["errors"],{"tff":"unavailable"})
        self.assertEqual(out["saved"],{"disagg":3})
        db=connect(self.path)
        try:
            self.assertEqual(db.execute(
                "SELECT count(*) FROM cot_reports WHERE dataset='tff'").fetchone()[0],0)
        finally:db.close()

    def test_reversed_or_naive_runtime_clocks_fail_closed(self):
        for clocks in (
            [NOW+dt.timedelta(seconds=3),NOW+dt.timedelta(seconds=1),
             NOW+dt.timedelta(seconds=4),NOW+dt.timedelta(seconds=8)],
            [NOW.replace(tzinfo=None),NOW+dt.timedelta(seconds=2),
             NOW+dt.timedelta(seconds=4),NOW+dt.timedelta(seconds=8)],
        ):
            with self.subTest(clocks=clocks):
                self.called=[]
                callbacks=[]
                with patch.object(cot,"utcnow",side_effect=clocks):
                    out=cot.collect_once(
                        self.path,now=NOW,fetch=self.fetch,
                        research_response_observer=lambda *a: callbacks.append(a))
                self.assertEqual(out["errors"],{"tff":"unavailable"})
                self.assertEqual(callbacks[0][0],"disagg")
                db=connect(self.path)
                try:
                    self.assertEqual(db.execute(
                        "SELECT count(*) FROM cot_reports WHERE dataset='tff'").fetchone()[0],0)
                finally:db.close()


if __name__=="__main__":
    unittest.main()
