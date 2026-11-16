# REMURA v0.8.110 LAB — 16/11/2026 17:23 CET
import json,unittest
from concurrent.futures import ThreadPoolExecutor
from test_level_local_probe_batch_v1 import row,T
from level_transport_receiver_lab_v1 import Receiver,SCHEMA,digest,decode
# Explicitly fake credentials, no live secrets.
KEY="1"*64
def payload(step=0,**changes):
    p=row(step);p.update(mode="REALTIME_WEBHOOK_PREVIEW",version="0.9.3-level-preview",**changes)
    # Extend fixture chart periods for the entire bounded test.
    for item in p["levels"][:-1]:item["period_end_ms"]=T+7200000
    return json.dumps({"schema":SCHEMA,"snapshot":p},separators=(",",":"))
class ReceiverTests(unittest.TestCase):
    def setUp(self):
        self.now=T+1500
        self.args=dict(key_hash=digest(KEY),expected_identity=decode(payload())[1],
            after_close_ms=T-300000,now=lambda:self.now,synthetic=True)
    def make(self,**kw):return Receiver(**dict(self.args,**kw))
    def test_off_and_wrong_key_before_processing(self):
        for enabled,key,state in ((False,KEY,"OFF"),(True,"2"*64,"DENIED")):
            r=self.make(enabled=enabled)
            self.assertEqual(r.receive("bad",capability=key)["status"],state)
            self.assertEqual(r.summary()["accepted"],0)
    def test_first_receiver_timestamp_no_admission(self):
        r=self.make(enabled=True);out=r.receive(payload(),capability=KEY)
        self.assertEqual(out,{"status":"ACCEPTED_SYNTHETIC","first_received_ms":self.now})
        s=r.summary()
        self.assertEqual(s["accepted"],1)
        self.assertEqual(s["present_slots"],4)
        for flag in ("source_attested","receipt_authenticated","durable_receipt","scientific_admission","comparison_admitted","operational_signal"):
            self.assertFalse(s[flag])
        self.assertNotIn("1.085301",str(s))
    def test_duplicate_does_not_overwrite_receipt(self):
        r=self.make(enabled=True);raw=payload()
        first=r.receive(raw,capability=KEY)
        self.now+=100
        self.assertEqual(r.receive(raw,capability=KEY),{"status":"DUPLICATE","first_received_ms":first["first_received_ms"]})
        self.assertEqual(r.summary()["accepted"],1)
    def test_conflict_does_not_mutate(self):
        r=self.make(enabled=True);raw=payload();r.receive(raw,capability=KEY)
        p=json.loads(raw);p["snapshot"]["levels"][0]["price"]="1.08599"
        self.assertEqual(r.receive(json.dumps(p),capability=KEY)["status"],"CONFLICT")
        self.assertEqual(r.summary()["accepted"],1)
    def test_future_late_and_pre_cutoff_rejected(self):
        r=self.make(enabled=True)
        for tick in (T-1,T+120001):
            self.now=tick;self.assertEqual(r.receive(payload(),capability=KEY)["status"],"INVALID")
        self.now=T+1500
        self.assertEqual(self.make(enabled=True,after_close_ms=T).receive(payload(),capability=KEY)["status"],"INVALID")
    def test_shape_and_identity_fail_closed(self):
        r=self.make(enabled=True)
        p=json.loads(payload());p["snapshot"]["configuration"]["lookback"]=31
        for raw in (payload(timezone="Etc/Other"),payload(receive_clock_ms=T),json.dumps(p),
                    json.dumps(json.loads(payload())["snapshot"]),payload()+"x",
                    payload().replace('"schema":"'+SCHEMA+'"','"schema":"'+SCHEMA+'","schema":"'+SCHEMA+'"',1),"x"*16000):
            self.assertEqual(r.receive(raw,capability=KEY)["status"],"INVALID")
        self.assertEqual(r.summary()["accepted"],0)
    def test_concurrent_duplicate_single_receipt(self):
        r=self.make(enabled=True)
        with ThreadPoolExecutor(max_workers=4) as pool:
            states=list(pool.map(lambda _:r.receive(payload(),capability=KEY)["status"],range(8)))
        self.assertEqual(states.count("ACCEPTED_SYNTHETIC"),1)
        self.assertEqual(states.count("DUPLICATE"),7)
    def test_capacity_and_stop(self):
        r=self.make(enabled=True)
        for step in range(13):
            self.now=T+step*300000+1500
            self.assertEqual(r.receive(payload(step),capability=KEY)["status"],"ACCEPTED_SYNTHETIC" if step<12 else "CAPACITY")
        r.stop()
        self.assertEqual(r.receive(payload(12),capability=KEY)["status"],"OFF")
        self.assertEqual(r.summary()["accepted"],12)
    def test_synthetic_required_and_config_enrollment_pin(self):
        with self.assertRaises(ValueError):self.make(synthetic=False)
        r=self.make(enabled=True,expected_identity=decode(payload(timezone="Etc/Other"))[1])
        self.assertEqual(r.receive(payload(),capability=KEY)["status"],"INVALID")
if __name__=="__main__":unittest.main()
