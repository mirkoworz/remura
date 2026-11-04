"""No-network, local-fixture tests of the one-shot pinned research probe."""
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

from scripts import shark_research_probe as probe
from test_shark_research_census import create_schema, create_sample

UTC = timezone.utc
NOW = datetime(2026, 11, 4, 10, 0, tzinfo=UTC)
ROOT = Path(__file__).resolve().parents[1] / "scripts"
MODS = ("scripts",) + tuple("scripts."+x for x in probe.BLOBS)


def local_source(name):
    if name not in probe.BLOBS:
        raise ValueError("bad_module")
    return (ROOT / (name + ".py")).read_bytes()


class ProbeTests(unittest.TestCase):
    def setUp(self):
        self.modules = {name:sys.modules.get(name) for name in MODS}
        self.bytecode = sys.dont_write_bytecode

    def tearDown(self):
        for name, obj in self.modules.items():
            if obj is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = obj
        sys.dont_write_bytecode = self.bytecode

    def test_pinned_blob_hashes_match_the_three_local_sources(self):
        self.assertEqual(set(probe.BLOBS), {
            "shark_cot_paired_baseline", "shark_data_readiness",
            "shark_research_census"})
        self.assertEqual(len(probe.SOURCE_COMMIT), 40)
        for name, expected in probe.BLOBS.items():
            self.assertEqual(probe._git_blob_hash(local_source(name)),expected)
        self.assertEqual(probe.DB_PATH,
                         "/opt/remura/private/remura-prices.sqlite3")

    def test_local_snapshot_is_read_and_source_never_fetched_online(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "sensitive.sqlite3"
            with sqlite3.connect(path) as db:
                create_schema(db)
                create_sample(db)
            before = path.read_bytes()
            with patch.object(probe,"_fetch",side_effect=AssertionError("network")):
                result = probe.run(
                    fetch=local_source,db_path=path,as_of=NOW)
            self.assertEqual(before,path.read_bytes())
            self.assertFalse(path.with_name(path.name+"-wal").exists())
            self.assertEqual(result["markets"]["EURUSD"]["historicalOutcomes"][1]["pointInTimeEligible"],1)
            self.assertEqual(result["brokerCalls"],0)
            self.assertFalse(result["actualTradingEdgeEstablished"])
            body=json.dumps(result)
            self.assertNotIn("PRIVATE_FAKE_BROKER_X",body)
            self.assertNotIn(str(path),body)
            self.assertNotIn("2026-11-02T09:01",body)

    def test_corrupted_source_blocked_before_execution(self):
        def corrupt(name):
            data = local_source(name)
            return data+b"\n# injected\n" if name=="shark_data_readiness" else data
        with self.assertRaisesRegex(ValueError,"source_integrity_failed"):
            probe.load_verified(fetch=corrupt)

    def test_short_or_wrong_shape_source_fails_closed(self):
        for source in (lambda name: b"", lambda name: "source"):
            with self.assertRaises(ValueError):
                probe.load_verified(fetch=source)

    def test_main_suppresses_private_paths_and_tracebacks(self):
        buf=io.StringIO()
        with patch.object(probe,"_fetch",side_effect=AssertionError("network")):
            with patch.object(probe,"DB_PATH","/never/show/PRIVATE_DB_SECRET.sqlite"):
                with redirect_stdout(buf):
                    exitcode = probe.main()
        self.assertEqual(exitcode,1)
        self.assertEqual(buf.getvalue().count("\n"),2)
        self.assertIn("NON_COMPLETATO",buf.getvalue())
        self.assertNotIn("PRIVATE_DB_SECRET",buf.getvalue())
        self.assertNotIn("Traceback",buf.getvalue())

    def test_invalid_naive_clock_cannot_be_used_as_asof(self):
        with self.assertRaises(ValueError):
            probe.run(fetch=local_source,db_path="/does/not/matter",
                      as_of=datetime(2026,11,4,10,0))

    def test_raw_download_target_is_a_pinned_https_allowlist(self):
        self.assertEqual(probe.RAW_BASE, "https://raw.githubusercontent.com/"
                         "mirkoworz/remura/"+probe.SOURCE_COMMIT+"/scripts/")
        with self.assertRaises(ValueError):
            probe._fetch("private_server")
        self.assertLessEqual(probe.MAX_SOURCE_BYTES,32768)


if __name__ == "__main__":
    unittest.main()
