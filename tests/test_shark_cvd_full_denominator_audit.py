"""Disposable synthetic read-only FULL_34 to CVD PILOT provenance-census tests.

No real broker sources, prices, costs, market edge, production database,
Oracle, network or HMAC secrets. All timestamps are FUTURE synthetic fixtures.
"""
from __future__ import annotations

from datetime import datetime,timedelta,timezone
import hashlib
import json
import sqlite3
import unittest

from scripts import shark_cvd_full_denominator_audit as audit
from scripts import shark_cvd_scan_coverage as scan
from scripts import shark_cvd_source_lineage as lineage
from scripts import shark_price_only_compact as compact
from scripts import shark_price_only_universe as universe
from scripts import shark_cvd_incremental_protocol as protocol

UTC=timezone.utc
BASE=datetime(2026,11,9,10,0,0,tzinfo=UTC)
KEY=b"PRIVATE_SYNTHETIC_LONG_HMAC_KEY_NEVER_DEPLOY_ME"
FAKE="SYNTHETIC_PRIVATE_BROKER_123456"


def stamp(t):
    return t.isoformat(timespec="microseconds").replace("+00:00","Z")


def private_source_sha(sym):
    return hashlib.sha256(("synthetic-offline-"+sym+FAKE).encode()).hexdigest()


def price_rows(*,unavailable=()):
    row=[]
    for sym in protocol.FROZEN_UNIVERSE:
        missing=sym in unavailable
        row.append((
            sym,stamp(BASE),stamp(BASE+timedelta(minutes=1)),
            stamp(BASE+timedelta(minutes=1,seconds=2)),
            "PRICE_UNIVERSE_NOT_RECORDED" if missing else "PRICE_CONTEXT_READY",
            "missing" if missing else "verified",
            "missing" if missing else "recent",
            None if missing else stamp(BASE),
            0 if missing else 1,
            None if missing else "confirmed",
            0 if missing else 1,0 if missing else 1,0 if missing else 1,
            None if missing else private_source_sha(sym),
            0 if missing else 1,
            universe.ALGORITHM,
        ))
    return row


def fixture(*,price=True,cvd=True,zero=True,late=False,mismatch=False,
            unknown_market=None,only_one=False,not_evaluable=False):
    p=sqlite3.connect(":memory:")
    c=sqlite3.connect(":memory:")
    if price:
        compact.ensure_schema(p)
        with p:
            p.execute("BEGIN")
            compact.seal(p,price_rows(unavailable=(unknown_market,) if unknown_market else ()),
                         full=True,clock=BASE+timedelta(minutes=1,seconds=3))
    if cvd:
        scan.ensure_schema(c)
        for sym in ("EURUSD",) if only_one else ("EURUSD","XAUUSD"):
            sha=private_source_sha(sym)
            c.execute(f"""INSERT INTO {scan.TABLE}
                (symbol,closed_at,attempted_at,state,source_hmac,
                 session_prefix_hmac,new_confirmations,reason,schema_version)
                VALUES (?,?,?,?,?,?,?,?,?)""",(
                sym,stamp(BASE),stamp(BASE+timedelta(minutes=1,seconds=1)
                                     if late and sym=="EURUSD" else
                                     BASE+timedelta(seconds=30)),
                "NOT_EVALUABLE" if not_evaluable and sym=="EURUSD" else "EVALUATED",
                None if not_evaluable and sym=="EURUSD" else
                   lineage._mac(KEY,("b"*64) if mismatch and sym=="EURUSD" else sha),
                None,
                None if not_evaluable and sym=="EURUSD" else
                    (0 if zero or sym=="XAUUSD" else 2),
                "SOURCE_ABSENT" if not_evaluable and sym=="EURUSD" else "DETECTOR_OK",
                scan.SCHEMA))
        c.commit()
    return p,c


def run(p,c,**kwargs):
    p.execute("PRAGMA query_only=ON")
    c.execute("PRAGMA query_only=ON")
    return audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                       days=1,secret=KEY,**kwargs)


class FullDenominatorAuditTests(unittest.TestCase):

    def test_frozen_34_and_two_pilot_markets_not_confused(self):
        self.assertEqual(len(protocol.FROZEN_UNIVERSE),34)
        self.assertEqual(set(scan.PILOT),{"EURUSD","XAUUSD"})
        self.assertEqual(set(scan.PILOT)&set(protocol.FROZEN_UNIVERSE),
                         set(scan.PILOT))
        p,c=fixture(zero=False)
        try:
            out=run(p,c)
            self.assertEqual(out["status"],
                             "PILOT_CVD_COVERAGE_AUDITED_NOT_FULL_34_GO")
            self.assertEqual(out["full34Batches"],1)
            self.assertEqual(out["full34MarketCells"],34)
            self.assertEqual(out["full34PriceReadyCells"],34)
            self.assertEqual(out["full34PriceOtherOrUnknownCells"],0)
            self.assertEqual(out["readyCellsOutsideExistingCvdPilot"],32)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],2)
            self.assertEqual(out["pilotMatchedZeroNewLocalConfirmations"],1)
            self.assertEqual(out["pilotMatchedNewTechnicalConfirmations"],1)
            self.assertEqual(out["genuineFull34CvdNegativeControlsAdmitted"],0)
            self.assertFalse(out["complete34MarketCvdCaptureEstablished"])
            self.assertFalse(out["localZeroNewConfirmationIsCertifiedNoCvd"])
            self.assertFalse(out["localPositiveCountEstablishesDirectionalCvd"])
            self.assertFalse(out["cotRetailAsOfCausalJoinEstablished"])
            self.assertFalse(out["futureOutcomeAndActualTradingCostsEstablished"])
            self.assertFalse(out["profitabilityOrStatisticalEdgeEstablished"])
            self.assertFalse(out["canEnableCvdResearch"])
            self.assertEqual(out["newCollectorOrBrokerCalls"],0)
            self.assertFalse(out["writesPerformed"])
            self.assertNotIn(FAKE,json.dumps(out))
            self.assertNotIn("EURUSD",json.dumps(out))
            self.assertEqual(p.execute("PRAGMA query_only").fetchone()[0],1)
            self.assertEqual(c.execute("PRAGMA query_only").fetchone()[0],1)
        finally:
            p.close();c.close()

    def test_v2_missed_scan_is_unknown_not_negative(self):
        p,c=fixture(only_one=True)
        try:
            out=run(p,c)
            self.assertEqual(out["pilotReadyCellsWithMissingScan"],1)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],1)
            self.assertEqual(out["genuineFull34CvdNegativeControlsAdmitted"],0)
        finally:
            p.close();c.close()

    def test_scan_ledger_absent_is_not_fake_zero(self):
        p,c=fixture(cvd=False)
        try:
            out=run(p,c)
            self.assertEqual(out["status"],"RESEARCH_LEDGER_UNAVAILABLE")
            self.assertTrue(out["priceLedgerPresent"])
            self.assertFalse(out["privateCvdLedgerPresent"])
            self.assertEqual(out["full34Batches"],0)
            self.assertFalse(out["canEnableCvdResearch"])
        finally:
            p.close();c.close()

    def test_price_batch_absent_is_unknown_even_with_private_scans(self):
        p,c=fixture(price=False)
        try:
            out=run(p,c)
            self.assertEqual(out["status"],"RESEARCH_LEDGER_UNAVAILABLE")
            self.assertFalse(out["priceLedgerPresent"])
            self.assertTrue(out["privateCvdLedgerPresent"])
        finally:
            p.close();c.close()

    def test_research_not_yet_started_prior_to_nov9(self):
        p,c=fixture()
        try:
            p.execute("PRAGMA query_only=ON")
            c.execute("PRAGMA query_only=ON")
            out=audit.audit(p,c,as_of="2026-11-06T16:00:00Z",
                            days=1,secret=KEY)
            self.assertEqual(out["status"],"NOT_YET_IN_PROSPECTIVE_WINDOW")
            self.assertEqual(out["full34Batches"],0)
            self.assertEqual(out["genuineFull34CvdNegativeControlsAdmitted"],0)
        finally:
            p.close();c.close()

    def test_hmac_source_mismatch_not_valid_cvd_overlap(self):
        p,c=fixture(mismatch=True)
        try:
            out=run(p,c)
            self.assertEqual(out["pilotReadyCellsWithDifferentSource"],1)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],1)
            self.assertEqual(out["pilotMatchedZeroNewLocalConfirmations"],1)
        finally:
            p.close();c.close()

    def test_synthetic_late_after_price_decision_is_not_retroactive(self):
        p,c=fixture(late=True)
        try:
            out=run(p,c)
            self.assertEqual(out["pilotReadyCellsWithLateOrFutureScan"],1)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],1)
            self.assertEqual(out["genuineFull34CvdNegativeControlsAdmitted"],0)
        finally:
            p.close();c.close()

    def test_not_evaluable_explicit_attempt_never_negative(self):
        p,c=fixture(not_evaluable=True)
        try:
            out=run(p,c)
            self.assertEqual(out["pilotReadyCellsWithUnusableScan"],1)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],1)
            self.assertEqual(out["pilotMatchedZeroNewLocalConfirmations"],1)
        finally:
            p.close();c.close()

    def test_missing_original_price_row_keeps_34_denominator(self):
        p,c=fixture(unknown_market="EURUSD")
        try:
            out=run(p,c)
            self.assertEqual(out["full34MarketCells"],34)
            self.assertEqual(out["full34PriceReadyCells"],33)
            self.assertEqual(out["full34PriceOtherOrUnknownCells"],1)
            self.assertEqual(out["readyCellsOutsideExistingCvdPilot"],32)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],1)
        finally:
            p.close();c.close()

    def test_empty_price_batch_table_does_not_create_evidence(self):
        p,c=fixture()
        try:
            p.execute(f"DELETE FROM {compact.TABLE}") # guarded by append-only trigger
        except sqlite3.DatabaseError:
            pass
        else:
            self.fail("immutable full batch was unexpectedly deletable")
        try:
            out=run(p,c)
            self.assertEqual(out["full34Batches"],1)
        finally:
            p.close();c.close()

    def test_query_only_required_and_no_foreign_implicit_live_access(self):
        p,c=fixture()
        try:
            with self.assertRaisesRegex(ValueError,"query_only"):
                audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                            secret=KEY)
            p.execute("PRAGMA query_only=ON")
            with self.assertRaisesRegex(ValueError,"query_only"):
                audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                            secret=KEY)
            c.execute("PRAGMA query_only=ON")
            with self.assertRaisesRegex(ValueError,"independent_research_dbs_required"):
                audit.audit(p,p,as_of=stamp(BASE+timedelta(minutes=5)),
                            secret=KEY)
            self.assertEqual(run(p,c)["full34Batches"],1)
        finally:
            p.close();c.close()

    def test_wrong_key_makes_all_sources_unknown(self):
        p,c=fixture()
        try:
            p.execute("PRAGMA query_only=ON")
            c.execute("PRAGMA query_only=ON")
            out=audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                            secret=b"THIS_IS_NOT_THE_STABLE_CVD_BINDING_KEY")
            self.assertEqual(out["pilotReadyCellsWithDifferentSource"],2)
            self.assertEqual(out["pilotReadyCellsWithSameDocumentLocalEvaluation"],0)
            self.assertFalse(out["canEnableCvdResearch"])
        finally:
            p.close();c.close()

    def test_corrupted_full_price_payload_sha_aborts_without_fabricating(self):
        p,c=fixture()
        try:
            p.execute("DROP TRIGGER research_compact_no_update")
            p.execute(f"UPDATE {compact.TABLE} SET payload_sha256=?",
                      ("f"*64,))
            p.execute("CREATE TRIGGER research_compact_no_update "
                      f"BEFORE UPDATE ON {compact.TABLE} "
                      "BEGIN SELECT RAISE(ABORT,'immutable_scan_batch'); END")
            p.commit()
            with self.assertRaisesRegex(ValueError,
                                         "archive_integrity_failed"):
                run(p,c)
        finally:
            p.close();c.close()

    def test_protected_database_guard_cannot_be_bypassed(self):
        p,c=fixture()
        try:
            p.execute("DROP TRIGGER research_compact_no_update")
            p.commit()
            with self.assertRaisesRegex(ValueError,
                                         "missing_research_immutable_triggers"):
                run(p,c)
        finally:
            p.close();c.close()

    def test_corrupt_scan_or_future_observation_fails_closed(self):
        p,c=fixture()
        try:
            c.execute("DROP TRIGGER research_cvd_scan_no_update")
            c.execute(f"UPDATE {scan.TABLE} SET attempted_at=? WHERE symbol=?",
                      (stamp(BASE+timedelta(minutes=4)),"EURUSD"))
            c.execute("CREATE TRIGGER research_cvd_scan_no_update "
                      f"BEFORE UPDATE ON {scan.TABLE} "
                      "BEGIN SELECT RAISE(ABORT,'immutable_cvd_attempt'); END")
            c.commit()
            with self.assertRaisesRegex(ValueError,
                                         "cvd_attempt_schema_or_clock_invalid"):
                run(p,c)
        finally:
            p.close();c.close()

    def test_bounded_days_and_valid_secret(self):
        p,c=fixture()
        try:
            p.execute("PRAGMA query_only=ON")
            c.execute("PRAGMA query_only=ON")
            for bad in (0,8,True,2.3):
                with self.assertRaises(ValueError):
                    audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                                days=bad,secret=KEY)
            with self.assertRaises(ValueError):
                audit.audit(p,c,as_of=stamp(BASE+timedelta(minutes=5)),
                            secret=b"short")
        finally:
            p.close();c.close()


if __name__=="__main__":
    unittest.main()
