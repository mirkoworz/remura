# REMURA v0.8.116 LAB — 17/11/2026 CET
import json,subprocess,unittest
from pathlib import Path
from level_transport_receiver_lab_v1 import decode
from test_level_transport_receiver_lab_v1 import payload,T
DRIVER=Path(__file__).parent/"gateway-lab"/"level_structure_fixture_driver.mjs"
class LevelStructureParity(unittest.TestCase):
    def check(self,items):
        result=subprocess.run(["node",str(DRIVER)],input=json.dumps(items),text=True,capture_output=True,check=True,timeout=10)
        got=json.loads(result.stdout)
        self.assertEqual(len(got),len(items))
        for i,(raw,js) in enumerate(zip(items,got)):
            try:
                _,_,p=decode(raw);expected=True
            except (ValueError,TypeError,KeyError,OverflowError,RecursionError):expected=False
            self.assertEqual(js["ok"],expected,(i,raw[:80]))
            if expected:
                self.assertEqual(js["result"]["present_levels"],p["present_levels"])
                self.assertEqual(js["result"]["missing_levels"],p["missing_levels"])
                for flag in ("configuration_equivalence","receipt_authenticated","scientific_admission","operational_signal"):self.assertFalse(js["result"][flag])
    def variants(self,path,values):
        out=[]
        for value in values:
            p=json.loads(payload());cur=p
            for k in path[:-1]:cur=cur[k]
            cur[path[-1]]=value;out.append(json.dumps(p,separators=(",",":")))
        return out
    def test_valid_fixture_sequence(self):self.check([payload(i) for i in range(12)])
    def test_duplicate_keys_even_escaped(self):
        raw=payload()
        self.check([raw.replace('"schema":','"schema":"duplicate","schema":',1),
                    raw.replace('"rank":1','"rank":1,"ra\\u006ek":1',1),
                    raw+"x",raw.replace('"rank":1','"rank":1.0',1),
                    raw.replace('"rank":1','"rank":1e0',1)])
    def test_identity(self):
        items=[]
        for key,values in {"feed":["OANDA","FXCM"],"symbol":["FXCM:EURUSD"],"version":["0.9.2-level-lab"],"receive_clock_ms":[T],"history_complete":[True],"mode":["HISTORICAL_RECONSTRUCTION"]}.items():items+=self.variants(["snapshot",key],values)
        self.check(items)
    def test_clocks(self):
        items=[]
        for key,values in {"snapshot_close_ms":[T+1,T+1000],"sender_clock_ms":[T-1,T+258],"snapshot_open_ms":[T-600000,T-299999]}.items():items+=self.variants(["snapshot",key],values)
        self.check(items)
    def test_configuration(self):
        items=[]
        for key,values in {"lookback":[4,5,5.0,True],"min_peak_gap":[-1,101],"fp_ticks":[0],"max_efficiency":[-2,1],"multiplier":[0.5,1.5],"fp_imbalance_pct":[99],"delta_library":["bad"]}.items():items+=self.variants(["snapshot","configuration",key],values)
        self.check(items)
    def test_price_and_origin(self):
        items=self.variants(["snapshot","levels",0,"price"],["0","0.00001","1.00000000001",1.01,"-1",None])
        items+=self.variants(["snapshot","levels",0,"peak_origin_close_ms"],[T+1000,None,T+1])
        items+=self.variants(["snapshot","levels",0,"method"],["PERIOD_MAX_ABS_DELTA_HL2"])
        self.check(items)
    def test_boundary_order_and_fields(self):
        p=json.loads(payload());p["snapshot"]["levels"].reverse()
        q=json.loads(payload());q["snapshot"]["unexpected"]=1
        items=[json.dumps(p),json.dumps(q)]
        items+=self.variants(["snapshot","levels",1,"period_start_ms"],[T-1000,None])
        items+=self.variants(["snapshot","levels",0,"boundary_observed"],[1,None])
        self.check(items)
if __name__=="__main__":unittest.main()
