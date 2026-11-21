# REMURA TradingView v0.8.182 LAB — only NEW calendar tests
import sys
from pathlib import Path
import unittest
from datetime import datetime, timedelta, timezone
from tempfile import TemporaryDirectory
sys.path.insert(0,str(Path(__file__).resolve().parent))
import holdout_freeze_v0182_lab as m

class NewFreezeTests(unittest.TestCase):
    def test_01_exact_protocol_git_blob(self):
        self.assertEqual(m.git_blob_hash(m.PROTOCOL.read_bytes()),m.PINNED_PROTOCOL_GIT_BLOB)
    def test_02_calendar_good(self):
        x=m.guard()
        self.assertEqual(x["version"],"0.8.182")
        self.assertTrue(x["interval_end_exclusive"])
        self.assertFalse(x["captures_active"])
        self.assertFalse(x["institutional_edge_established"])
    def test_03_dev_start_inclusive(self):
        self.assertEqual(m.phase(m.DEV_START),"DEVELOPMENT_FROZEN")
    def test_04_dev_before_start(self):
        self.assertEqual(m.phase(m.DEV_START-timedelta(seconds=1)),"OUTSIDE_RESERVED_WINDOWS")
    def test_05_h1_start_inclusive(self):
        self.assertEqual(m.phase(m.H1_START),"HOLDOUT_1")
    def test_06_dev_end_exclusive(self):
        self.assertEqual(m.phase(m.H1_START-timedelta(microseconds=1)),"DEVELOPMENT_FROZEN")
    def test_07_h2_start_inclusive(self):
        self.assertEqual(m.phase(m.H2_START),"HOLDOUT_2")
    def test_08_h1_end_exclusive(self):
        self.assertEqual(m.phase(m.H2_START-timedelta(microseconds=1)),"HOLDOUT_1")
    def test_09_h2_end_exclusive(self):
        self.assertEqual(m.phase(m.H2_END),"OUTSIDE_RESERVED_WINDOWS")
    def test_10_h2_last_inclusive(self):
        self.assertEqual(m.phase(m.H2_END-timedelta(microseconds=1)),"HOLDOUT_2")
    def test_11_naive_datetime_denied(self):
        with self.assertRaises(m.FreezeError):
            m.phase(datetime(2026,11,23))
    def test_12_non_utc_offset_denied(self):
        with self.assertRaises(m.FreezeError):
            m.phase(datetime(2026,11,23,tzinfo=timezone(timedelta(hours=1))))
    def test_13_missing_protocol_denied(self):
        with TemporaryDirectory() as p:
            with self.assertRaises(m.FreezeError):
                m.guard(Path(p)/"missing.md")
    def test_14_protocol_change_denied(self):
        with TemporaryDirectory() as p:
            f=Path(p)/"protocol.md"
            f.write_bytes(m.PROTOCOL.read_bytes()+b"\nrevised")
            with self.assertRaises(m.FreezeError):
                m.guard(f)
    def test_15_symlink_denied(self):
        with TemporaryDirectory() as p:
            f=Path(p)/"linked.md";f.symlink_to(m.PROTOCOL)
            with self.assertRaises(m.FreezeError):
                m.guard(f)
    def test_16_no_market_data_outputs(self):
        x=str(m.guard()).lower()
        self.assertNotIn("profit",x)
        self.assertNotIn("pnl",x)
        self.assertNotIn("token",x)
        self.assertNotIn("email",x)
    def test_17_bad_args(self):
        self.assertEqual(m.main([]),2)
    def test_18_good_args(self):
        self.assertEqual(m.main(["--check"]),0)

if __name__=="__main__":
    unittest.main()
