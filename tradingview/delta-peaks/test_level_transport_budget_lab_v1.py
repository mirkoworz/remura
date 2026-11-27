# REMURA v0.8.113 LAB — 17/11/2026 06:44 CET
import tempfile,unittest,sqlite3
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,KEY,T
from level_transport_receiver_lab_v1 import decode,digest
from level_transport_sqlite_lab_v1 import PersistentReceiver
from level_transport_http_lab_v1 import ROUTE,PEER
from level_transport_budget_lab_v1 import SharedBudget,SharedAdapter

class SharedBudgetTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/"budget.sqlite";self.now=T+2000
        self.r=self.receiver(create=True,enabled=True)
        self.b=SharedBudget(self.r,initialize=True,synthetic=True)
    def receiver(self,**kw):
        return PersistentReceiver(self.path,key_hash=digest(KEY),expected_identity=decode(payload())[1],
            after_close_ms=T-300000,now=lambda:self.now,synthetic=True,**kw)
    def reopen(self):
        return SharedBudget(self.receiver(),synthetic=True)
    def adapter(self,b=None,enabled=True):
        b=self.b if b is None else b
        return SharedAdapter(b.receiver,budget=b,key_hash=digest(KEY),now=lambda:self.now,
                             enabled=enabled,synthetic=True)
    def call(self,a,**kw):
        raw=payload().encode()
        args=dict(method="POST",path=ROUTE+KEY,headers=[("Content-Type","application/json"),
            ("Content-Length",str(len(raw)))],body=raw,peer=PEER)
        return a.handle(**dict(args,**kw))["http_status"]
    def test_shared_window_across_adapters(self):
        a,c=self.adapter(),self.adapter(self.reopen())
        for i in range(20):
            self.assertEqual(self.call(a if i%2 else c,path=ROUTE+"2"*64),403)
        self.assertEqual(self.call(c),429)
        self.assertEqual(self.b.summary()["attempts"],21)
        self.now+=60000
        self.assertEqual(self.call(c,path=ROUTE+"2"*64),403)
    def test_terminal_cap_survives_reopen(self):
        for _ in range(48):self.b.reserve(T)
        c=self.reopen()
        self.assertEqual(c.reserve(T+60000),"RATE_LIMIT")
        self.assertEqual(c.summary()["attempts"],48)
    def test_concurrent_reservations(self):
        def reserve(_):return self.reopen().reserve(T)
        with ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(reserve,range(40)))
        self.assertEqual(results.count("RESERVED"),20)
        self.assertEqual(results.count("RATE_LIMIT"),20)
        self.assertEqual(self.b.summary()["attempts"],40)
    def test_stop_persistent(self):
        self.adapter().stop()
        self.assertEqual(self.call(self.adapter(self.reopen())),503)
        self.assertFalse(self.r.summary()["enabled"])
    def test_clock_regression_latches_receipt_off(self):
        self.assertEqual(self.b.reserve(T),"RESERVED")
        self.assertEqual(self.reopen().reserve(T-1),"CLOCK_UNAVAILABLE")
        self.assertEqual(self.b.reserve(T+1),"OFF")
        self.assertEqual(self.r.receive(payload(),capability=KEY)["status"],"OFF")
    def test_bad_clock_no_allowance(self):
        self.assertEqual(self.b.reserve(None),"STORAGE_UNAVAILABLE")
        self.assertEqual(self.b.summary()["attempts"],0)
    def test_no_reset_and_explicit_fixture(self):
        with self.assertRaises(sqlite3.Error):SharedBudget(self.r,initialize=True,synthetic=True)
        with self.assertRaises(ValueError):SharedBudget(self.r)
        self.assertEqual(self.b.summary()["attempts"],0)
    def test_missing_state_no_automatic_repair(self):
        with sqlite3.connect(self.path) as db:db.execute("DROP TABLE attempt_budget")
        self.assertEqual(self.call(self.adapter()),503)
        with self.assertRaises(sqlite3.Error):self.reopen()
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_corrupt_state_no_allowance(self):
        with sqlite3.connect(self.path) as db:db.execute("UPDATE attempt_budget SET total=1")
        self.assertEqual(self.call(self.adapter()),503)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_adapter_off_counts_nothing_and_pin_identity(self):
        self.assertEqual(self.call(self.adapter(enabled=False)),503)
        self.assertEqual(self.b.summary()["attempts"],0)
        with self.assertRaises(ValueError):
            SharedAdapter(self.receiver(),budget=self.b,key_hash=digest(KEY),now=lambda:self.now,synthetic=True)
    def test_first_receipt_and_duplicate_survive_reopen(self):
        self.assertEqual(self.call(self.adapter()),201)
        self.assertEqual(self.call(self.adapter(self.reopen())),200)
        self.assertEqual(self.r.summary()["accepted"],1)
        self.assertEqual(self.b.summary()["attempts"],2)
if __name__=="__main__":unittest.main()
