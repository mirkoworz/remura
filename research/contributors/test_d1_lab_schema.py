# REMURA Contributors v0.16 LAB — 14/11/2026 23:56 CET
import re
import sqlite3
import subprocess
import unittest
from pathlib import Path
from uuid import UUID

ROOT=Path(__file__).parent
SCHEMA=(ROOT/"d1_lab_schema.sql").read_text()
SQL=dict(re.findall(r'^\s*(gate|existing|insert|receipts):"([^"]+)"', (ROOT/"d1_lab_adapter.mjs").read_text(),re.M))
A="fixture-a";B="fixture-b";KEY=("EURUSD","OANDA","EURUSD","SPOT","")
T="2026-11-14T22:56:00Z";ANCHOR="2026-11-09T00:00:00Z"

class D1Tests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:")
        self.db.executescript(SCHEMA)
        self.db.executemany("INSERT INTO lab_identities(subject,slot) VALUES(?,?)",[(A,"friend-a"),(B,"friend-b")])
        self.db.execute("INSERT INTO lab_catalog VALUES(?,?,?,?,?,?,1)",KEY+("fixture-fx",))
    def tearDown(self):self.db.close()
    def enable(self):self.db.execute("UPDATE lab_state SET enabled=1 WHERE id=1")
    def submit(self,i=1,subject=A,price="1.0854",key=KEY):
        return self.db.execute(SQL["insert"],(subject,str(UUID(int=i)),*key,"WEEK","DELTA_PEAK",price,ANCHOR,T,T,"synthetic",*key))
    def receipts(self,subject):return self.db.execute(SQL["receipts"],(subject,0)).fetchall()
    def test_disabled_and_mapping(self):
        with self.assertRaises(sqlite3.IntegrityError):self.submit()
        self.assertIsNone(self.db.execute(SQL["gate"],(A,)).fetchone())
        self.enable()
        self.assertEqual(self.submit(key=("EURUSD","FXCM","EURUSD","SPOT","")).rowcount,0)
        self.assertEqual(self.submit().rowcount,1)
    def test_isolation_and_revocation(self):
        self.enable();self.submit()
        self.assertEqual(len(self.receipts(A)),1)
        self.assertEqual(self.receipts(B),[])
        self.db.execute("UPDATE lab_identities SET revoked=1 WHERE subject=?",(A,))
        self.assertEqual(self.receipts(A),[])
        self.assertIsNone(self.db.execute(SQL["existing"],(A,str(UUID(int=1)))).fetchone())
        with self.assertRaises(sqlite3.IntegrityError):self.submit(2,price="1.0855")
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("UPDATE lab_identities SET revoked=0 WHERE subject=?",(A,))
        with self.assertRaises(sqlite3.IntegrityError):self.db.execute("DELETE FROM lab_identities WHERE subject=?",(A,))
        self.assertEqual(self.submit(subject=B).rowcount,1)
    def test_caps_dedup_and_append_only(self):
        self.enable();self.submit()
        self.assertEqual(self.submit().rowcount,0)
        with self.assertRaises(sqlite3.IntegrityError):self.submit(2)
        for i in range(2,21):self.submit(i,price=str(i))
        with self.assertRaises(sqlite3.IntegrityError):self.submit(21,price="21")
        self.assertEqual(len(self.receipts(A)),20)
        for sql in ("UPDATE lab_entries SET note='changed'","DELETE FROM lab_entries"):
            with self.assertRaises(sqlite3.IntegrityError):self.db.execute(sql)
    def test_catalog_inactive(self):
        self.enable()
        self.db.execute("UPDATE lab_catalog SET active=0")
        self.assertEqual(self.submit().rowcount,0)
    def test_access_context_node(self):
        subprocess.run(["node",str(ROOT/"test_access_context_lab.mjs")],check=True,timeout=20)
    def test_adapter_node(self):
        subprocess.run(["node",str(ROOT/"test_d1_lab_adapter.mjs")],check=True,timeout=20)

if __name__=="__main__":unittest.main()
