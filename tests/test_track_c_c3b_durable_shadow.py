"""Track C3b OFFLINE: durable metadata outbox, restart and crash chaos.

All test inputs are fake. The only persistent file has a deliberately
restricted name inside a new TemporaryDirectory. Neither LIVE SQLite nor
provider HTTP, broker, Myfxbook, Firestore or Oracle are ever contacted.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import track_c_c3b_durable_shadow as shadow
import cot_monitor as collector
from price_store import connect

NOW=datetime(2026,11,9,12,0,0,tzinfo=timezone.utc)
STAMP="2026-11-09T12:00:00Z"


def iso(instant):
    return instant.strftime("%Y-%m-%dT%H:%M:%SZ")


def meta(i=1,symbol="EURUSD",source="cot",seen=STAMP,commit=STAMP):
    return {"symbol":symbol,"source":source,"seenAtUtc":seen,
            "coreCommittedAtUtc":commit,"originalSha256":f"{i:064x}"}


class DurableShadowC3bTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix="remura-c3b-")
        self.path=Path(self.temp.name)/shadow.FILE
        self.assertEqual(shadow.prepare(self.path,mode=shadow.MODE),shadow.SCHEMA)

    def tearDown(self):
        self.temp.cleanup()

    def stage(self,metadata=None,**kw):
        return shadow.stage(
            self.path,meta() if metadata is None else metadata,
            at=STAMP,enabled=True,mode=shadow.MODE,**kw)

    def claim(self,at=STAMP):
        return shadow.claim(self.path,at=at,mode=shadow.MODE,enabled=True)

    def finish(self,job,at=STAMP,okay=True):
        return shadow.finish(self.path,item_id=job["id"],
                             lease_token=job["leaseToken"],at=at,
                             synthetic_worker_ok=okay,enabled=True,
                             mode=shadow.MODE)

    def summary(self):
        return shadow.inspect_lab(self.path,mode=shadow.MODE)

    def test_wal_persists_after_close_and_identity_cannot_be_edited(self):
        self.assertEqual(self.stage(),shadow.STAGED)
        self.assertEqual(self.summary()["pending"],1)
        db=sqlite3.connect(str(self.path))
        try:
            self.assertEqual(db.execute("PRAGMA journal_mode").fetchone()[0],"wal")
            rows=db.execute(f"SELECT * FROM {shadow.TABLE}").fetchall()
            self.assertEqual(len(rows),1)
            self.assertEqual(rows[0][1:5],("EURUSD","cot",STAMP,STAMP))
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "immutable_research_identity"):
                with db:
                    db.execute(f"UPDATE {shadow.TABLE} SET source='retail'")
            with self.assertRaisesRegex(sqlite3.IntegrityError,
                                         "append_only_no_delete"):
                with db:
                    db.execute(f"DELETE FROM {shadow.TABLE}")
        finally:
            db.close()
        self.assertEqual(self.summary()["pending"],1)
        safe=json.dumps(self.summary())
        for literal in ("EURUSD","099741","XAUUSD","broker",
                        "password",meta()["originalSha256"]):
            self.assertNotIn(literal,safe)
        self.assertFalse(self.summary()["realCollectorIsolationProven"])
        self.assertFalse(self.summary()["diskLimitIsHard"])

    def test_independent_python_process_claims_and_acks_after_restart(self):
        self.assertEqual(self.stage(),shadow.STAGED)
        # Independent interpreter, not a background promise. Explicit one-off
        # synthetic research worker process, NO core collector imports/calls.
        body="""import sys
import track_c_c3b_durable_shadow as s
path=sys.argv[1]
job=s.claim(path,at=sys.argv[2],enabled=True,mode=s.MODE)
assert job is not None
ans=s.finish(path,item_id=job['id'],lease_token=job['leaseToken'],
             at=sys.argv[2],synthetic_worker_ok=True,enabled=True,mode=s.MODE)
assert ans==s.ACKED
print('SYNTHETIC_OK')
"""
        env=dict(os.environ)
        env["PYTHONPATH"]=str(ROOT/"scripts")
        result=subprocess.run(
            [sys.executable,"-c",body,str(self.path),STAMP],
            capture_output=True,text=True,timeout=15,env=env,check=False)
        self.assertEqual(result.returncode,0,
                         "independent synthetic subprocess failed")
        self.assertEqual(result.stdout.strip(),"SYNTHETIC_OK")
        self.assertEqual(self.summary()["syntheticAck"],1)
        self.assertEqual(self.summary()["pending"],0)
        self.assertEqual(self.stage(),shadow.UNKNOWN)
        self.assertIsNone(self.claim())

    def test_simulated_worker_crash_expires_to_unknown_no_replay(self):
        self.assertEqual(self.stage(),shadow.STAGED)
        job=self.claim()
        self.assertIsNotNone(job)
        self.assertEqual(self.summary()["leased"],1)
        late=iso(NOW+timedelta(seconds=21))
        self.assertIsNone(self.claim(at=late))  # reclaimer after crash
        self.assertEqual(self.summary()["unknown"],1)
        self.assertEqual(self.finish(job,at=late),shadow.UNKNOWN)
        self.assertEqual(self.stage(),shadow.UNKNOWN)
        self.assertEqual(self.summary()["total"],1)

    def test_wrong_lease_and_double_ack_fail_closed(self):
        self.stage()
        job=self.claim()
        self.assertEqual(shadow.finish(
            self.path,item_id=job["id"],lease_token="0"*32,
            at=STAMP,synthetic_worker_ok=True,enabled=True,mode=shadow.MODE),
            shadow.UNKNOWN)
        self.assertEqual(self.summary()["leased"],1)
        self.assertEqual(self.finish(job),shadow.ACKED)
        self.assertEqual(self.finish(job),shadow.UNKNOWN)
        self.assertEqual(self.summary()["syntheticAck"],1)

    def test_worker_negative_ack_is_not_successful_research(self):
        self.stage()
        job=self.claim()
        self.assertEqual(self.finish(job,okay=False),shadow.UNKNOWN)
        self.assertEqual(self.summary()["unknown"],1)
        self.assertEqual(self.stage(),shadow.UNKNOWN)

    def test_very_late_worker_ack_is_unknown(self):
        self.stage()
        job=self.claim()
        late=iso(NOW+timedelta(minutes=4))
        self.assertEqual(self.finish(job,at=late),shadow.UNKNOWN)
        self.assertEqual(self.summary()["unknown"],1)

    def test_queue_pressure_is_bounded_and_older_is_not_replaced(self):
        for i in range(1,shadow.MAX_PENDING+1):
            self.assertEqual(self.stage(meta(i)),shadow.STAGED)
        self.assertEqual(self.stage(meta(99)),shadow.UNKNOWN)
        self.assertEqual(self.summary()["pending"],16)
        # Leased items still occupy the capacity until resolved.
        job=self.claim()
        self.assertEqual(self.stage(meta(99)),shadow.UNKNOWN)
        self.assertEqual(self.finish(job),shadow.ACKED)
        self.assertEqual(self.stage(meta(99)),shadow.STAGED)
        self.assertEqual(self.summary()["total"],17)
        self.assertEqual(self.summary()["pending"],16)

    def test_total_cap_is_persistent_across_restarts(self):
        with patch.object(shadow,"MAX_TOTAL",2):
            self.assertEqual(self.stage(meta(1)),shadow.STAGED)
            self.assertEqual(self.stage(meta(2)),shadow.STAGED)
            ticket=self.claim()
            self.assertEqual(self.finish(ticket),shadow.ACKED)
            self.assertEqual(self.stage(meta(3)),shadow.UNKNOWN)
            self.assertEqual(self.summary()["total"],2)

    def test_disabled_and_invalid_source_never_create_new_files(self):
        before=self.summary()["total"]
        for payload in (meta(symbol="GBPUSD"),meta(source="signal"),
                        meta(seen="2026-11-09T12:01:00Z"),
                        meta(seen="2026-11-09T11:56:00Z"),
                        meta(commit="2026-11-09T12:01:00Z"),
                        meta(commit="2026-11-09T11:59:00Z"),
                        meta()):
            payload=dict(payload)
            payload["account"]="SYNTHETIC_ID_SHOULD_NOT_ENTER_DISK"
            self.assertEqual(self.stage(payload),shadow.UNKNOWN)
        self.assertEqual(shadow.stage(
            self.path,meta(),at=STAMP,mode=shadow.MODE),
            shadow.UNKNOWN)
        self.assertIsNone(shadow.claim(self.path,at=STAMP,mode=shadow.MODE))
        self.assertEqual(self.summary()["total"],before)
        with self.assertRaisesRegex(ValueError,"explicit_offline"):
            shadow.stage(self.path,meta(),at=STAMP,enabled=True)

    def test_explicit_migration_only_and_no_live_file_path(self):
        other=Path(self.temp.name)/"not-a-research-sqlite.db"
        with self.assertRaisesRegex(ValueError,"only_dedicated_temp"):
            shadow.prepare(other,mode=shadow.MODE)
        with self.assertRaisesRegex(ValueError,"will_not_overwrite"):
            shadow.prepare(self.path,mode=shadow.MODE)
        with tempfile.TemporaryDirectory(prefix="remura-c3b-") as root:
            p=Path(root)/shadow.FILE
            self.assertEqual(shadow.stage(p,meta(),at=STAMP,
                                          enabled=True,mode=shadow.MODE),
                             shadow.UNKNOWN)
            self.assertFalse(p.exists())
        self.assertEqual(self.summary()["total"],0)

    def test_symlink_and_full_disk_guard_fail_closed(self):
        linked=Path(self.temp.name)/"remura-shadow-link"
        try:
            linked.symlink_to(self.path)
        except (OSError,NotImplementedError):
            self.skipTest("symlink unsupported")
        with self.assertRaises(ValueError):
            shadow.stage(linked,meta(),at=STAMP,mode=shadow.MODE,enabled=True)
        with patch.object(shadow,"MAX_MAIN_BYTES",0):
            self.assertEqual(self.stage(),shadow.UNKNOWN)
        self.assertEqual(self.summary()["total"],0)

    def test_shadow_database_lock_returns_unknown_core_continues(self):
        shadow_lock=sqlite3.connect(str(self.path),timeout=.025)
        core=Path(self.temp.name)/"core-cot-separate.sqlite3"
        try:
            shadow_lock.execute("BEGIN EXCLUSIVE")
            shadow_lock.execute("UPDATE c3b_schema_guard SET version=version")
            start=time.monotonic()
            self.assertEqual(self.stage(),shadow.UNKNOWN)
            elapsed=time.monotonic()-start
            self.assertLess(elapsed,2.0)
            calls=[]
            def local_fetch(dataset,now):
                calls.append(dataset)
                spec=collector.DATASETS[dataset]
                return [
                    {"report_date_as_yyyy_mm_dd":"2026-11-03T00:00:00",
                     "cftc_contract_market_code":code,
                     "open_interest_all":"1000",
                     **{k:"100" for k in spec["keys"]}}
                    for code in spec["codes"]
                ]
            with patch.object(collector,"utcnow",
                              side_effect=AssertionError("core_default_off")):
                result=collector.collect_once(core,now=NOW,fetch=local_fetch)
            self.assertEqual(result["errors"],{})
            self.assertEqual(result["saved"],{"tff":11,"disagg":3})
            self.assertEqual(calls,["tff","disagg"])
            db=connect(core)
            try:
                self.assertEqual(db.execute(
                    "SELECT count(*) FROM cot_reports").fetchone()[0],14)
            finally:
                db.close()
        finally:
            shadow_lock.rollback()
            shadow_lock.close()
        self.assertEqual(self.summary()["total"],0)

    def test_no_real_cost_proof_no_os_disk_quota_claim(self):
        out=self.summary()
        self.assertFalse(out["liveEnabled"])
        self.assertFalse(out["providerTimestampSigned"])
        self.assertFalse(out["actualEdgeEstablished"])
        self.assertFalse(out["realCrossDbAtomicity"])
        self.assertFalse(out["realCollectorIsolationProven"])
        self.assertEqual(out["newProviderCalls"],0)
        self.assertEqual(out["cvd"],"UNKNOWN")


if __name__=="__main__":
    unittest.main()
