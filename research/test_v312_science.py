import sqlite3,unittest
from v311_science import initialize,ingest,observe_tick
from v312_science_continuation import prepare,evaluate_pending,summary
from test_v311_science import fixture,COT,T,F,M
class Continuation(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        initialize(self.db);prepare(self.db)
        now=T+400000
        ingest(self.db,[fixture(T-i*F) for i in range(11,-1,-1)],now)
        observe_tick(self.db,COT,b"fixture",lambda:now,now)
    def tearDown(self):self.db.close()
    def test_preserve_and_mature_once(self):
        self.assertEqual(summary(self.db)["local_observations"],1)
        end=T+5*M
        ingest(self.db,[fixture(t) for t in range(T+M+F,end+1,F)],end+1000)
        self.assertEqual(evaluate_pending(self.db,end+1000)["new_outcome_rows"],3)
        self.assertEqual(evaluate_pending(self.db,end+1000)["new_outcome_rows"],0)
    def test_terminal_missing_not_fake_result(self):
        out=evaluate_pending(self.db,T+100*3600000)
        self.assertEqual(out["terminal_missing_added"],3)
        self.assertEqual(summary(self.db)["outcome_rows"],0)
        self.assertFalse(summary(self.db)["prospective_admitted"])
