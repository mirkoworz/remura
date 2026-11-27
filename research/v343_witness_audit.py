"""REMURA V34.3 — offline witness classification.
Does not contact TSA, alter prior result, or admit an observation.
This audit relies on the recorded V34.1 cryptographic verification result;
it is not an independent signature verification.
"""
import json,sys,re,subprocess,os,unittest
from pathlib import Path
ROOT=Path.home()/".remura-v296/v318/witness-v341"
def assess(packet,result,attempt,accuracy):
    freeze=packet["frozen_ms"];entry=packet["entry_ms"]
    sent=attempt["attempt_ms"];received=result["received_ms"]
    declared=result["signed_time_lower_ms"]
    if any(type(t) is not int for t in (freeze,entry,sent,received,declared)):
        raise ValueError("clock")
    if result["status"] not in ("WITNESS_TIME_NOT_ADMITTED","WITNESSED_BEFORE_ENTRY") or result["prospective_admitted"] is not False:
        raise ValueError("prior_result")
    if result["entry_ms"]!=entry or not 0<freeze<=sent<=received:
        raise ValueError("clock")
    local_before=received<entry
    declared_before=freeze<=declared<entry
    if not local_before or not declared_before:status="TIME_INCONSISTENT"
    elif accuracy.strip().lower()=="unspecified":status="SIGNED_WITNESS_ACCURACY_UNSPECIFIED"
    else:status="SIGNED_WITNESS_ACCURACY_REVIEW_REQUIRED"
    return {"status":status,"prior_result":result["status"],
        "prior_crypto_check":"RECORDED_V341_COMPLETED_NOT_REVERIFIED",
        "accuracy":accuracy,"declared_time_before_entry":declared_before,
        "local_receipt_before_entry":local_before,"receipt_margin_ms":entry-received,
        "roundtrip_ms":received-sent,"prospective_admitted":False,
        "new_tsa_requests":0,"persistent_write":False}
def run():
    def j(n):return json.loads((ROOT/n).read_bytes())
    text=subprocess.run(["/usr/bin/openssl","ts","-reply","-in","response.tsr","-text"],
        cwd=ROOT,env=dict(os.environ,LC_ALL="C",TZ="UTC"),capture_output=True,check=True,timeout=10).stdout.decode("ascii")
    matches=re.findall(r"^Accuracy:\s*([^\r\n]+)$",text,re.M)
    if len(matches)!=1:raise ValueError("accuracy")
    return assess(j("packet.json"),j("result.json"),j("attempt.json"),matches[0])
class Tests(unittest.TestCase):
    def test_unknown(self):
        p={"frozen_ms":1000,"entry_ms":10000}
        r={"status":"WITNESS_TIME_NOT_ADMITTED","prospective_admitted":False,"received_ms":2345,"signed_time_lower_ms":2000,"entry_ms":10000}
        a={"attempt_ms":1700}
        out=assess(p,r,a,"unspecified")
        self.assertEqual(out["status"],"SIGNED_WITNESS_ACCURACY_UNSPECIFIED")
        self.assertFalse(out["prospective_admitted"])
        self.assertEqual(out["new_tsa_requests"],0)
        self.assertEqual(assess(p,r,a,"1 second")["status"],"SIGNED_WITNESS_ACCURACY_REVIEW_REQUIRED")
    def test_late(self):
        p={"frozen_ms":1000,"entry_ms":2000}
        r={"status":"WITNESS_TIME_NOT_ADMITTED","prospective_admitted":False,"received_ms":2345,"signed_time_lower_ms":1800,"entry_ms":2000}
        self.assertEqual(assess(p,r,{"attempt_ms":1700},"unspecified")["status"],"TIME_INCONSISTENT")
if __name__=="__main__":
    if sys.argv[1:]==["--selftest"]:unittest.main(argv=[sys.argv[0]])
    elif sys.argv[1:]==["--audit"]:
        try:print("V343 WITNESS",json.dumps(run(),sort_keys=True))
        except Exception as e:print("V343 STOP",type(e).__name__);sys.exit(2)
    else:raise SystemExit("--selftest | --audit")
