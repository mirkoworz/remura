import importlib.util
from pathlib import Path
import unittest

path=Path(__file__).resolve().parents[1] / "scripts" / "inspect_spacing.py"
spec=importlib.util.spec_from_file_location("inspect_spacing",path)
mod=importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

class SpacingTests(unittest.TestCase):
    def test_regular_ladder_with_skips(self):
        result=mod.inspect([1100,800,700,600,500,200])
        self.assertEqual(result["inferred_hops_descriptive"],[3,1,1,1,3])
        self.assertEqual(result["estimated_grid_spacing_points"],100)
        self.assertEqual(result["max_abs_fit_residual_points"],0)
        self.assertEqual(result["status"],"POST_HOC_PATTERN_ONLY_NOT_A_TRADING_SIGNAL")
    def test_bad_levels(self):
        for v in ([100],[100,200,300],[300,300,200]):
            with self.subTest(levels=v), self.assertRaises(ValueError):
                mod.inspect(v)

if __name__=="__main__":
    unittest.main()
