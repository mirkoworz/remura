import sqlite3,unittest
from v312_collector_tick import select_slots,validate,M5
T=1800000000000
class Handoff(unittest.TestCase):
    def test_recent_history_and_repair(self):
        db=sqlite3.connect(":memory:")
        db.execute("CREATE TABLE v300_slot_coverage(close_ms INTEGER PRIMARY KEY,status TEXT,checked_ms INTEGER)")
        db.execute("INSERT INTO v300_slot_coverage VALUES(?,?,?)",(T+M5,"MISSING_AT_CHECK",T))
        result=select_slots(db,T,T+20*M5,T+21*M5)
        self.assertEqual(len(result),4)
        self.assertIn(T,result)
        self.assertIn(T+M5,result)
        self.assertGreaterEqual(max(result),T+17*M5)
        db.close()
    def test_usage_gate(self):
        p={"enabled":True,"free_confirmed":True,"start_ms":T,"end_ms":T+3600000,"first_slot_ms":T,"usage_checked_ms":T,"account_rows_read":999999}
        validate(p,T+1000)
        with self.assertRaises(ValueError):validate({**p,"account_rows_read":1000000},T+1000)
        with self.assertRaises(ValueError):validate({**p,"enabled":False},T+1000)
