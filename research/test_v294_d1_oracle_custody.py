"""New synthetic tests, no real D1 or filesystem access."""
import json,sqlite3,unittest
from v294_d1_oracle_custody import initialize,pull_once,cursor
T=1800000000000
def row(c,lag=1000,extra=0):
    m={"event_key":f"FX:EURUSD|5|{c}|0.9.1-cvd-lab","symbol":"FX:EURUSD","timeframe":"5","version":"0.9.1-cvd-lab","is_timely":0,"bar_close_ms":c,"received_at_ms":c+lag,"event_type":"HEARTBEAT"}
    p={"schema":"remura.tv.flow.cvd.preview.v1","snapshot":m,"cvd":{},"fixture":extra}
    return {**m,"raw_json":json.dumps(p)}
class Custody(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        initialize(self.db)
    def tearDown(self):
        self.db.close()
    def test_disabled(self):
        def fail(_): self.fail("unexpected fetch")
        with self.assertRaisesRegex(ValueError,"disabled"):pull_once(self.db,fail,T,T+10000)
    def test_save_and_replay(self):
        a=row(T)
        out=pull_once(self.db,lambda _: [a],T,T+10000,enabled=True)
        self.assertEqual(out["inserted"],1)
        before=cursor(self.db)
        out=pull_once(self.db,lambda _: [a],T,T+10000,enabled=True,reconciliation=True)
        self.assertEqual(out["inserted"],0)
        self.assertEqual(cursor(self.db),before)
    def test_conflict_rollback(self):
        a=row(T+300000)
        pull_once(self.db,lambda _: [a],T,T+400000,enabled=True)
        before=cursor(self.db)
        with self.assertRaisesRegex(ValueError,"custody_conflict"):
            pull_once(self.db,lambda _: [row(T),row(T+300000,extra=1)],T,T+400000,enabled=True,reconciliation=True)
        self.assertEqual(self.db.execute("SELECT count(*) FROM tv_test_custody").fetchone()[0],1)
        self.assertEqual(cursor(self.db),before)
    def test_reject_foreign_db(self):
        db=sqlite3.connect(":memory:")
        try:
            db.execute("CREATE TABLE prices (x)")
            with self.assertRaisesRegex(ValueError,"not_dedicated_db"):initialize(db)
        finally:db.close()
