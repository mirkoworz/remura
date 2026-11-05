"""Synthetic-only tests for atomic private CVD source binding.

No private broker access, no REMURA live database, no actual COT/CVD edge.
The exact detector is rerun on the in-memory source; the only persisted
document identity is a private keyed HMAC.
"""
from __future__ import annotations

from datetime import timedelta
import json
import sqlite3
import unittest
from unittest.mock import patch

from scripts import shark_cvd_ledger as ledger
from scripts import shark_cvd_source_lineage as lineage
from test_shark_cvd_ledger import (
    COLLECTED, NOW, QUALITY, SECRET, START, event,
)


def source_document(ev):
    # Same synthetic 25-bar day used in detector fixture, plus 56 prior
    # closed bars to satisfy the original M15 source-length contract.
    frames=[]
    for i in range(-56,25):
        t=START+timedelta(minutes=i*15)
        low=10.0 if i==10 else (9.7 if i==22 else 10.4)
        frames.append({
            "t":t.isoformat().replace("+00:00","Z"),
            "o":10.8,"h":11.2,"l":low,"c":11.0,"v":100,
        })
    return {
        "symbol":ev["symbol"],"provider":"ctrader",
        "providerSymbol":ev["providerSymbol"],"timezone":"UTC",
        "sourceTimeframe":"M15","lastComplete":frames[-1]["t"],
        "timeframes":{"M15":frames,"H1":[],"H4":[]},
    }


class CVDSourceBindingTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        ledger.ensure_schema(self.db)
        self.ev=event()
        self.doc=source_document(self.ev)

    def tearDown(self):
        self.db.close()

    def _save(self,doc=None,ev=None):
        return ledger.append(
            self.db, self.ev if ev is None else ev, QUALITY,
            source_collected_at=COLLECTED,hmac_secret=SECRET,
            now=NOW,source_document=self.doc if doc is None else doc)

    def _key(self):
        return self.db.execute(
            "SELECT key FROM research_cvd_observations").fetchone()[0]

    def _match(self,sha=None,obs=None,at=None,secret=SECRET):
        return lineage.match(
            self.db,event_key=self._key(),
            original_price_sha=sha or lineage._document_sha(self.doc),
            observed_at=(obs or NOW+timedelta(minutes=5)).isoformat().replace(
                "+00:00","Z"),
            as_of=(at or NOW+timedelta(minutes=10)).isoformat().replace(
                "+00:00","Z"),secret=secret)

    def test_verified_original_detector_replay_and_hmac_match(self):
        out=self._save()
        self.assertEqual(out["state"],"RECORDED")
        self.assertTrue(out["sourceDocumentBound"])
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM research_cvd_observations").fetchone()[0],1)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {lineage.TABLE}").fetchone()[0],1)
        self.assertEqual(self._match()["state"],
                         "EXACT_LOCAL_SOURCE_AND_CHRONOLOGY")
        self.assertTrue(self._match()["sourceMatch"])
        self.assertTrue(self._match()["causal"])
        self.assertFalse(self._match()["tradingEdgeEstablished"])
        self.assertFalse(self._match()["cvdAggressorFlowMeasured"])
        stored="\n".join(self.db.iterdump())
        self.assertNotIn(self.ev["providerSymbol"],stored)
        self.assertNotIn(self.ev["id"],stored)
        self.assertNotIn(lineage._document_sha(self.doc),stored)
        self.assertNotIn('"o":',stored)
        self.assertNotIn("10.8",stored)
        self.assertNotIn(self.ev["id"],json.dumps(out))

    def test_wrong_source_digest_key_or_chronology_is_not_a_causal_join(self):
        self._save()
        wrong="0"*64
        self.assertFalse(self._match(sha=wrong)["sourceMatch"])
        self.assertEqual(self._match(sha=wrong)["state"],
                         "NOT_SAME_SOURCE_OR_NOT_CAUSAL")
        self.assertFalse(self._match(secret=b"different-key-30-bytes-long!!!")[
            "sourceMatch"])
        self.assertFalse(self._match(obs=NOW-timedelta(minutes=1))["causal"])
        self.assertFalse(self._match(at=NOW-timedelta(minutes=1))["causal"])
        self.assertFalse(self._match(obs=NOW+timedelta(minutes=91),
                                     at=NOW+timedelta(minutes=92))["causal"])

    def test_mutated_ohlc_event_and_mapping_cannot_gain_source_proof(self):
        wrong=json.loads(json.dumps(self.doc))
        wrong["timeframes"]["M15"][-1]["v"]=0
        with self.assertRaisesRegex(ValueError,"not_reproduced"):
            self._save(doc=wrong)
        wrong=json.loads(json.dumps(self.doc))
        wrong["providerSymbol"]="WRONG_BROKER"
        with self.assertRaisesRegex(ValueError,"mapping_mismatch"):
            self._save(doc=wrong)
        wrong=json.loads(json.dumps(self.doc))
        wrong["lastComplete"]=wrong["timeframes"]["M15"][-2]["t"]
        with self.assertRaisesRegex(ValueError,"source_last_closed"):
            self._save(doc=wrong)
        self.assertEqual(ledger.aggregate(self.db)["events"],0)
        self.assertEqual(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name=?",
            (lineage.TABLE,)).fetchone(),None)

    def test_old_unbound_event_is_not_retroactively_qualified(self):
        out=ledger.append(
            self.db,self.ev,QUALITY,source_collected_at=COLLECTED,
            hmac_secret=SECRET,now=NOW)
        self.assertEqual(out["state"],"RECORDED")
        with self.assertRaisesRegex(ValueError,"cannot_gain_later"):
            self._save()
        self.assertEqual(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name=?",
            (lineage.TABLE,)).fetchone(),None)
        m=self._match()
        self.assertEqual(m["state"],"NO_SOURCE_BINDINGS")
        self.assertFalse(m["sourceMatch"])

    def test_duplicate_bound_event_cannot_rewrite_original_proof(self):
        self._save()
        before=self.db.total_changes
        with self.assertRaisesRegex(ValueError,"cannot_gain_later"):
            self._save()
        self.assertEqual(self.db.total_changes,before)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {lineage.TABLE}").fetchone()[0],1)
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(f"UPDATE {lineage.TABLE} SET bound_at='2020'")
        with self.assertRaises(sqlite3.IntegrityError):
            self.db.execute(f"DELETE FROM {lineage.TABLE}")

    def test_unbound_legacy_ledger_does_not_import_binding_or_write_schema(self):
        out=ledger.append(
            self.db,self.ev,QUALITY,source_collected_at=COLLECTED,
            hmac_secret=SECRET,now=NOW)
        self.assertEqual(out["state"],"RECORDED")
        self.assertFalse(out["sourceDocumentBound"])
        self.assertEqual(self.db.execute(
            "SELECT name FROM sqlite_master WHERE name=?",
            (lineage.TABLE,)).fetchone(),None)

    def test_rollback_both_event_and_source_when_private_binding_fails(self):
        with patch.object(lineage,"insert",
                          side_effect=sqlite3.OperationalError("synthetic_sqlite")):
            with self.assertRaisesRegex(sqlite3.OperationalError,
                                        "synthetic_sqlite"):
                self._save()
        self.assertEqual(ledger.aggregate(self.db)["events"],0)
        self.assertEqual(self.db.execute(
            f"SELECT count(*) FROM {lineage.TABLE}").fetchone()[0],0)

    def test_tampered_trigger_is_detected_and_no_secret_leaked(self):
        self._save()
        self.db.execute(f"DROP TRIGGER {lineage.TRIGGERS[0]}")
        with self.assertRaisesRegex(ValueError,"triggers_missing"):
            self._match()
        with self.assertRaises(ValueError):
            lineage._mac(b"short","0"*64)
        with self.assertRaises(ValueError):
            lineage._mac(SECRET,"BAD_SHA")

if __name__=="__main__":
    unittest.main()
