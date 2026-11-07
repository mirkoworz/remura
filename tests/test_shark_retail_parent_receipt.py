"""OFFLINE integration: true private_server retail_once JSON-read path.

Real retail_once, a fake local subprocess, temporary SQLite and synthetic
Myfxbook numbers. No network, real passwords, live data or provider accounts.
"""
from __future__ import annotations
from datetime import datetime,timezone
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import types
import unittest
from unittest.mock import patch

from scripts import shark_retail_first_seen as retail
from test_shark_retail_first_seen import original,READ,RECORDED,UPDATED
import private_server as server
from price_store import connect,get_status

UTC=timezone.utc
SECRET="FAKE_MYFXBOOK_PASSWORD_NEVER_PUBLISH"


class RetailParentReadTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"private"/"prices.sqlite"
        self.db=connect(self.path)
        self.payload=original()
        self.payload["symbols"]["XAUUSD"]=copy.deepcopy(
            self.payload["symbols"]["EURUSD"])
        self.payload["symbols"]["XAUUSD"]["avgL"]=2020.
        self.calls=0

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def fake_runner(self,cmd,*,cwd,**kw):
        self.calls+=1
        self.assertTrue(str(cmd[1]).endswith("update_myfxbook.py"))
        target=Path(cwd)/"data"/"myfxbook"
        target.mkdir(parents=True,exist_ok=True)
        (target/"latest.json").write_text(
            json.dumps(self.payload),encoding="utf-8")
        return types.SimpleNamespace(returncode=0)

    def invoke(self,*,enabled=False):
        with patch.dict(os.environ,{
            "MYFXBOOK_EMAIL":"fake@example.invalid",
            "MYFXBOOK_PASSWORD":SECRET,
        }),patch.object(server,"utcnow",side_effect=[
            READ,RECORDED,RECORDED,RECORDED]):
            return server.retail_once(
                self.path,runner=self.fake_runner,
                research_retail_first_seen=enabled)

    def rows(self):
        return self.db.execute(
            f"SELECT symbol,source_updated_at,original_read_at,recorded_at "
            f"FROM {retail.TABLE} ORDER BY symbol").fetchall()

    def test_pair_from_exact_retail_once_child_file_and_local_utc(self):
        retail.ensure_schema(self.db)
        self.assertTrue(self.invoke(enabled=True))
        self.assertEqual(self.calls,1)
        self.assertEqual([x[0] for x in self.rows()],["EURUSD","XAUUSD"])
        for symbol,source,read,recorded in self.rows():
            self.assertEqual(
                datetime.fromisoformat(source.replace("Z","+00:00")),
                datetime(2026,11,9,11,55,tzinfo=UTC))
            self.assertEqual(
                datetime.fromisoformat(read.replace("Z","+00:00")),READ)
            self.assertEqual(
                datetime.fromisoformat(recorded.replace("Z","+00:00")),RECORDED)
        self.assertEqual(get_status(self.db)["retail_status"],"running")
        safe=json.dumps(retail.aggregate(self.db))+json.dumps(
            self.db.execute(f"SELECT * FROM {retail.TABLE}").fetchall())
        for forbidden in (SECRET,"fake@example.invalid","62.5","2020.0"):
            self.assertNotIn(forbidden,safe)

    def test_default_off_legacy_single_market_no_schema_or_env_switch(self):
        self.payload["symbols"].pop("XAUUSD")
        with patch.dict(os.environ,{"REMURA_RETAIL_FIRST_SEEN":"true"}):
            self.assertTrue(self.invoke(enabled=False))
        self.assertEqual(self.calls,1)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM sqlite_master WHERE name=?",
            (retail.TABLE,)).fetchone()[0],0)

    def test_absent_schema_or_trigger_prevents_any_subprocess(self):
        with self.assertRaisesRegex(ValueError,"research_retail_schema_absent"):
            self.invoke(enabled=True)
        self.assertEqual(self.calls,0)
        retail.ensure_schema(self.db)
        self.db.execute("DROP TRIGGER research_retail_first_delete")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,"research_retail_append_only_trigger_absent"):
            self.invoke(enabled=True)
        self.assertEqual(self.calls,0)

    def test_missing_pilot_rejects_both_no_partial_receipt(self):
        retail.ensure_schema(self.db)
        self.payload["symbols"].pop("XAUUSD")
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(self.rows(),[])
        self.assertEqual(get_status(self.db)["retail_status"],"failed")

    def test_changed_numeric_and_future_source_do_not_create_proof(self):
        retail.ensure_schema(self.db)
        self.payload["symbols"]["XAUUSD"]["lPct"]=float("nan")
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(self.rows(),[])
        self.payload["symbols"]["XAUUSD"]["lPct"]=62.5
        self.payload["updatedAt"]="2026-11-09T11:59:00Z"
        for entry in self.payload["symbols"].values():
            entry["t"]=self.payload["updatedAt"]
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(self.rows(),[])

    def test_duplicate_original_cannot_be_backfilled(self):
        retail.ensure_schema(self.db)
        self.assertTrue(self.invoke(enabled=True))
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(len(self.rows()),2)

    def test_second_insert_sql_failure_rolls_back_first(self):
        retail.ensure_schema(self.db)
        self.db.execute(f"""CREATE TRIGGER simulated_second_failure
            BEFORE INSERT ON {retail.TABLE}
            WHEN NEW.symbol='XAUUSD'
            BEGIN SELECT RAISE(ABORT,'fail_second_synthetic'); END""")
        self.db.commit()
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(self.rows(),[])

    def test_frozen_protocol_start_not_retrospective(self):
        retail.ensure_schema(self.db)
        self.payload["updatedAt"]="2026-11-07T12:00:00Z"
        for entry in self.payload["symbols"].values():
            entry["t"]=self.payload["updatedAt"]
        self.assertFalse(self.invoke(enabled=True))
        self.assertEqual(self.rows(),[])

    def test_flag_must_be_explicit_boolean_without_api(self):
        with self.assertRaisesRegex(ValueError,"research_retail_opt_in_boolean_required"):
            server.retail_once(self.path,runner=self.fake_runner,
                research_retail_first_seen="yes")
        self.assertEqual(self.calls,0)

    def test_normal_scheduler_remains_default_off(self):
        import inspect
        loop=inspect.getsource(server.retail_loop)
        self.assertIn("retail_once(db_path)",loop)
        self.assertNotIn("research_retail_first_seen",loop)


if __name__=="__main__":
    unittest.main()
