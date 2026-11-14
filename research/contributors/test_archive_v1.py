# REMURA Contributors v0.4 LAB — 14/11/2026 23:32 CET
import os
import tempfile
import unittest
from pathlib import Path
from uuid import UUID
from archive_v1 import Archive,CatalogEntry,FILENAME
from ledger_v1 import Principal

NOW="2026-11-14T22:32:00Z"
LATER="2026-11-14T22:33:00Z"
LATEST="2026-11-14T22:34:00Z"
E=CatalogEntry("NAS100","PEPPERSTONE","NAS100","CFD","","lab-common")
F=CatalogEntry("NAS100","LABCME","NQZ6","FUTURE","2026-12","lab-future")
A=Principal("friend-a","CONTRIBUTOR")
B=Principal("friend-b","CONTRIBUTOR")
O=Principal("owner","OWNER")

class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name).resolve()
        self.config=dict(catalog=[E,F],contributors=["friend-a","friend-b"],owners=["owner"],synthetic=True)
        self.db=Archive(self.root,**self.config)
        self.p=dict(request_id=str(UUID(int=1)),market=E.market,provider=E.provider,ticker=E.ticker,
                    product=E.product,contract=E.contract,period="WEEK",kind="DELTA_PEAK",price="21000.50",
                    anchor_utc="2026-11-09T00:00:00Z",observed_utc="2026-11-14T20:00:00Z",note="synthetic")
    def tearDown(self):
        self.db.close()
        self.temp.cleanup()
    def submit(self,actor=A,**changes):
        return self.db.submit(actor,dict(self.p,**changes),received_utc=NOW)
    def test_persistence(self):
        self.submit()
        self.db.review(O,1,"APPROVED",at_utc=LATER,reason="checked example")
        self.db.close()
        self.db=Archive(self.root,**self.config)
        self.assertEqual(self.db.receipts(A)[0]["status"],"APPROVED")
        self.assertEqual(len(self.db.queue(O)[0]["history"]),1)
        self.assertEqual((self.root/FILENAME).stat().st_mode & 0o777,0o600)
    def test_review_and_revocation(self):
        self.submit()
        self.assertFalse(self.db.review(O,1,"APPROVED",at_utc=LATER,reason="checked")["scientific_admission"])
        self.db.review(O,1,"REVOKED",at_utc=LATEST,reason="correction")
        row=self.db.queue(O)[0]
        self.assertEqual([x["action"] for x in row["history"]],["APPROVED","REVOKED"])
        self.assertEqual(row["data"]["price"],"21000.5")
        self.assertEqual(self.submit()["status"],"REVOKED")
        with self.assertRaises(ValueError):self.db.review(O,1,"APPROVED",at_utc=LATEST,reason="again")
    def test_rejection(self):
        self.submit()
        self.db.review(O,1,"REJECTED",at_utc=LATER,reason="unverified")
        self.assertEqual(self.db.receipts(A)[0]["status"],"REJECTED")
        with self.assertRaises(ValueError):self.db.review(O,1,"APPROVED",at_utc=LATEST,reason="again")
    def test_role_isolation(self):
        self.submit()
        self.submit(B)
        self.assertEqual(len(self.db.receipts(A)),1)
        self.assertEqual(len(self.db.receipts(B)),1)
        self.assertNotIn("subject",self.db.receipts(A)[0])
        self.assertNotIn("history",self.db.receipts(B)[0])
        self.assertEqual(len(self.db.queue(O)),2)
        for actor in (A,Principal("friend-a","OWNER"),Principal("unknown","OWNER")):
            with self.assertRaises(PermissionError):self.db.queue(actor)
            with self.assertRaises(PermissionError):self.db.review(actor,1,"APPROVED",at_utc=LATER,reason="fake")
        with self.assertRaises(PermissionError):self.submit(O)
    def test_mapping_and_contract(self):
        for change in ({"provider":"CAPITALCOM"},{"ticker":"SPX500"},{"product":"SPOT"},{"contract":"2026-12"},{"market":"EURUSD"}):
            with self.assertRaises(ValueError):self.submit(**change)
        self.submit(provider=F.provider,ticker=F.ticker,product=F.product,contract=F.contract)
        self.assertEqual(self.db.receipts(A)[0]["data"]["contract"],"2026-12")
    def test_duplicate_and_conflict(self):
        self.submit()
        self.assertTrue(self.submit(price="21000.500")["duplicate"])
        with self.assertRaises(ValueError):self.submit(price="21001")
        with self.assertRaises(ValueError):self.submit(request_id=str(UUID(int=2)),note="different note")
    def test_time_and_validation(self):
        for change in ({"observed_utc":LATEST},{"anchor_utc":LATEST},{"price":"NaN"},{"note":"a\nb"},
                       {"status":"APPROVED"},{"request_id":"bad"},{"period":"YEAR"}):
            with self.assertRaises(ValueError):self.submit(**change)
        self.submit()
        with self.assertRaises(ValueError):self.db.review(O,1,"APPROVED",at_utc="2026-11-14T20:00:00Z",reason="checked")
        with self.assertRaises(ValueError):self.db.review(O,1,"APPROVED",at_utc=LATER,reason="")
    def test_mapping_change_blocks_approval(self):
        self.submit()
        self.db.close()
        self.config["catalog"]=[CatalogEntry(E.market,E.provider,E.ticker,E.product,E.contract,"changed-source")]
        self.db=Archive(self.root,**self.config)
        with self.assertRaises(ValueError):self.db.review(O,1,"APPROVED",at_utc=LATER,reason="checked")
    def test_immutable_tables(self):
        self.submit()
        self.db.review(O,1,"APPROVED",at_utc=LATER,reason="checked")
        import sqlite3
        for sql in ("UPDATE entries SET subject='wrong'","DELETE FROM entries","UPDATE reviews SET reason='wrong'","DELETE FROM reviews"):
            with self.assertRaises(sqlite3.IntegrityError):self.db.db.execute(sql)
    def test_daily_limit(self):
        for i in range(20):self.submit(request_id=str(UUID(int=i+1)),price=str(21000+i))
        with self.assertRaises(ValueError):self.submit(request_id=str(UUID(int=21)),price="22000")
        self.assertTrue(self.submit(price="21000")["duplicate"])
    def test_explicit_and_private(self):
        with self.assertRaises(ValueError):Archive(self.root,**dict(self.config,synthetic=False))
        self.root.chmod(0o755)
        try:
            with self.assertRaises(ValueError):Archive(self.root,**self.config)
        finally:self.root.chmod(0o700)
    def test_no_other_db(self):
        import sqlite3
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/FILENAME
            with sqlite3.connect(p) as db:db.execute("CREATE TABLE unrelated(x)")
            p.chmod(0o600)
            with self.assertRaises(ValueError):Archive(Path(d).resolve(),**self.config)
            with sqlite3.connect(p) as db:self.assertIsNotNone(db.execute("SELECT name FROM sqlite_master WHERE name='unrelated'").fetchone())
    def test_symlink(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d)/FILENAME).symlink_to(self.root/FILENAME)
            with self.assertRaises(ValueError):Archive(Path(d).resolve(),**self.config)
if __name__=="__main__":
    unittest.main()
