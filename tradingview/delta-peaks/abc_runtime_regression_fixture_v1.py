# REMURA v0.8.131 LAB — 17/11/2026 12:05 CET
import json,os,sys,tempfile,threading,unittest
from pathlib import Path
from unittest.mock import patch
from http.server import ThreadingHTTPServer
from urllib.request import urlopen
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import private_server as server
import price_store
class ABCFixture(unittest.TestCase):
    def test_b_default_observer_once_even_with_partial_ack(self):
        for env in ({},{"REMURA_SHARK_COMPACT_RESEARCH_ENABLED":"1"},{"REMURA_SHARK_COMPACT_RESEARCH_ACK":"ACK_UNVALIDATED_PROSPECTIVE_RESEARCH"}):
            with patch.object(server,"observe_squalincome",return_value={"fixture":True}) as observer:
                self.assertEqual(server.observe_periodic_squalincome("fixture",env=env),{"fixture":True})
                observer.assert_called_once_with("fixture")
    def test_c_resources_off_default_and_cached_on(self):
        with tempfile.TemporaryDirectory() as folder:
            db=Path(folder)/"prices.sqlite";price_store.connect(db).close()
            with patch.object(server,"resource_snapshot",return_value={"fixture":True}),patch.object(server._STORAGE_CACHE,"peek",return_value={"fixtureCache":True}) as peek:
                site=ThreadingHTTPServer(("127.0.0.1",0),server.http_handler(db))
                th=threading.Thread(target=site.serve_forever,daemon=True);th.start()
                try:
                    url=f"http://127.0.0.1:{site.server_address[1]}/private-api/resources"
                    with patch.dict(os.environ,{},clear=True),urlopen(url,timeout=5) as response:
                        self.assertEqual(json.load(response),{"fixture":True})
                    peek.assert_not_called()
                    with patch.dict(os.environ,{"REMURA_STORAGE_DIAG_ENABLED":"1"},clear=True),urlopen(url,timeout=5) as response:
                        self.assertEqual(json.load(response)["storageInventory"],{"fixtureCache":True})
                    peek.assert_called_once_with()
                finally:site.shutdown();site.server_close();th.join(timeout=5)
    def test_research_collect_guard_denies_before_runner(self):
        with patch.object(server,"connect",side_effect=AssertionError("unexpected DB")):
            with self.assertRaises(ValueError):server.collect_once("fixture",["USDJPY"],research_ingest_first_seen=True)
            with self.assertRaises(ValueError):server.retail_once("fixture",research_retail_numeric_features=True)
