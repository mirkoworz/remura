"""No-network regression tests for full-universe immutable one-shot probe."""
from contextlib import redirect_stdout
from datetime import datetime, timezone
import io
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

from scripts import shark_universe_probe as probe
from test_shark_universe_lineage import schema, insert

NOW=datetime(2026,11,4,10,0,tzinfo=timezone.utc)
ROOT=Path(__file__).resolve().parents[1]/"scripts"
MODS=("scripts",)+tuple("scripts."+x for x in probe.BLOBS)


def source(name):
    if name not in probe.BLOBS:
        raise ValueError("invalid_module")
    return (ROOT/(name+".py")).read_bytes()


class UniverseProbeTests(unittest.TestCase):
    def setUp(self):
        self.previous={k:sys.modules.get(k) for k in MODS}
        self.bytecode=sys.dont_write_bytecode

    def tearDown(self):
        for k,v in self.previous.items():
            if v is None:
                sys.modules.pop(k,None)
            else:
                sys.modules[k]=v
        sys.dont_write_bytecode=self.bytecode

    def test_pinned_blobs_match_checkout_and_immutable_commit(self):
        self.assertEqual(len(probe.PIN),40)
        self.assertEqual(set(probe.BLOBS),{
            "shark_cot_paired_baseline","shark_universe_lineage"})
        for name, expected in probe.BLOBS.items():
            self.assertEqual(probe.blob_hash(source(name)),expected)
        self.assertEqual(probe.DB_PATH,"/opt/remura/private/remura-prices.sqlite3")

    def test_private_sqlite_read_only_and_no_network(self):
        with tempfile.TemporaryDirectory() as work:
            path=Path(work)/"PRIVATE_DB_FILE"
            with sqlite3.connect(path) as db:
                schema(db)
                insert(db,"EURJPY")
                insert(db,"XAUUSD")
                db.commit()
            original=path.read_bytes()
            with patch.object(probe,"_fetch",side_effect=AssertionError("network forbidden")):
                report=probe.run(fetch=source,database=path,as_of=NOW)
            self.assertEqual(original,path.read_bytes())
            self.assertFalse(path.with_name(path.name+"-wal").exists())
            self.assertEqual(report["reasons"]["eligible_time_provenance_only"],2)
            self.assertEqual(report["eligibleMarketsByFamily"]["fx_cross_two_legs"],1)
            self.assertEqual(report["edge"],"NOT_ESTABLISHED")
            self.assertEqual(report["brokerCalls"],0)
            safe=json.dumps(report)
            self.assertNotIn("SENSITIVE_BROKER",safe)
            self.assertNotIn("PRIVATE_DB_FILE",safe)
            self.assertNotIn("2026-11-02T09:01",safe)

    def test_corrupt_source_cannot_execute(self):
        def corrupt(name):
            val=source(name)
            return val+b"\n# not signed\n" if name=="shark_universe_lineage" else val
        with self.assertRaisesRegex(ValueError,"source_integrity_failed"):
            probe.verified_modules(fetch=corrupt)

    def test_missing_or_invalid_source_is_rejected(self):
        for value in (lambda name:b"",lambda name:object()):
            with self.assertRaises(ValueError):
                probe.verified_modules(fetch=value)

    def test_errors_do_not_leak_path_or_traceback(self):
        buf=io.StringIO()
        with patch.object(probe,"_fetch",side_effect=ValueError("PRIVATE_TOKEN")):
            with patch.object(probe,"DB_PATH","/private/SECRET_PATH"):
                with redirect_stdout(buf):
                    self.assertEqual(probe.main(),1)
        self.assertIn("NON_COMPLETATO",buf.getvalue())
        self.assertNotIn("PRIVATE_TOKEN",buf.getvalue())
        self.assertNotIn("SECRET_PATH",buf.getvalue())
        self.assertNotIn("Traceback",buf.getvalue())

    def test_naive_timestamp_not_accepted(self):
        with self.assertRaises(ValueError):
            probe.run(fetch=source,database="/not/there",
                      as_of=datetime(2026,11,4,10))

    def test_raw_fetch_only_pinned_public_github(self):
        self.assertEqual(probe.BASE,
                         "https://raw.githubusercontent.com/mirkoworz/remura/"
                         +probe.PIN+"/scripts/")
        with self.assertRaises(ValueError):
            probe._fetch("private_server")


if __name__=="__main__":
    unittest.main()
