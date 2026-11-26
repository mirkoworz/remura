import unittest
from v303_science_candidate import candidate
class Candidate(unittest.TestCase):
    def test_agree_disagree(self):
        p=[1.1,1.2,1.3,1.4]
        f={"status":"DESCRIPTIVE_ONLY","segment_bars":12,"segment_cvd":"-50"}
        c={"status":"PUBLIC_DESCRIPTIVE_ONLY","asset_manager_weekly_change_pp":-2}
        self.assertEqual(candidate(p,f,c)["sides"],{"price_only":1,"footprint_only":-1,"footprint_plus_cot":-1})
        c["asset_manager_weekly_change_pp"]=2
        self.assertEqual(candidate(p,f,c)["sides"]["footprint_plus_cot"],0)
    def test_missing(self):
        self.assertEqual(candidate([1,1,1,1],{}, {})["status"],"INELIGIBLE")
