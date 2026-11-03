"""Offline JS↔Python parity for causal CVD pivot detector, no live data."""
import copy
import json
from pathlib import Path
import random
import subprocess
import unittest

from scripts import cvd_divergence as engine

ROOT = Path(__file__).resolve().parents[1]
STEP = engine.STEP
START = 1793577600000  # 2026-11-02T00:00:00Z


def market(side="bull", length=45, volume=100, symbol="EURUSD"):
    bars = []
    for i in range(length):
        high, low = 11.2, 10.4 if side == "bull" else 10.0
        if i == 10:
            if side == "bull":
                low = 10.0
            else:
                high = 11.6
        if i == 22:
            if side == "bull":
                low = 9.7
            else:
                high = 11.95
        bars.append({
            "t": START+i*STEP, "o": 10.8 if side == "bull" else 10.5,
            "h": high, "l": low,
            "c": 11.0 if side == "bull" else 10.2, "v": volume,
        })
    return {"symbol": symbol, "provider": "ctrader", "providerSymbol": "broker-id-1",
            "frames": {"M15": bars, "H1": [], "H4": []}}


def tick_now(m):
    return m["frames"]["M15"][-1]["t"]+STEP+60_000


def variants():
    result = []
    for side in ("bull", "bear"):
        m = market(side)
        result.append({"market": m, "now": tick_now(m)})
        result.append({"market": m, "now": tick_now(m),
                       "settings": {"right": 3, "minCvdFraction": 0.08}})
    m = market(volume=0)
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    for row in m["frames"]["M15"]:
        row["c"] = (row["h"]+row["l"])/2
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["frames"]["M15"].pop(8)
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["frames"]["M15"].pop(0)
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["frames"]["M15"][5].pop("v")
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["frames"]["M15"][3]["v"] = -1
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["frames"]["M15"][9]["t"] = m["frames"]["M15"][8]["t"]
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    result.append({"market": m, "now": tick_now(m)+91*60_000})
    m = market()
    result.append({"market": m, "now": m["frames"]["M15"][-1]["t"]+STEP-1})
    m = market()
    m["symbol"] = "USOIL"
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["provider"] = "csv"
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    m["providerSymbol"] = ""
    result.append({"market": m, "now": tick_now(m)})
    m = market(length=25)
    result.append({"market": m, "now": tick_now(m)})
    m = market()
    day2 = [dict(row, t=START+86_400_000+i*STEP)
            for i, row in enumerate(m["frames"]["M15"][:8])]
    m["frames"]["M15"].extend(day2)
    result.append({"market": m, "now": tick_now(m)})
    rng = random.Random(79044)
    for n in range(14):
        rows = []
        previous = 10.0
        for i in range(20+n*3):
            close = max(0.5, previous+rng.uniform(-0.22,0.22))
            high = max(close,previous)+rng.uniform(0.01,0.26)
            low = min(close,previous)-rng.uniform(0.01,0.26)
            rows.append({"t":START+i*STEP,"o":previous,"h":high,"l":low,
                         "c":close,"v":rng.randrange(0,400)})
            previous = close
        m = {"symbol": "EURUSD" if n%2 else "XAUUSD",
             "provider": "ctrader", "providerSymbol":"private-no-real-broker",
             "frames":{"M15":rows,"H1":[],"H4":[]}}
        result.append({"market":m,"now":tick_now(m)})
    return result


def node_results(items):
    script = """const detector=require('./cvd-divergence-core.js');
      const samples=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
      process.stdout.write(JSON.stringify(samples.map(
        s=>detector.analyze(s.market,{now:s.now,settings:s.settings||{}}))));"""
    p = subprocess.run(["node","-e",script],input=json.dumps(items),
                       capture_output=True,text=True,check=True,cwd=ROOT,timeout=15)
    return json.loads(p.stdout)


class ParityTests(unittest.TestCase):
    def assert_equivalent(self, actual, expected, context="root"):
        if isinstance(expected,dict):
            self.assertIsInstance(actual,dict,context)
            self.assertEqual(set(actual),set(expected),context)
            for key,value in expected.items():
                self.assert_equivalent(actual[key],value,context+"."+key)
        elif isinstance(expected,list):
            self.assertIsInstance(actual,list,context)
            self.assertEqual(len(actual),len(expected),context)
            for index,(a,b) in enumerate(zip(actual,expected)):
                self.assert_equivalent(a,b,context+"["+str(index)+"]")
        elif type(expected) in (int,float) and type(actual) in (int,float):
            self.assertAlmostEqual(actual,expected,delta=max(1e-8,abs(expected)*1e-12),msg=context)
        else:
            self.assertEqual(actual,expected,context)

    def test_js_python_equivalent_on_30_synthetic_scenarios(self):
        items=variants()
        self.assertEqual(len(items),30)
        expected=node_results(items)
        self.assertEqual(len(expected),len(items))
        for index,item in enumerate(items):
            original=copy.deepcopy(item)
            actual=engine.analyze(item["market"],now=item["now"],
                                  settings=item.get("settings"))
            self.assert_equivalent(actual,expected[index],context="case"+str(index))
            self.assertEqual(item,original,"must not change candle input")
        self.assertEqual(expected[0]["status"],"ok")
        self.assertEqual(len(expected[0]["events"]),1)
        self.assertEqual(expected[2]["status"],"ok")
        self.assertEqual(len(expected[2]["events"]),1)
        self.assertTrue(all(x["notificationEnabled"] is False for x in expected
                            if x["status"]=="ok"))

    def test_python_causal_confirmation_and_id_are_stable(self):
        full=market()
        before=copy.deepcopy(full)
        before["frames"]["M15"]=before["frames"]["M15"][:24]
        self.assertEqual(engine.analyze(before,now=tick_now(before))["events"],[])
        valid=copy.deepcopy(full)
        valid["frames"]["M15"]=valid["frames"]["M15"][:25]
        early=engine.analyze(valid,now=tick_now(valid))["events"]
        late=engine.analyze(full,now=tick_now(full))["events"]
        self.assertEqual(len(early),1)
        self.assertEqual(early,late)
        self.assertGreaterEqual(tick_now(valid),
                                int(__import__("datetime").datetime.fromisoformat(
                                    early[0]["confirmedAt"].replace("Z","+00:00")
                                ).timestamp()*1000))

    def test_missing_gaps_and_invalid_volumes_fail_closed(self):
        for index in (6,7,8,9,10):
            self.assertEqual(variants()[index]["market"]["provider"],"ctrader")
        self.assertEqual(engine.VERSION,"cvd-divergence-proxy-m15-v1")
        self.assertRaises(ValueError,engine.parameters,{"right":0})
        self.assertRaises(ValueError,engine.parameters,{"minCvdFraction":-1})

if __name__=="__main__":
    unittest.main()
