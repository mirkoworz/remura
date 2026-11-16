# REMURA v0.8.111 LAB — 16/11/2026 17:39 CET
import json,sqlite3,tempfile,unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from test_level_transport_receiver_lab_v1 import payload,KEY,T
from level_transport_receiver_lab_v1 import decode,digest
from level_transport_sqlite_lab_v1 import PersistentReceiver
class SQLiteReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.path=Path(self.tmp.name)/"test.sqlite";self.now=T+2000
        self.args=dict(key_hash=digest(KEY),expected_identity=decode(payload())[1],
          after_close_ms=T-300000,now=lambda:self.now,synthetic=True)
    def open(self,**kw):return PersistentReceiver(self.path,**dict(self.args,**kw))
    def make(self):return self.open(create=True,enabled=True)
    def test_reopen_first_receipt_and_conflict(self):
        a=self.make().receive(payload(),capability=KEY);self.now+=1
        b=self.open();self.assertEqual(b.receive(payload(),capability=KEY),{"status":"DUPLICATE","first_received_ms":a["first_received_ms"]})
        p=json.loads(payload());p["snapshot"]["levels"][0]["price"]="1.08599"
        self.assertEqual(b.receive(json.dumps(p),capability=KEY)["status"],"CONFLICT")
        self.assertEqual(b.summary()["accepted"],1);self.assertFalse(b.summary()["durable_receipt"])
        self.assertNotIn("1.085301",str(b.summary()))
    def test_stop_survives_reopen(self):
        a=self.make();a.stop();b=self.open()
        self.assertEqual(b.receive(payload(),capability=KEY)["status"],"OFF")
        with self.assertRaises(ValueError):self.open(enabled=True)
    def test_concurrent_connections_one_receipt(self):
        self.make()
        with ThreadPoolExecutor(max_workers=4) as pool:
            results=list(pool.map(lambda _:self.open().receive(payload(),capability=KEY)["status"],range(8)))
        self.assertEqual(results.count("ACCEPTED_SYNTHETIC"),1)
        self.assertEqual(results.count("DUPLICATE"),7)
    def test_capacity_survives_reopen(self):
        self.make()
        for step in range(13):
            self.now=T+step*300000+2000
            self.assertEqual(self.open().receive(payload(step),capability=KEY)["status"],"ACCEPTED_SYNTHETIC" if step<12 else "CAPACITY")
        self.assertEqual(self.open().summary()["accepted"],12)
    def test_wrong_pin_and_no_silent_recreation(self):
        with self.assertRaises(ValueError):self.open()
        self.make()
        with self.assertRaises(FileExistsError):self.make()
        with self.assertRaises(ValueError):self.open(after_close_ms=T)
        a=self.open();self.path.unlink()
        self.assertEqual(a.receive(payload(),capability=KEY)["status"],"INVALID")
        self.assertFalse(self.path.exists())
    def test_corruption_fails_closed(self):
        a=self.make();a.receive(payload(),capability=KEY)
        with sqlite3.connect(self.path) as db:db.execute("UPDATE receipts SET body_digest=?",("0"*64,))
        self.assertEqual(a.receive(payload(),capability=KEY)["status"],"INVALID")
        with self.assertRaises(ValueError):self.open()
    def test_off_denied_and_invalid_no_writes(self):
        a=self.open(create=True);self.assertEqual(a.receive("bad",capability=KEY)["status"],"OFF")
        self.path.unlink();a=self.make()
        self.assertEqual(a.receive("bad",capability="2"*64)["status"],"DENIED")
        self.assertEqual(a.receive("bad",capability=KEY)["status"],"INVALID")
        self.assertEqual(a.summary()["accepted"],0)
    def test_synthetic_only_and_late_receipt(self):
        with self.assertRaises(ValueError):self.open(create=True,synthetic=False)
        a=self.make();self.now=T+120001
        self.assertEqual(a.receive(payload(),capability=KEY)["status"],"INVALID")
        self.assertEqual(a.summary()["accepted"],0)
if __name__=="__main__":unittest.main()
