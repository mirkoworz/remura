import unittest,sqlite3
from v304_local_freeze import initialize,record,verify_chain
D={"status":"EXPLORATORY_RULE","prospective_admitted":False,"sides":{"price_only":1,"footprint_only":-1,"footprint_plus_cot":0}}
H={k:"a"*64 for k in ("price","footprint","cot")}
class Freeze(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");initialize(self.db)
    def tearDown(self):self.db.close()
    def test_disabled(self):
        with self.assertRaises(ValueError):record(self.db,D,H,lambda:100)
    def test_chain(self):
        record(self.db,D,H,lambda:100,enabled=True)
        record(self.db,D,H,lambda:101,enabled=True)
        self.assertEqual(verify_chain(self.db)["records"],2)
        self.assertFalse(verify_chain(self.db)["prospective_admitted"])
    def test_no_backdating_or_update(self):
        record(self.db,D,H,lambda:100,enabled=True)
        with self.assertRaises(ValueError):record(self.db,D,H,lambda:99,enabled=True)
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE v304_commitments SET frozen_ms=2")
