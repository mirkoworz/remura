"""REMURA P0: private capacity endpoint integration, no VPS or credentials."""
import json
from http.server import ThreadingHTTPServer
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import private_server as server


class PrivateResourceEndpointTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db=Path(self.temp.name)/"private"/"remura-prices.sqlite3"
        self.db.parent.mkdir(parents=True)
        self.db.write_bytes(b"private-test-only")
        self.site=ThreadingHTTPServer(("127.0.0.1",0),server.http_handler(self.db))
        self.worker=threading.Thread(target=self.site.serve_forever,daemon=True)
        self.worker.start()

    def tearDown(self):
        self.site.shutdown()
        self.site.server_close()
        self.worker.join(timeout=2)
        self.temp.cleanup()

    def endpoint(self):
        with urlopen("http://127.0.0.1:"+str(self.site.server_port)
                     +"/private-api/resources/status",timeout=5) as response:
            self.assertEqual(response.headers.get("Cache-Control"),
                             "no-store, max-age=0")
            self.assertEqual(response.headers.get("X-Content-Type-Options"),"nosniff")
            return json.load(response)

    def test_endpoint_reports_sanitized_data_and_never_enables_paid_growth(self):
        data={"schema":"remura-p0-capacity-v1",
              "capacityGate":"capacity_only_pass",
              "reasons":[],
              "diskTotalBytes":20*1024**3,
              "diskAvailableBytes":8*1024**3,
              "memoryTotalBytes":6*1024**3,
              "memoryAvailableBytes":3*1024**3,
              "allowAutomaticExpansion":False,
              "oracleAlwaysFreeVerified":False,
              "backupIntegrityVerified":False,
              "interpretation":"local_capacity_only_not_oracle_billing_attestation"}
        before=self.db.read_bytes()
        with patch.object(server,"capture_local_capacity",return_value=data) as probe:
            result=self.endpoint()
            self.assertEqual(probe.call_count,1)
            self.assertEqual(result["capacityGate"],"capacity_only_pass")
            self.assertFalse(result["oracleAlwaysFreeVerified"])
            self.assertFalse(result["allowAutomaticExpansion"])
        self.assertEqual(self.db.read_bytes(),before)
        serialized=json.dumps(result)
        self.assertNotIn(str(self.db),serialized)
        self.assertNotIn("account",serialized.lower())
        self.assertNotIn("token",serialized.lower())

    def test_failure_returns_hold_without_local_errors_or_paths(self):
        with patch.object(server,"capture_local_capacity",
                          side_effect=OSError("sensitive/path/not-for-logs")):
            result=self.endpoint()
        self.assertEqual(result["schema"],"remura-p0-capacity-v1")
        self.assertEqual(result["capacityGate"],"hold")
        self.assertEqual(result["reasons"],["local_resource_sample_unavailable"])
        self.assertNotIn("sensitive",json.dumps(result))
        self.assertFalse(result["allowAutomaticExpansion"])

    def test_nonconforming_probe_fails_closed(self):
        with patch.object(server,"capture_local_capacity",return_value={"bad":"schema"}):
            result=self.endpoint()
        self.assertEqual(result["capacityGate"],"hold")


if __name__=="__main__":
    unittest.main()
