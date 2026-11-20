# REMURA v0.8.114 LAB — 17/11/2026 CET
import io,tempfile,unittest
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,KEY,T
from level_transport_receiver_lab_v1 import decode,digest,MAX_BYTES
from level_transport_sqlite_lab_v1 import PersistentReceiver
from level_transport_http_lab_v1 import ROUTE,PEER
from level_transport_budget_lab_v1 import SharedBudget
from level_transport_stream_lab_v1 import StreamAdapter,CHUNK,MAX_READS

class StreamTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.now=T+2000
        self.r=PersistentReceiver(Path(tmp.name)/"test.sqlite",key_hash=digest(KEY),
            expected_identity=decode(payload())[1],after_close_ms=T-300000,
            now=lambda:self.now,create=True,enabled=True,synthetic=True)
        self.b=SharedBudget(self.r,initialize=True,synthetic=True)
        self.a=StreamAdapter(self.r,budget=self.b,key_hash=digest(KEY),now=lambda:self.now,enabled=True,synthetic=True)
        self.raw=payload().encode()
    def call(self,read=None,length=None,**kw):
        if read is None:read=io.BytesIO(self.raw).read
        if length is None:length=len(self.raw)
        args=dict(method="POST",path=ROUTE+KEY,headers=[("Content-Type","application/json"),
             ("Content-Length",str(length))],peer=PEER,read=read)
        return self.a.handle_stream(**dict(args,**kw))
    def untouched(self,n):
        self.fail("reader invoked before preflight")
    def test_valid_and_duplicate_single_reservation_each(self):
        self.assertEqual(self.call()["http_status"],201)
        self.assertEqual(self.call()["http_status"],200)
        self.assertEqual(self.b.summary()["attempts"],2)
        self.assertEqual(self.r.summary()["accepted"],1)
    def test_denied_before_read(self):
        self.assertEqual(self.call(self.untouched,peer="other")["http_status"],403)
        self.assertEqual(self.call(self.untouched,length=MAX_BYTES+1)["http_status"],413)
        self.assertEqual(self.call(self.untouched,method="GET")["http_status"],405)
        self.assertEqual(self.call(self.untouched,headers=[("Content-Type","application/json"),("content-type","application/json")])["http_status"],400)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_chunk_read_limits(self):
        stream=io.BytesIO(self.raw);limits=[]
        def read(n):limits.append(n);return stream.read(n)
        self.assertEqual(self.call(read)["http_status"],201)
        self.assertTrue(all(1<=n<=CHUNK for n in limits))
        self.assertLessEqual(len(limits),MAX_READS)
        self.assertEqual(limits[-1],1)
    def test_short_and_trailing_body(self):
        self.assertEqual(self.call(io.BytesIO(self.raw[:-1]).read)["http_status"],400)
        self.assertEqual(self.call(io.BytesIO(self.raw+b"x").read)["http_status"],400)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_oversized_chunk(self):
        self.assertEqual(self.call(lambda n:b"x"*(n+1))["http_status"],413)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_bad_reader_and_read_count(self):
        def err(n):raise OSError("private fixture error")
        self.assertEqual(self.call(err)["http_status"],400)
        self.assertEqual(self.call(lambda n:None)["http_status"],400)
        calls=[]
        def tiny(n):calls.append(n);return b"x"
        self.assertEqual(self.call(tiny,length=100)["http_status"],400)
        self.assertEqual(len(calls),MAX_READS)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_stop_while_reading(self):
        stream=io.BytesIO(self.raw)
        def read(n):
            self.a.stop()
            return stream.read(n)
        self.assertEqual(self.call(read)["http_status"],503)
        self.assertEqual(self.r.summary()["accepted"],0)
        self.assertEqual(self.call(self.untouched)["http_status"],503)
    def test_rate_denial_before_read(self):
        for _ in range(20):self.b.reserve(self.now)
        self.assertEqual(self.call(self.untouched)["http_status"],429)
        self.assertEqual(self.r.summary()["accepted"],0)
    def test_zero_length_before_read(self):
        self.assertEqual(self.call(self.untouched,length=0)["http_status"],400)
        self.assertEqual(self.r.summary()["accepted"],0)
if __name__=="__main__":unittest.main()
