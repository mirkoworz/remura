# REMURA v0.8.127 LAB — 17/11/2026 CET
import sqlite3,unittest,concurrent.futures,threading,uuid
from level_receipt_publication_lab_v1 import init,publish,latest,LIMIT
from level_receipt_witness_lab_v1 import ZERO
KEY=b"j"*32
FLAGS=dict(synthetic=True,ingress_closed=True)
def gen(i):return f"{i:032x}"
def pin(i):return f"{i:064x}"
class PublicationTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        init(self.db,**FLAGS)
    def pub(self,anchor=ZERO,i=1,**kw):
        args=dict(expected_anchor=anchor,new_generation=gen(i),new_snapshot_pin=pin(i),**FLAGS)
        return publish(self.db,KEY,**dict(args,**kw))
    def test_atomic_chain_and_latest(self):
        r,a=self.pub();s,b=self.pub(a,2)
        self.assertEqual(s["body"]["previous_anchor"],a)
        self.assertEqual(latest(self.db,KEY,expected_anchor=b,**FLAGS),(s,b))
        with self.assertRaises(ValueError):latest(self.db,KEY,expected_anchor=a,**FLAGS)
    def test_stale_writer_preserves_head(self):
        _,a=self.pub();r,b=self.pub(a,2)
        with self.assertRaises(ValueError):self.pub(a,3)
        self.assertEqual(latest(self.db,KEY,expected_anchor=b,**FLAGS),(r,b))
        self.assertEqual(self.db.execute("SELECT count(*) FROM custody_fixture").fetchone()[0],2)
        self.assertFalse(self.db.in_transaction)
    def test_generation_and_pin_cannot_be_reused(self):
        _,a=self.pub();_,b=self.pub(a,2)
        for kw in (dict(new_generation=gen(1)),dict(new_snapshot_pin=pin(1))):
            with self.assertRaises(ValueError):self.pub(b,3,**kw)
        self.assertEqual(self.db.execute("SELECT count(*) FROM custody_fixture").fetchone()[0],2)
    def test_tampered_previous_record_fails_closed(self):
        _,a=self.pub();_,b=self.pub(a,2)
        self.db.execute("UPDATE custody_fixture SET record='{}' WHERE seq=1");self.db.commit()
        with self.assertRaises(ValueError):self.pub(b,3)
        with self.assertRaises(ValueError):latest(self.db,KEY,expected_anchor=b,**FLAGS)
    def test_wrong_key_and_scope(self):
        _,a=self.pub()
        with self.assertRaises(ValueError):latest(self.db,b"x"*32,expected_anchor=a,**FLAGS)
        with self.assertRaises(ValueError):self.pub(a,2,synthetic=False)
        self.db.execute("CREATE TEMP TABLE custody_fixture(x)")
        with self.assertRaises(ValueError):self.pub(a,2)
    def test_two_writers_one_winner(self):
        uri="file:custody-"+uuid.uuid4().hex+"?mode=memory&cache=shared"
        keeper=sqlite3.connect(uri,uri=True);self.addCleanup(keeper.close)
        init(keeper,**FLAGS)
        _,a=publish(keeper,KEY,expected_anchor=ZERO,new_generation=gen(1),new_snapshot_pin=pin(1),**FLAGS)
        barrier=threading.Barrier(2)
        def writer(i):
            db=sqlite3.connect(uri,uri=True,timeout=1)
            try:
                barrier.wait(timeout=5)
                try:return publish(db,KEY,expected_anchor=a,new_generation=gen(i),new_snapshot_pin=pin(i),**FLAGS)
                except (ValueError,sqlite3.OperationalError):return None
            finally:db.close()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results=list(pool.map(writer,(2,3)))
        winners=[r for r in results if r is not None]
        self.assertEqual(len(winners),1)
        self.assertEqual(latest(keeper,KEY,expected_anchor=winners[0][1],**FLAGS),winners[0])
        self.assertEqual(keeper.execute("SELECT count(*) FROM custody_fixture").fetchone()[0],2)
    def test_bounded_capacity_and_no_reinit(self):
        a=ZERO
        for i in range(1,LIMIT+1):_,a=self.pub(a,i)
        with self.assertRaises(ValueError):self.pub(a,LIMIT+1)
        with self.assertRaises(ValueError):init(self.db,**FLAGS)
        self.assertEqual(self.db.execute("SELECT count(*) FROM custody_fixture").fetchone()[0],LIMIT)
if __name__=="__main__":unittest.main()
