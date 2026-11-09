"""Track B synthetic 14 x 14-day capacity and read-only rollover tests."""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import copy
import sqlite3
import unittest

from scripts import shark_retail_segment_readiness as segment
from scripts import shark_retail_first_seen as retail
from scripts import shark_retail_numeric_features as numeric
from test_shark_retail_receipt_handoff import original_pair

UTC=timezone.utc
AUTHORIZED=datetime(2026,11,9,10,0,tzinfo=UTC)


def make_pair(timestamp):
    source=original_pair()
    updated=timestamp-timedelta(minutes=3)
    stamp=updated.isoformat().replace("+00:00","Z")
    source["updatedAt"]=stamp
    for market in ("EURUSD","XAUUSD"):
        source["symbols"][market]["t"]=stamp
    return source


class RetailSegmentReadinessTests(unittest.TestCase):
    def setUp(self):
        self.plan=segment.plan(AUTHORIZED)
        self.dbs=[]
        for _ in range(14):
            db=sqlite3.connect(":memory:")
            retail.ensure_schema(db)
            numeric.ensure_schema(db)
            self.dbs.append(db)

    def tearDown(self):
        for db in self.dbs:
            db.close()

    def t(self,i):
        return datetime.fromisoformat(
            self.plan["segments"][i]["startUtc"].replace("Z","+00:00"))

    def pair(self,i,when):
        db=self.dbs[i]
        db.execute("PRAGMA query_only=OFF")
        retail.capture_pair(
            db,original_snapshot=make_pair(when),
            file_read_at=when-timedelta(seconds=5),clock=when,
            research_numeric_features=True)

    def inspect(self):
        for db in self.dbs:
            db.execute("PRAGMA query_only=ON")
        try:
            return segment.audit_shards(AUTHORIZED,self.dbs)
        finally:
            for db in self.dbs:
                db.execute("PRAGMA query_only=OFF")

    def test_frozen_fold_layout_is_6_4_4_with_14_contiguous_shards(self):
        p=self.plan
        self.assertEqual(p["status"],
                         "OFFLINE_CAPACITY_LAYOUT_PLAUSIBLE_NOT_LIVE_GO")
        self.assertEqual(len(p["segments"]),14)
        self.assertEqual([x["fold"] for x in p["segments"]],
                         ["train"]*6+["validation"]*4+["test"]*4)
        self.assertEqual(p["scenarioAllSegmentsRows"],28224)
        self.assertEqual(p["segments"][0]["scenarioTwoMarketRows"],2016)
        self.assertEqual(p["segments"][0]["numericHeadroomRows"],2484)
        self.assertTrue(p["crossDatabaseSqualincomeAtomicLinkMissing"])
        self.assertFalse(p["liveAuthorized"])
        for a,b in zip(p["segments"],p["segments"][1:]):
            self.assertEqual(a["endExclusiveUtc"],b["startUtc"])

    def test_10_minute_scenario_fits_but_8_minute_scenario_fails(self):
        ten=segment.plan(AUTHORIZED,scenario_cycle_minutes=10)
        eight=segment.plan(AUTHORIZED,scenario_cycle_minutes=8)
        self.assertEqual(ten["segments"][0]["scenarioTwoMarketRows"],4032)
        self.assertEqual(eight["segments"][0]["scenarioTwoMarketRows"],5040)
        self.assertEqual(eight["status"],"NO_GO_SEGMENT_SCENARIO_EXCEEDS_HARD_CAP")
        self.assertFalse(ten["liveAuthorized"])
        self.assertFalse(eight["liveAuthorized"])

    def test_without_hypothetical_authorization_remains_blocked(self):
        blocked=segment.plan()
        self.assertEqual(blocked["status"],"BLOCKED_NO_AUTHORIZED_RETAIL_START")
        self.assertEqual(blocked["segments"],[])
        self.assertFalse(blocked["retailFirstSeenActivated"])

    def test_real_capture_pair_in_two_separate_sqlite_shards_and_global_readonly_audit(self):
        self.pair(0,self.t(0)+timedelta(minutes=3))
        self.pair(1,self.t(1)+timedelta(minutes=3))
        changes=[db.total_changes for db in self.dbs]
        report=self.inspect()
        self.assertEqual([db.total_changes for db in self.dbs],changes)
        self.assertEqual(report["locallyRevalidatedRetailReceipts"],4)
        self.assertEqual(report["locallyRevalidatedNumericRows"],4)
        self.assertEqual(report["populatedShardCount"],2)
        self.assertFalse(report["complete28WeekEnrollmentProven"])
        self.assertFalse(report["crossDatabaseAtomicSignalLinkProven"])

    def test_cross_shard_backdated_original_cannot_be_silently_accepted(self):
        earlier=self.t(1)-timedelta(minutes=2)
        self.pair(0,earlier)
        self.pair(1,self.t(1)+timedelta(seconds=1))
        # Both were independently valid inserts in their local DBs; the
        # second source timestamp is later, so this SHOULD pass.
        self.assertEqual(self.inspect()["locallyRevalidatedRetailReceipts"],4)
        # Now change the source timestamp inside the second shard after
        # temporarily disabling its append-only trigger in disposable test.
        db=self.dbs[1]
        db.execute("DROP TRIGGER research_retail_first_update")
        db.execute(f"UPDATE {retail.TABLE} SET source_updated_at=?",
                   ((earlier-timedelta(minutes=1)).isoformat(),))
        db.commit()
        with self.assertRaisesRegex(ValueError,"backdated_receipt"):
            self.inspect()

    def test_partial_pair_is_fail_closed(self):
        self.pair(0,self.t(0)+timedelta(minutes=3))
        db=self.dbs[0]
        db.execute("DROP TRIGGER research_retail_first_delete")
        db.execute(f"DELETE FROM {retail.TABLE} WHERE symbol='XAUUSD'")
        db.execute("DROP TRIGGER research_retail_features_no_delete")
        db.execute(f"DELETE FROM {numeric.TABLE} WHERE symbol='XAUUSD'")
        db.commit()
        with self.assertRaisesRegex(ValueError,"partial_pair"):
            self.inspect()

    def test_unbound_or_modified_numeric_values_are_not_certified(self):
        self.pair(0,self.t(0)+timedelta(minutes=3))
        db=self.dbs[0]
        db.execute("DROP TRIGGER research_retail_features_no_update")
        db.execute(f"UPDATE {numeric.TABLE} SET long_pct=71 WHERE symbol='EURUSD'")
        db.commit()
        with self.assertRaisesRegex(ValueError,"numeric_sha256"):
            self.inspect()

    def test_requires_all_fourteen_clean_readonly_schemas(self):
        with self.assertRaisesRegex(ValueError,"fourteen_explicit"):
            segment.audit_shards(AUTHORIZED,self.dbs[:2])
        with self.assertRaisesRegex(ValueError,"readonly_clean"):
            segment.audit_shards(AUTHORIZED,self.dbs)
        for db in self.dbs:
            db.execute("PRAGMA query_only=ON")
        self.dbs[0].execute("PRAGMA query_only=OFF")
        with self.assertRaisesRegex(ValueError,"readonly_clean"):
            segment.audit_shards(AUTHORIZED,self.dbs)

    def test_invalid_cycle_and_timestamps_fail_closed(self):
        for cycle in (False,0,-1,121,1.5,"20"):
            with self.subTest(cycle=cycle):
                with self.assertRaises(ValueError):
                    segment.plan(AUTHORIZED,scenario_cycle_minutes=cycle)
        for bad in ("", "2026-11-09T01:00:00", "2026-11-09T01:00:00+01:00"):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    segment._time(bad)


if __name__=="__main__":
    unittest.main()
