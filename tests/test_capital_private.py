"""Private REMURA API never exposes credentials, raw provider identifiers."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/"scripts"))
import private_server as api

class CapitalPrivateTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.db=Path(self.tmp.name)/"private"/"prices.sqlite"
        self.dir=self.db.parent/"capital"
        self.dir.mkdir(parents=True)
    def tearDown(self):self.tmp.cleanup()

    def test_filtered_latest_and_history(self):
        payload={"status":"ok","environment":"demo","updatedAt":"2026-10-18T09:00:00Z",
                 "symbols":{
                  "XAGUSD":{"t":"2026-10-18T09:00:00Z","lPct":71,"sPct":29,
                            "marketId":"SILVER","SECRET":"never expose"},
                  "EURUSD":{"t":"2026-10-18T09:00:00Z","lPct":200,"sPct":-100},
                  "OTHER":{"t":"2026-10-18T09:00:00Z","lPct":50,"sPct":50}}}
        (self.dir/"latest.json").write_text(json.dumps(payload))
        doc=api.capital_document(self.db,api.CAPITAL_LATEST)
        self.assertEqual(set(doc["symbols"]),{"XAGUSD"})
        self.assertNotIn("SECRET",json.dumps(doc))
        self.assertNotIn("marketId",json.dumps(doc))
        self.assertIsNone(api.resolve_asset("/private/capital/latest.json"))
        hist=self.dir/"history"
        hist.mkdir()
        (hist/"XAGUSD.json").write_text(json.dumps({"symbol":"XAGUSD",
            "records":[payload["symbols"]["XAGUSD"]]}))
        old=api.capital_document(self.db,"/private-api/capital/history/XAGUSD.json")
        self.assertEqual(len(old["records"]),1)
        self.assertNotIn("SECRET",json.dumps(old))
        self.assertIsNone(api.capital_document(self.db,"/private-api/capital/history/OTHER.json"))

    def test_missing_data_is_not_made_up(self):
        self.assertIsNone(api.capital_document(self.db,api.CAPITAL_LATEST))
        (self.dir/"latest.json").write_text('{"status":"ok","environment":"live","symbols":{"XAGUSD":{"t":"2026-10-18T09:00:00Z","lPct":70,"sPct":30}}}')
        self.assertIsNone(api.capital_document(self.db,api.CAPITAL_LATEST))

if __name__=="__main__":unittest.main()
