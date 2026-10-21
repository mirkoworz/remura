"""Offline tests: progressive cTrader backfill never trades or bulk-loads blindly."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import ctrader_backfill as backfill


class BackfillTests(unittest.TestCase):
    def test_only_enabled_missing_markets_selected_in_small_batch(self):
        discovered = {"EURUSD": "EURUSD", "GBPJPY": "GBPJPY",
                      "XAUUSD": "XAUUSD", "USDJPY": "USDJPY",
                      "INVALID": "INVALID", "NZDJPY": "NZDJPY"}
        self.assertEqual(backfill.next_batch(discovered, ["EURUSD", "XAUUSD"], 2),
                         ["GBPJPY", "NZDJPY"])
        self.assertEqual(backfill.next_batch(discovered, ["EURUSD", "XAUUSD"], 3),
                         ["GBPJPY", "NZDJPY", "USDJPY"])
        with self.assertRaises(ValueError):
            backfill.next_batch(discovered, [], 4)

    def test_preview_cannot_write_prices(self):
        plan = dict(available=31, existing=5, waiting=26,
                    next=["AUDCAD", "AUDCHF", "AUDJPY"], unmatched=["DXY"])
        with patch.object(backfill, "load_plan", return_value=plan), \
             patch.object(backfill, "collect_once") as collect:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                result = backfill.main([])
            self.assertEqual(result, 0)
            collect.assert_not_called()
            self.assertIn("ANTEPRIMA", out.getvalue())
            self.assertIn("ANCORA DA CARICARE: 26", out.getvalue())

    def test_apply_runs_exactly_one_bounded_batch(self):
        plan = dict(available=31, existing=5, waiting=26,
                    next=["AUDCAD", "AUDCHF", "AUDJPY"], unmatched=["DXY"])
        report = {"saved": {"AUDCAD": 1300, "AUDCHF": 1300, "AUDJPY": 1300}, "errors": {}}
        with patch.object(backfill, "load_plan", return_value=plan), \
             patch.object(backfill, "collect_once", return_value=report) as collect:
            with contextlib.redirect_stdout(io.StringIO()):
                result = backfill.main(["--apply", "--days", "21"])
            self.assertEqual(result, 0)
            collect.assert_called_once_with(
                backfill.DEFAULT_DB, plan["next"], days=21
            )

    def test_partial_batch_fails_safely(self):
        plan = dict(available=31, existing=5, waiting=26,
                    next=["AUDCAD", "AUDCHF"], unmatched=[])
        with patch.object(backfill, "load_plan", return_value=plan), \
             patch.object(backfill, "collect_once", return_value={
                 "saved": {"AUDCAD": 1300}, "errors": {}
             }):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(backfill.main(["--apply"]), 1)

    def test_no_markets_to_load_does_not_collect(self):
        plan = dict(available=31, existing=31, waiting=0,
                    next=[], unmatched=["NAS100"])
        with patch.object(backfill, "load_plan", return_value=plan), \
             patch.object(backfill, "collect_once") as collect:
            with contextlib.redirect_stdout(io.StringIO()):
                result = backfill.main(["--apply"])
            self.assertEqual(result, 0)
            collect.assert_not_called()

    def test_auto_loads_two_batches_and_waits_between_them(self):
        pending=["AUDCAD", "AUDCHF", "AUDJPY", "AUDNZD"]
        plan=dict(available=31, existing=5, waiting=len(pending),
                  remaining=pending, next=pending[:3], unmatched=[])
        pause=[]
        def fake_collect(db_path, symbols, days):
            return {"saved": {s: 1300 for s in symbols}, "errors": {}}
        with patch.object(backfill, "load_plan", return_value=plan) as discovery, \
             patch.object(backfill, "collect_once", side_effect=fake_collect) as collect, \
             contextlib.redirect_stdout(io.StringIO()):
            result=backfill.run_all_missing(backfill.DEFAULT_DB, 21, 3, 60, sleeper=pause.append)
        self.assertEqual(result, 0)
        self.assertEqual(collect.call_count, 2)
        self.assertEqual(collect.call_args_list[0].args[1], pending[:3])
        self.assertEqual(collect.call_args_list[1].args[1], pending[3:])
        self.assertEqual(discovery.call_count, 1)  # Twisted reactor starts only once.
        self.assertEqual(pause, [60])

    def test_auto_stops_after_first_incomplete_batch(self):
        plan=dict(available=31, existing=5, waiting=26,
                  remaining=["AUDCAD","AUDCHF"], next=["AUDCAD","AUDCHF"], unmatched=[])
        with patch.object(backfill, "load_plan", return_value=plan) as discovery, \
             patch.object(backfill, "collect_once", return_value={
                 "saved": {"AUDCAD":1300}, "errors": {"AUDCHF":"unavailable"}
             }) as collect, contextlib.redirect_stdout(io.StringIO()):
            result=backfill.run_all_missing(backfill.DEFAULT_DB,21,3,60,sleeper=lambda x: None)
        self.assertEqual(result,1)
        discovery.assert_called_once()
        collect.assert_called_once()

    def test_auto_requires_apply_and_safe_pause_limits(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                backfill.main(["--all-missing"])
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                backfill.main(["--apply","--all-missing","--pause-seconds","3"])

    def test_private_aliases_are_validated(self):
        with tempfile.TemporaryDirectory() as directory:
            db = Path(directory) / "prices.sqlite3"
            aliases = Path(directory) / "ctrader-symbols.json"
            self.assertEqual(backfill.private_aliases(db), {})
            aliases.write_text('{"US500":"US500.cash"}', encoding="utf-8")
            self.assertEqual(backfill.private_aliases(db), {"US500": "US500.cash"})
            aliases.write_text('{"CTRADER_CLIENT_SECRET":"DONT_PRINT"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                backfill.private_aliases(db)


if __name__ == "__main__":
    unittest.main()
