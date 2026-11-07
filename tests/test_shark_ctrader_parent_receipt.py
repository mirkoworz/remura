"""Offline integration: the REAL private_server collector parent JSON-read clock.

No cTrader SDK, broker request, Oracle VM, identity, or production price DB.
The synthetic child process is a local runner writing a private temp JSON.
"""
from __future__ import annotations

from datetime import timedelta,timezone
import json
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))

import price_store as store
import private_server as server
from scripts import shark_ingest_first_seen as first
from test_shark_ctrader_ingest_handoff import (
    fixture, CHILD_STARTED, PARENT_READ, INGEST_DONE, SCAN, SECRET
)

class ParentReadFirstSeenTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.path=Path(self.temp.name)/"private"/"price.sqlite"
        memory,self.child,_=fixture()
        memory.close()
        self.db=store.connect(self.path)
        self.calls=[]
        self.exports=[]

    def tearDown(self):
        self.db.close()
        self.temp.cleanup()

    def init_research(self):
        first.ensure_schema(self.db)
        self.assertTrue(first.require_schema(self.db))

    def fake_runner(self,command,**kwargs):
        self.calls.append("collector")
        target=Path(command[command.index("--output")+1])
        # Simulate only an existing private child file, NOT a broker GET.
        target.write_text(json.dumps(self.child),encoding="utf-8")
        self.exports.append(target)
        return types.SimpleNamespace(returncode=0)

    def invoke(self,*,research=False,symbols=None,source="primary"):
        with patch.object(server,"source_configured",return_value=True), \
             patch.object(server,"ctrader_preflight",return_value={
                 "sdk":"installed","configuration":"ready",
                 "environment":"demo","enabled":True}), \
             patch.object(server,"access_token",return_value="synthetic-token"), \
             patch.object(server,"utcnow",
                          side_effect=[PARENT_READ,INGEST_DONE,INGEST_DONE,INGEST_DONE]):
            return server.collect_once(
                self.path, symbols or ["EURUSD"], runner=self.fake_runner,
                now=CHILD_STARTED, source=source,
                research_ingest_first_seen=research)

    def total(self):
        return self.db.execute(
            f"SELECT count(*) FROM {first.TABLE}").fetchone()[0]

    def test_original_parent_read_clock_is_persisted_at_price_upsert(self):
        self.init_research()
        out=self.invoke(research=True)
        self.assertIn("EURUSD",out["saved"])
        self.assertEqual(self.total(),1)
        proof=self.db.execute(
            f"SELECT parent_read_at_utc,recorded_at_utc,"
            f"collection_started_utc FROM {first.TABLE}"
        ).fetchone()
        self.assertEqual(proof[0],"2026-11-09T12:00:25Z")
        self.assertEqual(proof[1],"2026-11-09T12:00:40Z")
        self.assertEqual(proof[2],"2026-11-09T12:00:10Z")
        self.assertEqual(len(self.calls),1)
        self.assertFalse(self.exports[0].exists())
        summary=first.verify_scan(
            self.db,symbol="EURUSD",
            current_document=store.latest(self.db,"EURUSD"),
            scan_at=SCAN)
        self.assertEqual(summary["status"],"LOCAL_SAME_MERGED_DOCUMENT_MATCHED")
        self.assertFalse(summary["brokerSignedOrExternallyTimestamped"])
        self.assertFalse(summary["realProspectiveOutcomeOrCostsKnown"])
        self.assertEqual(summary["additionalBrokerCalls"],0)
        exposed=json.dumps(summary)+json.dumps(first.aggregate(self.db))
        self.assertNotIn(SECRET,exposed)
        self.assertNotIn("EURUSD",exposed)
        self.assertNotIn("2026-11-09",exposed)

    def test_default_off_does_not_create_or_import_research(self):
        # No first-seen schema at all. Original code still works unchanged.
        self.assertFalse(hasattr(server,"research_first_seen"))
        out=self.invoke()
        self.assertIn("EURUSD",out["saved"])
        self.assertEqual(len(self.calls),1)
        self.assertFalse(self.exports[0].exists())
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM sqlite_master WHERE name=?",
            (first.TABLE,)).fetchone()[0],0)

    def test_no_schema_or_missing_triggers_is_blocked_before_child_process(self):
        with self.assertRaisesRegex(ValueError,
                "research_append_only_migration_not_authorized_or_missing"):
            self.invoke(research=True)
        self.assertEqual(len(self.calls),0)
        self.init_research()
        self.db.execute("DROP TRIGGER research_ingest_first_no_delete")
        self.db.commit()
        with self.assertRaisesRegex(ValueError,
                "research_append_only_migration_not_authorized_or_missing"):
            self.invoke(research=True)
        self.assertEqual(len(self.calls),0)

    def test_no_auto_enable_for_full_34_market_or_secondary_broker(self):
        self.init_research()
        for syms,source in [
            (["EURUSD","USDJPY"],"primary"),
            (["EURUSD","XAUUSD","US500"],"primary"),
            (["EURUSD","EURUSD"],"primary"),
            (["EURUSD"],"backup"),
        ]:
            with self.subTest(syms=syms,source=source):
                with self.assertRaisesRegex(
                        ValueError,"research_first_seen_primary_two_market_pilot_only"):
                    self.invoke(research=True,symbols=syms,source=source)
                self.assertEqual(len(self.calls),0)
                self.assertEqual(self.total(),0)

    def test_parent_receipt_must_not_be_generatedat_or_updatedat(self):
        self.init_research()
        # The "receipt" is read immediately after file read at 12:00:25;
        # the child generatedAt was 12:00:10 and lastComplete is 11:45.
        self.invoke(research=True)
        receipt=self.db.execute(
            f"SELECT parent_read_at_utc FROM {first.TABLE}"
        ).fetchone()[0]
        candle_open=self.db.execute(
            "SELECT updated_at FROM prices WHERE symbol='EURUSD'"
        ).fetchone()[0]
        self.assertNotEqual(receipt,self.child["generatedAt"])
        self.assertNotEqual(receipt,candle_open)

    def test_invalid_child_json_never_creates_proof(self):
        self.init_research()
        def bad_runner(command,**kwargs):
            self.calls.append("collector")
            target=Path(command[command.index("--output")+1])
            target.write_text("{bad json not market",encoding="utf-8")
            self.exports.append(target)
            return types.SimpleNamespace(returncode=0)
        with patch.object(server,"source_configured",return_value=True), \
             patch.object(server,"ctrader_preflight",return_value={
                 "sdk":"installed","configuration":"ready",
                 "environment":"demo","enabled":True}), \
             patch.object(server,"access_token",return_value="synthetic-token"), \
             patch.object(server,"utcnow",return_value=PARENT_READ):
            result=server.collect_once(
                self.path,["EURUSD"],runner=bad_runner,
                now=CHILD_STARTED,research_ingest_first_seen=True)
        self.assertEqual(result["saved"],{})
        self.assertEqual(self.total(),0)
        self.assertFalse(self.exports[0].exists())

    def test_closed_market_stale_and_wrong_source_errors_do_not_store_evidence(self):
        self.init_research()
        bad=self.child
        self.child=dict(bad,markets={
            "EURUSD":dict(bad["markets"]["EURUSD"],providerSymbol="FAKE_OTHER_BROKER")})
        # This is internally coherent and locally claimed, not signed by
        # broker. It CAN be ingested as new original, and MUST NOT claim
        # origin is independently verified; this tests the epistemic limit.
        out=self.invoke(research=True)
        self.assertIn("EURUSD",out["saved"])
        self.assertEqual(self.total(),1)
        proof=first.verify_scan(
            self.db,symbol="EURUSD",
            current_document=store.latest(self.db,"EURUSD"),scan_at=SCAN)
        self.assertFalse(proof["brokerSignedOrExternallyTimestamped"])

    def test_explicit_flag_bool_cannot_be_env_or_truthy_string(self):
        self.init_research()
        with patch.dict(os.environ,{"REMURA_RESEARCH_INGEST_FIRST_SEEN":"1"},clear=False):
            out=self.invoke(research=False)
        self.assertIn("EURUSD",out["saved"])
        self.assertEqual(self.total(),0)
        with self.assertRaisesRegex(ValueError,
                                    "research_first_seen_explicit_boolean_required"):
            server.collect_once(self.path,["EURUSD"],
                research_ingest_first_seen="true",now=CHILD_STARTED)
        self.assertEqual(len(self.calls),1)


if __name__=="__main__":
    unittest.main()
