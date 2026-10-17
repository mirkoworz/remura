"""Offline tests for the private IG endpoint and guarded scheduler."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import private_server as server
import price_store as store


class TestPrivateIg(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.db_path=Path(self.temp.name)/"private"/"prices.sqlite"
        self.ig_dir=self.db_path.parent/"ig"
        self.ig_dir.mkdir(parents=True,exist_ok=True)
    def tearDown(self):
        self.temp.cleanup()

    def snapshot(self):
        return {"status":"ok","source":"IG Client Sentiment",
                "environment":"demo","updatedAt":"2026-10-17T09:00:00Z",
                "symbols":{
                    "EURUSD":{"t":"2026-10-17T09:00:00Z","lPct":61,"sPct":39,"metric":"client_positions",
                              "SECRET":"must never leak"},
                    "OTHER":{"t":"2026-10-17T09:00:00Z","lPct":80,"sPct":20},
                    "GBPUSD":{"t":"2026-10-17T09:00:00Z","lPct":160,"sPct":20}}}

    def test_only_whitelisted_aggregates_leave_private_storage(self):
        target=self.ig_dir/"latest.json"
        target.write_text(json.dumps(self.snapshot()),encoding="utf-8")
        doc=server.ig_document(self.db_path)
        self.assertEqual(set(doc["symbols"]),{"EURUSD"})
        self.assertEqual(doc["symbols"]["EURUSD"]["lPct"],61)
        self.assertNotIn("SECRET",json.dumps(doc))
        self.assertNotIn("marketId",json.dumps(doc))
        self.assertIsNone(server.resolve_asset("/private/ig/latest.json"))

    def test_missing_invalid_or_empty_source_returns_no_data(self):
        self.assertIsNone(server.ig_document(self.db_path))
        target=self.ig_dir/"latest.json"
        target.write_text("{bad",encoding="utf-8")
        self.assertIsNone(server.ig_document(self.db_path))
        target.write_text(json.dumps({"status":"ok","symbols":{}}),encoding="utf-8")
        self.assertIsNone(server.ig_document(self.db_path))

    def test_without_credentials_collection_is_disabled(self):
        with patch.dict(os.environ,{"IG_API_KEY":"","IG_IDENTIFIER":"","IG_PASSWORD":""}):
            self.assertFalse(server.ig_once(self.db_path,runner=lambda *a,**k: None))
        db=store.connect(self.db_path)
        try:
            self.assertEqual(store.get_status(db)["ig_status"],"awaiting_credentials")
        finally:
            db.close()


if __name__=="__main__":
    unittest.main()
