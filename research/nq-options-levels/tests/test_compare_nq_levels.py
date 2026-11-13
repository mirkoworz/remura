import importlib.util
from pathlib import Path
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "compare_nq_levels.py"
spec = importlib.util.spec_from_file_location("compare_nq_levels", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

class TestNqLevels(unittest.TestCase):
    def setUp(self):
        self.manual = {"instrument": "NQ", "session_date": "2026-11-10",
                       "levels": [30000, 29000], "published_at_utc": None}
        self.ref = {"symbol": "QQQ", "price_basis": "NDX_index_proxy_not_NQ_futures",
                    "as_of_utc": "2026-11-09T20:58:30Z",
                    "call_wall": 29900, "gamma_flip": 29200, "put_wall": 28200}
    def test_nearest_and_no_performance_claim(self):
        output = module.compare(self.manual, self.ref)
        self.assertEqual(output["comparisons"][0]["signed_distance_points"], 100)
        self.assertEqual(output["causal_status"], "EXPLORATORY_ONLY_NO_VERIFIED_FIRST_SEEN")
        self.assertEqual(output["performance_claim"], "NONE")
    def test_no_future_or_same_day_reference(self):
        self.ref["as_of_utc"] = "2026-11-10T20:00:00Z"
        with self.assertRaises(ValueError):
            module.compare(self.manual, self.ref)
    def test_reject_invalid_levels(self):
        for v in ([29000,30000], [29000,29000], [30000,-1], [30000,"x"]):
            with self.subTest(levels=v), self.assertRaises(ValueError):
                module.compare({**self.manual,"levels":v}, self.ref)
    def test_reject_wrong_basis(self):
        self.ref["price_basis"] = "NQ futures"
        with self.assertRaises(ValueError):
            module.compare(self.manual, self.ref)
    def test_timezone_required(self):
        self.ref["as_of_utc"] = "2026-11-09T20:58:30"
        with self.assertRaises(ValueError):
            module.compare(self.manual, self.ref)

if __name__ == "__main__":
    unittest.main()
