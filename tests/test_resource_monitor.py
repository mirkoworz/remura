"""Pure offline tests for local resource diagnostics; no cloud credentials."""
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import resource_monitor as r

class ResourceTests(unittest.TestCase):
    def test_no_oci_billing_guesses(self):
        x=r.snapshot({"allGet":4,"privateGet":2})
        self.assertEqual(x["schema"],"remura-resources-v1")
        self.assertEqual(x["webApi"]["privateGet"],2)
        self.assertEqual(x["oracle"]["bill"],"unverified")
        self.assertIsNone(x["oracle"]["networkMonthly"])
        self.assertIsNone(x["oracle"]["externalApiCalls"])

    def test_unavailable_proc_data_not_a_zero_usage_claim(self):
        with patch.object(r,"read",return_value=""):
            self.assertIsNone(r.memory()["total"])
            self.assertIsNone(r.network()["txSinceInterfaceStart"])
            self.assertIsNone(r.snapshot()["uptimeSeconds"])

    def test_memory_uses_available_not_memfree(self):
        raw="MemTotal: 1000 kB\nMemFree: 100 kB\nMemAvailable: 600 kB\nSwapTotal: 500 kB\nSwapFree: 300 kB\n"
        with patch.object(r,"read",return_value=raw):
            self.assertEqual(r.memory()["used"],400*1024)
            self.assertEqual(r.memory()["swapUsed"],200*1024)

if __name__=="__main__": unittest.main()
