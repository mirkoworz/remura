# REMURA v0.8.117 LAB — 17/11/2026 CET
import json,subprocess,unittest
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,T
from level_transport_receiver_lab_v1 import decode
DRIVER=Path(__file__).parent/"gateway-lab"/"level_pin_fixture_driver.mjs"
def case(raw=None,expected=None,**kw):
    raw=payload() if raw is None else raw
    p=json.loads(raw)["snapshot"]
    if expected is None:
        _,_,v=decode(raw)
        expected={k:p[k] for k in ("chart_type","timezone","session")}
        expected["configuration_digest"]=v["configuration_digest"]
    return dict(raw=raw,expected=expected,options=dict(receivedMs=T+1500,afterCloseMs=T-300000,synthetic=True)|kw)
class LevelPinTests(unittest.TestCase):
    def run_cases(self,items,expected):
        result=subprocess.run(["node",str(DRIVER)],input=json.dumps(items),text=True,capture_output=True,check=True,timeout=10)
        got=json.loads(result.stdout)
        self.assertEqual([x["ok"] for x in got],expected)
        for x in got:
            if x["ok"]:
                for flag in ("configuration_pin_matched","normalized_size_checked","fixture_cutoff_checked"):self.assertTrue(x["result"][flag])
                for flag in ("configuration_equivalence","receipt_authenticated","scientific_admission","operational_signal"):self.assertFalse(x["result"][flag])
    def test_python_digest_and_key_order(self):
        a=case();p=json.loads(a["raw"])
        p["snapshot"]["configuration"]=dict(reversed(list(p["snapshot"]["configuration"].items())))
        self.run_cases([a,case(json.dumps(p),a["expected"])],[True,True])
    def test_float_type_and_trailing_zeros(self):
        a=case();raw=a["raw"].replace('"multiplier":3.5','"multiplier":3.5000')
        integer=a["raw"].replace('"fp_imbalance_pct":300','"fp_imbalance_pct":300.0')
        self.run_cases([case(raw,a["expected"]),case(integer,a["expected"]),case(integer)],[True,False,True])
    def test_other_config_and_chart(self):
        a=case();p=json.loads(a["raw"])
        p["snapshot"]["configuration"]["lookback"]=31
        self.run_cases([case(json.dumps(p),a["expected"]),case(payload(timezone="America/New_York"),a["expected"])],[False,False])
    def test_noncanonical_numeric_subset_denied(self):
        a=case();items=[]
        for raw in [a["raw"].replace('"multiplier":3.5','"multiplier":3.5e0'),a["raw"].replace('"max_efficiency":0.07','"max_efficiency":0.00000001'),a["raw"].replace('"multiplier":3.5','"multiplier":3.500000000000001')]:
            items.append(case(raw))
        self.run_cases(items,[False]*3)
    def test_negative_zero_preserved(self):
        raw=payload().replace('"max_efficiency":0.07','"max_efficiency":-0.0')
        a=case(raw)
        self.run_cases([a,case(raw.replace('-0.0','0.0'),a["expected"])],[True,False])
    def test_receipt_clock_and_cutoff(self):
        self.run_cases([case(receivedMs=T+1234),case(receivedMs=T+1233),case(receivedMs=T+120000),case(receivedMs=T+120001),case(afterCloseMs=T),case(receivedMs=True),case(synthetic=False)],[True,False,True,False,False,False,False])
    def test_wrong_or_missing_external_pin(self):
        a=case();e=a["expected"]
        self.run_cases([case(expected={**e,"configuration_digest":"0"*64}),case(expected={k:v for k,v in e.items() if k!="configuration_digest"}),case(expected={**e,"extra":1})],[False]*3)
    def test_untrusted_unicode_and_size(self):
        a=case();raw=payload(timezone="Etc/é")
        self.run_cases([case(raw),case(a["raw"]+" "*15000,a["expected"]),case(a["raw"]+" "*1000,a["expected"])],[False,False,True])
if __name__=="__main__":unittest.main()
