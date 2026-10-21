"""Offline Linux-only test of shared cTrader collection lock."""
import os
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
from ctrader_lock import collection_guard


@unittest.skipUnless(os.name=="posix", "Uses Linux flock")
class CTraderLockTests(unittest.TestCase):
    def test_guard_serializes_and_releases_across_file_descriptors(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"private"/"prices.sqlite3"
            with collection_guard(db,timeout_seconds=1):
                with self.assertRaises(TimeoutError):
                    with collection_guard(db,timeout_seconds=0.05):
                        self.fail("Concurrent lock should not be acquired")
            with collection_guard(db,timeout_seconds=1):
                self.assertTrue((db.parent/"ctrader-collection.lock").is_file())

    def test_guard_releases_after_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            db=Path(temp)/"prices.sqlite3"
            with self.assertRaisesRegex(RuntimeError,"fake"):
                with collection_guard(db,timeout_seconds=1):
                    raise RuntimeError("fake")
            with collection_guard(db,timeout_seconds=1):
                self.assertTrue(True)


if __name__=="__main__":
    unittest.main()
