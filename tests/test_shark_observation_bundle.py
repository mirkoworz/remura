"""Synthetic tests for combined future-only COT+price evidence in one transaction."""
from datetime import timedelta
import json
import sqlite3
import unittest

from scripts import shark_cot_asof_witness as witness
from scripts import shark_observation_bundle as bundle
from scripts import shark_price_asof_evidence as price
from test_shark_signal_evidence import fixture as cot_db_fixture
from test_shark_signal_evidence import insert_history,AT,NOW
from test_shark_price_asof_evidence import prepare as price_db_fixture

def create():
    db=cot_db_fixture()
    other=price_db_fixture()
    row=other.execute(
        "SELECT symbol,source,broker_symbol,updated_at,payload FROM prices"
    ).fetchone()
    other.close()
    db.execute("""CREATE TABLE prices(
        symbol TEXT PRIMARY KEY,source TEXT,broker_symbol TEXT,
        updated_at TEXT,payload TEXT)""")
    db.execute("INSERT INTO prices VALUES(?,?,?,?,?)",row)
    db.commit()
    price.ensure_schema(db)
    doc=json.loads(row[-1])
    return db,doc


class ObservationBundleTests(unittest.TestCase):
    def setUp(self):
        self.db,self.original_doc=create()

    def tearDown(self):
        self.db.close()

    def run_capture(self,*,doc=None,clock=NOW):
        with self.db:
            hid=insert_history(self.db)
            return bundle.record(
                self.db,history_id=hid,
                observed_document=self.original_doc if doc is None else doc,
                clock=clock)

    def test_both_proofs_as_of_same_original_observation(self):
        witness.witness(self.db,clock=AT)
        out=self.run_capture()
        self.assertEqual(out["state"],"BOTH_LOCAL_PROOFS_PRESENT")
        self.assertTrue(out["cotValueVersionMatched"])
        self.assertTrue(out["priceM15H1H4SourceVerified"])
        self.assertTrue(out["h1AndH4FreshAtObservation"])
        self.assertTrue(out["last16TickVolumeComplete"])
        self.assertFalse(out["cvdAggressorFlowMeasured"])
        self.assertFalse(out["priceSourceCollectionTimeIndependentlyKnown"])
        self.assertEqual(bundle.summary(self.db)["pairedEvidenceRows"],1)
        self.assertNotIn("PRIVATE_FAKE_BROKER_IDENTIFIER",json.dumps(out))
        self.assertNotIn("1.015",json.dumps(out))
        self.assertEqual(out["edge"],"NOT_ESTABLISHED")
        self.assertFalse(out["notificationsEnabled"])
        self.assertEqual(out["brokerCalls"],0)

    def test_absent_cot_proof_does_not_discard_real_price_observation(self):
        out=self.run_capture()
        self.assertEqual(out["state"],"PARTIAL_LOCAL_PROOFS")
        self.assertFalse(out["cotValueVersionMatched"])
        self.assertTrue(out["priceM15H1H4SourceVerified"])
        self.assertEqual(bundle.summary(self.db)["cotEvidenceRows"],0)
        self.assertEqual(bundle.summary(self.db)["priceEvidenceRows"],1)
        self.assertEqual(bundle.summary(self.db)["pairedEvidenceRows"],0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],1)

    def test_cot_proof_survives_stale_or_replaced_price_document(self):
        witness.witness(self.db,clock=AT)
        changed=json.loads(self.db.execute(
            "SELECT payload FROM prices").fetchone()[0])
        changed["timeframes"]["H1"][-1]["h"]=1.12
        self.db.execute("UPDATE prices SET payload=?",(json.dumps(changed),))
        self.db.commit()
        out=self.run_capture()
        self.assertEqual(out["state"],"PARTIAL_LOCAL_PROOFS")
        self.assertTrue(out["cotValueVersionMatched"])
        self.assertFalse(out["priceM15H1H4SourceVerified"])
        self.assertFalse(out["h1AndH4FreshAtObservation"])
        self.assertEqual(bundle.summary(self.db)["pairedEvidenceRows"],0)

    def test_no_proofs_cannot_be_misread_as_valid_signal(self):
        self.db.execute("DELETE FROM prices")
        self.db.commit()
        out=self.run_capture()
        self.assertEqual(out["state"],"NO_VERIFIABLE_LOCAL_PROOF")
        self.assertFalse(out["cotValueVersionMatched"])
        self.assertFalse(out["priceM15H1H4SourceVerified"])
        self.assertEqual(bundle.summary(self.db)["pairedEvidenceRows"],0)
        self.assertFalse(out["ordersEnabled"])

    def test_sqlite_error_on_second_proof_rolls_back_first_and_history(self):
        witness.witness(self.db,clock=AT)
        self.db.execute("DROP TABLE research_squalincome_price_evidence")
        self.db.commit()
        with self.assertRaises(sqlite3.OperationalError):
            self.run_capture()
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM squalincome_history").fetchone()[0],0)
        self.assertEqual(self.db.execute(
            "SELECT count(*) FROM research_squalincome_cot_links").fetchone()[0],0)

    def test_cannot_attach_to_previously_committed_row_or_after_another_insert(self):
        with self.db:
            hid=insert_history(self.db)
        with self.assertRaisesRegex(ValueError,"original_observation_transaction_required"):
            bundle.record(self.db,history_id=hid,
                          observed_document=self.original_doc,clock=NOW)
        with self.assertRaisesRegex(ValueError,"history_must_be_last_insert_before_recording"):
            with self.db:
                self.db.execute("CREATE TABLE IF NOT EXISTS extraneous (id INTEGER PRIMARY KEY)")
                self.db.execute("INSERT INTO extraneous VALUES(421)")
                bundle.record(self.db,history_id=hid,
                              observed_document=self.original_doc,clock=NOW)

    def test_late_clock_is_both_unknown_not_forged(self):
        witness.witness(self.db,clock=AT)
        out=self.run_capture(clock=NOW+timedelta(minutes=10))
        self.assertEqual(out["state"],"NO_VERIFIABLE_LOCAL_PROOF")
        self.assertEqual(bundle.summary(self.db)["pairedEvidenceRows"],0)


if __name__=="__main__":
    unittest.main()
