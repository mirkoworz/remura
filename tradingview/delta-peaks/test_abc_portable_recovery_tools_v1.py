# REMURA v0.8.149 LAB — 18/11/2026
import json,os,sqlite3,tempfile,unittest
from pathlib import Path
from abc_prices_recovery_v2 import snapshot,make_tar,verify_plain,inspect_closed
from abc_v165_preflight_portable_v1 import modules,SOURCES,MANIFEST
class Tests(unittest.TestCase):
    def test_portable_exact_sources_and_manifest(self):
        here=Path(__file__).resolve().parent
        for n,s in SOURCES:self.assertEqual((here/(n+".py")).read_text(),s)
        self.assertEqual((here/"abc-v165-pinned-application-manifest.json").read_text(),MANIFEST)
        p,m=modules()
        self.assertEqual(len(m),155)
        self.assertEqual(sum(r["operation"]=="add" for r in m),76)
        self.assertTrue(callable(p.oracle_report))
    def test_future_snapshot_and_schema_and_archive(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d).resolve();source=root/"live.db";copy=root/"copy.db";tar=root/"copy.tar.gz"
            a=sqlite3.connect(source)
            try:
                a.execute("PRAGMA journal_mode=WAL")
                a.executescript("CREATE TABLE prices(x);CREATE TABLE status(x);CREATE TABLE cot_reports(x);CREATE TABLE cot_first_seen(x);CREATE TABLE research_cvd_observations(x);INSERT INTO prices VALUES(1);")
                a.commit()
                summary=snapshot(source,copy)
                self.assertEqual(summary["cot_tables_present"],2)
                self.assertEqual(summary["research_tables_present"],1)
                self.assertEqual(inspect_closed(copy)["result"],summary)
                make_tar(copy,tar,6,summary)
                self.assertEqual(verify_plain(tar.read_bytes(),6)["status"],"DECRYPTION_AND_MEMBER_HASH_VERIFIED")
                with self.assertRaises(ValueError):verify_plain(tar.read_bytes(),7)
                self.assertEqual(a.execute("SELECT count(*) FROM prices").fetchone()[0],1)
            finally:a.close()
    def test_refuse_closed_with_sidecar(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d).resolve()/"x.db";p.write_bytes(b"x")
            Path(str(p)+"-wal").touch()
            with self.assertRaises(ValueError):inspect_closed(p)
