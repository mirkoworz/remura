"""Pure offline fixture tests for CFTC snapshot adapter; never touch a live DB."""
import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("cot_intel_snapshot",ROOT/"scripts"/"cot_intelligence_snapshot.py")
module=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(module)

class TestCotIntelligenceSnapshot(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"offline-copy.sqlite3"
        db=sqlite3.connect(self.path)
        db.executescript("""
        CREATE TABLE cot_reports (
          dataset TEXT NOT NULL,code TEXT NOT NULL,report_date TEXT NOT NULL,
          oi REAL NOT NULL,first_long REAL NOT NULL,first_short REAL NOT NULL,
          second_long REAL NOT NULL,second_short REAL NOT NULL,
          PRIMARY KEY(dataset,code,report_date));
        CREATE TABLE cot_first_seen (
          dataset TEXT NOT NULL,code TEXT NOT NULL,report_date TEXT NOT NULL,
          first_seen_at TEXT NOT NULL,
          PRIMARY KEY(dataset,code,report_date));
        """)
        db.executemany("INSERT INTO cot_reports VALUES (?,?,?,?,?,?,?,?)",[
            ("tff","090741","2026-11-17",1000,400,200,100,200),
            ("tff","097741","2026-11-17",1200,200,400,200,150),
            ("disagg","088691","2026-11-17",1400,700,100,300,600),
            ("tff","999999","2026-11-17",10,1,1,1,1)
        ])
        db.execute("INSERT INTO cot_first_seen VALUES (?,?,?,?)",(
            "tff","090741","2026-11-17","2026-11-20T20:35:00+00:00"))
        db.commit()
        db.close()
    def tearDown(self):
        self.tmp.cleanup()
    def test_cot_only_columns_and_exact_first_capture_join(self):
        result=module.read_snapshot(self.path)
        self.assertEqual(result["schema"],module.SCHEMA)
        self.assertEqual(result["rowCount"],3)
        self.assertFalse(result["truncated"])
        rows={(r["dataset"],r["code"]):r for r in result["rows"]}
        self.assertEqual(rows[("tff","090741")]["first_seen_at"],"2026-11-20T20:35:00+00:00")
        self.assertIsNone(rows[("tff","097741")]["first_seen_at"])
        self.assertIsNone(rows[("disagg","088691")]["first_seen_at"])
        self.assertNotIn(("tff","999999"),rows)
        self.assertNotIn("price",str(result).lower())
    def test_bounded_rows_and_cannot_create_missing_db(self):
        result=module.read_snapshot(self.path,1)
        self.assertEqual(result["rowCount"],1)
        self.assertTrue(result["truncated"])
        with self.assertRaises(ValueError):
            module.read_snapshot(self.path,5001)
        absent=Path(self.tmp.name)/"absent.sqlite3"
        with self.assertRaises(FileNotFoundError):
            module.read_snapshot(absent)
        self.assertFalse(absent.exists())
    def test_read_only_does_not_mutate_data_or_schema(self):
        before=self.path.read_bytes()
        module.read_snapshot(self.path)
        self.assertEqual(before,self.path.read_bytes())

if __name__=="__main__":
    unittest.main()
