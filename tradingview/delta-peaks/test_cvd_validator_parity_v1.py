#!/usr/bin/env python3
# REMURA v0.8.61 — 14/11/2026 CET — compares identical synthetic fixtures, not Pine execution.
import copy,json,shutil,subprocess,unittest
from pathlib import Path
from test_cvd_telemetry_preview_v1 import fixture,T0
from cvd_telemetry_preview_v1 import validate

class ParityTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("node"),"Node unavailable")
    def test_shared_fixture_acceptance_and_keys(self):
        rows=[]
        for changes in ({},{"complete":False},{"price_bull":False},{"trusted_delta":0},
                        {"pivot_close_ms":T0},{"intrabar_count":4},{"segment_bars":11}):
            e=fixture();e["cvd"].update(changes);rows.append(e)
        e=fixture();e["configuration"]["cvd_right"]=4;rows.append(e)
        e=fixture();e["snapshot"]["symbol"]="FXCM:EURUSD";rows.append(e)
        expected=[]
        for e in rows:
            try:
                expected.append(validate(e,received_ms=T0+5000)["event_key"])
            except ValueError:
                expected.append(None)
        script='''import {validateCvdEnvelope} from "./worker_cvd_candidate.mjs";
import fs from "node:fs";
const {rows,at}=JSON.parse(fs.readFileSync(0,"utf8"));
console.log(JSON.stringify(rows.map(r=>{try{return validateCvdEnvelope(r,at).key;}catch{return null;}})));'''
        p=subprocess.run(["node","--input-type=module","-e",script],cwd=Path(__file__).resolve().parent/"gateway-lab",
            input=json.dumps({"rows":rows,"at":T0+5000}),text=True,capture_output=True,check=True,timeout=10)
        self.assertEqual(json.loads(p.stdout),expected)
if __name__=="__main__":
    unittest.main()
