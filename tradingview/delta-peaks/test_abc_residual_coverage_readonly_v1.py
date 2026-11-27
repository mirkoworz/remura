# REMURA v0.8.141 LAB — 18/11/2026, sessione 09:19 CET
import sqlite3
import tempfile
import unittest
from pathlib import Path
from abc_residual_coverage_readonly_v1 import cot_closed, classify_environment_files, metadata

class ResidualCoverageTest(unittest.TestCase):
    def test_cot_counts_and_lineage_gaps(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"copy.db"
            db=sqlite3.connect(p)
            db.executescript("""
            CREATE TABLE cot_reports(dataset,code,report_date,oi,first_long,first_short,second_long,second_short);
            CREATE TABLE cot_first_seen(dataset,code,report_date,first_seen_at);
            INSERT INTO cot_reports VALUES ('TFF','A','2026-11-10',1,2,3,4,5),('TFF','B','2026-11-10',1,2,3,4,5);
            INSERT INTO cot_first_seen VALUES ('TFF','A','2026-11-10','2026-11-13'),('TFF','C','2026-11-03','2026-11-06');
            """)
            db.commit(); db.close()
            before=p.read_bytes()
            out=cot_closed(p)
            self.assertEqual(out["cot_reports"]["rows"],2)
            self.assertEqual(out["reports_without_first_seen"],1)
            self.assertEqual(out["first_seen_without_reports"],1)
            self.assertEqual(before,p.read_bytes())
    def test_missing_and_view(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"copy.db"
            db=sqlite3.connect(p);db.execute("CREATE VIEW cot_reports AS SELECT 1");db.close()
            r=cot_closed(p)
            self.assertEqual(r["cot_reports"]["state"],"unexpected_object")
            self.assertEqual(r["cot_first_seen"]["state"],"absent")
    def test_sidecars_denied(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"copy.db"
            p.touch();Path(str(p)+"-wal").touch()
            with self.assertRaises(ValueError):cot_closed(p)
    def test_metadata_no_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"env";p.write_text("SECRET=never_print")
            p.chmod(0o600); self.assertEqual(metadata(p),"regular_restricted")
            r=classify_environment_files(str(p)+" (ignore_errors=no)")
            self.assertEqual(r["classes"],{"regular_restricted":1})
            self.assertNotIn(str(p),str(r))
            self.assertEqual(classify_environment_files("ambiguous")["state"],"unparsed")
            self.assertEqual(classify_environment_files("")["state"],"none_reported")
