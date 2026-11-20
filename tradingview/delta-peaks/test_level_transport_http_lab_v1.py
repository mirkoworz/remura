# REMURA v0.8.112 LAB — 16/11/2026 17:43 CET
import tempfile,unittest,json
from pathlib import Path
from test_level_transport_receiver_lab_v1 import payload,KEY,T
from level_transport_receiver_lab_v1 import decode,digest
from level_transport_sqlite_lab_v1 import PersistentReceiver
from level_transport_http_lab_v1 import Adapter,ROUTE,PEER

class HttpAdapterTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.now=T+2000
        self.receiver=PersistentReceiver(Path(tmp.name)/"test.sqlite",key_hash=digest(KEY),
            expected_identity=decode(payload())[1],after_close_ms=T-300000,
            now=lambda:self.now,create=True,enabled=True,synthetic=True)
        self.adapter=Adapter(self.receiver,key_hash=digest(KEY),now=lambda:self.now,enabled=True,synthetic=True)
    def call(self,body=None,**kw):
        if body is None:body=payload().encode()
        args=dict(method="POST",path=ROUTE+KEY,peer=PEER,body=body,
                  headers=[("Content-Type","application/json"),("Content-Length",str(len(body)))])
        return self.adapter.handle(**dict(args,**kw))
    def test_accepted_duplicate_conflict_private_response(self):
        a=self.call();self.assertEqual(a["http_status"],201)
        self.assertEqual(self.call()["http_status"],200)
        p=json.loads(payload());p["snapshot"]["levels"][0]["price"]="1.08599"
        self.assertEqual(self.call(json.dumps(p).encode())["http_status"],409)
        self.assertEqual(self.receiver.summary()["accepted"],1)
        for secret in (KEY,"1.085301","first_received_ms",ROUTE):
            self.assertNotIn(secret,str(a))
        self.assertEqual(a["headers"]["Cache-Control"],"no-store")
    def test_off_and_wrong_peer_key(self):
        off=Adapter(self.receiver,key_hash=digest(KEY),now=lambda:self.now,synthetic=True)
        self.assertEqual(off.handle(method="POST",path=ROUTE+KEY,peer=PEER,body=b"x",headers=[])["http_status"],503)
        self.assertEqual(self.call(b"bad",peer="OTHER")["http_status"],403)
        self.assertEqual(self.call(b"bad",path=ROUTE+"2"*64)["http_status"],403)
        self.assertEqual(self.receiver.summary()["accepted"],0)
    def test_method_route_query_and_malformed_encoding(self):
        for opts,status in (({"method":"GET"},405),({"path":"/ingest/"+KEY},404),
            ({"path":ROUTE+KEY+"?a=b"},403),({"body":b"\xff","headers":[("Content-Type","application/json"),("Content-Length","1")]},400)):
            # body is supplied as keyword when present.
            self.assertEqual(self.call(**opts)["http_status"],status)
        self.assertEqual(self.receiver.summary()["accepted"],0)
    def test_headers_and_body_bounds(self):
        for headers,status in (([("Content-Type","text/plain"),("Content-Length","1")],415),
            ([("Content-Type","application/json"),("Content-Length","1"),("content-length","1")],400),
            ([("Content-Type","application/json"),("Content-Length","4")],400),
            ([("Content-Type","application/json"),("Content-Length","1"),("Transfer-Encoding","chunked")],400),
            ([("Content-Type","application/json"),("Content-Length","1"),("Content-Encoding","gzip")],400),
            ([("Content-Type","application/json"),("Content-Length","15001")],413)):
            self.assertEqual(self.call(b"x",headers=headers)["http_status"],status)
        self.assertEqual(self.call(b"x"*15001)["http_status"],413)
        self.assertEqual(self.receiver.summary()["accepted"],0)
    def test_rate_counts_denied_requests_and_session_cap(self):
        for _ in range(20):self.assertEqual(self.call(path=ROUTE+"2"*64)["http_status"],403)
        self.assertEqual(self.call()["http_status"],429)
        self.now+=60000
        for _ in range(20):self.assertEqual(self.call(path=ROUTE+"2"*64)["http_status"],403)
        self.now+=60000
        for _ in range(7):self.assertEqual(self.call(path=ROUTE+"2"*64)["http_status"],403)
        self.now+=60000
        self.assertEqual(self.call()["http_status"],429)
        self.assertEqual(self.receiver.summary()["accepted"],0)
    def test_clock_regression_and_persistent_stop(self):
        self.call();self.now-=1
        self.assertEqual(self.call()["http_status"],503)
        self.adapter.stop()
        self.assertEqual(self.call()["http_status"],503)
        self.assertFalse(self.receiver.summary()["enabled"])
    def test_late_and_wrong_schema_never_written(self):
        self.now=T+120001;self.assertEqual(self.call()["http_status"],400)
        self.assertEqual(self.call(b'{"schema":"wrong"}')["http_status"],400)
        self.assertEqual(self.receiver.summary()["accepted"],0)
    def test_constructor_requires_synthetic_and_exact_pin(self):
        with self.assertRaises(ValueError):Adapter(self.receiver,key_hash=digest(KEY),now=lambda:self.now)
        with self.assertRaises(ValueError):Adapter(self.receiver,key_hash=digest("2"*64),now=lambda:self.now,synthetic=True)
if __name__=="__main__":unittest.main()
