# REMURA v0.8.124 LAB — 17/11/2026 08:24 CET
import sqlite3,unittest,tempfile
from pathlib import Path
from contextlib import closing
from test_level_transport_receiver_lab_v1 import payload,T
from level_transport_receiver_lab_v1 import decode,digest
from test_level_permit_ledger_v2 import RESERVE,STOP,FINAL
from level_receipt_custody_lab_v1 import SCHEMAS,ROOT,snapshot,verify_snapshot
PIN="a"*64
class ReceiptCustodyTests(unittest.TestCase):
    def setUp(self):
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        p,_,v=decode(payload());self.cfg=v["configuration_digest"]
        self.args=(PIN,self.cfg,p["chart_type"],p["timezone"],p["session"],T-300000)
        for f in SCHEMAS:self.db.executescript((ROOT/f).read_text())
        self.db.execute("INSERT INTO level_admission_v1(id,pin) VALUES(1,?)",(PIN,))
        self.db.execute("INSERT INTO level_receipt_session_v1 VALUES(1,?,?,?,?,?,?)",self.args)
        self.db.execute("UPDATE level_admission_v1 SET enabled=1")
        self.reserve(T+1500);self.finish(1,T+1500)
        self.db.commit()
    def reserve(self,t):self.db.execute(RESERVE,(PIN,t)).fetchall()
    def finish(self,a,t,n=0,raw=None):
        raw=payload(n) if raw is None else raw
        p,_,v=decode(raw)
        self.db.execute(FINAL,(PIN,p["snapshot_close_ms"],t,p["sender_clock_ms"],a,digest(raw),raw,v["present_levels"],*self.args[1:],t+100)).fetchall()
    def copy(self,stop=True):
        # Close only the isolated clone; never modify source flags to make a pin.
        self.db.commit()
        d=sqlite3.connect(":memory:");self.addCleanup(d.close)
        self.db.backup(d)
        if stop:d.execute(STOP,(PIN,)).fetchall()
        d.commit();d.execute("PRAGMA query_only=ON");return d
    def seal(self,d):return snapshot(d,synthetic=True,ingress_closed=True)
    def verify(self,d,p):return verify_snapshot(d,p,synthetic=True,ingress_closed=True)
    def test_exact_sqlite_backup_and_closed_flags(self):
        d=self.copy();m,p=self.seal(d)
        clone=sqlite3.connect(":memory:");self.addCleanup(clone.close)
        d.backup(clone);clone.execute("PRAGMA query_only=ON")
        out=self.verify(clone,p)
        self.assertEqual(out["receipts"],1)
        for key in ("independent_pin_verified","backup_encrypted","restore_authorized","may_open","scientific_admission"):self.assertFalse(out[key])
        self.assertNotIn(PIN,str(m));self.assertNotIn(payload(),str(m))
        self.assertFalse(d.in_transaction)
    def test_older_backup_and_same_count_pin(self):
        old=self.copy();_,oldpin=self.seal(old)
        self.reserve(T+1600);new=self.copy();_,pin=self.seal(new)
        self.assertNotEqual(pin,oldpin)
        with self.assertRaises(ValueError):self.verify(old,pin)
        self.assertEqual(self.verify(new,pin)["attempts"],2)
    def test_same_receipt_count_duplicate_changes_pin(self):
        self.reserve(T+1600);before=self.copy();_,p=self.seal(before)
        self.finish(2,T+1600);after=self.copy();m,q=self.seal(after)
        self.assertEqual(m["receipts"],1);self.assertEqual(m["finalizations"],2)
        self.assertNotEqual(p,q)
        with self.assertRaises(ValueError):self.verify(before,q)
    def test_schema_tamper_and_open_rejected(self):
        with self.assertRaises(ValueError):self.seal(self.copy(stop=False))
        d=self.copy();d.execute("PRAGMA query_only=OFF")
        d.execute("DROP TRIGGER level_finalizations_no_update_v2")
        d.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):self.seal(d)
    def test_payload_tamper_even_when_schema_restored(self):
        d=self.copy();_,p=self.seal(d);d.execute("PRAGMA query_only=OFF")
        sql=d.execute("SELECT sql FROM sqlite_master WHERE name='level_finalizations_no_update_v2'").fetchone()[0]
        d.execute("DROP TRIGGER level_finalizations_no_update_v2")
        d.execute("UPDATE level_finalizations_v2 SET body='{}'")
        d.execute(sql);d.commit();d.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):self.verify(d,p)
    def test_wrong_pin_and_scope(self):
        d=self.copy();_,p=self.seal(d)
        with self.assertRaises(ValueError):self.verify(d,"0"*64)
        for k in ("synthetic","ingress_closed"):
            args=dict(synthetic=True,ingress_closed=True);args[k]=False
            with self.assertRaises(ValueError):snapshot(d,**args)
        d.execute("PRAGMA query_only=OFF")
        with self.assertRaises(ValueError):self.seal(d)
    def test_disk_and_attached_denied(self):
        with tempfile.TemporaryDirectory() as t,closing(sqlite3.connect(Path(t)/"fixture.sqlite")) as disk:
            self.db.backup(disk);disk.execute("PRAGMA query_only=ON")
            with self.assertRaises(ValueError):self.seal(disk)
        d=self.copy();d.execute("PRAGMA query_only=OFF");d.execute("ATTACH ':memory:' AS extra");d.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):self.seal(d)
    def test_no_legacy_receipt_mix(self):
        # Populate old v1 while source is enabled and last permit is available.
        self.db.execute("INSERT INTO level_receipts_v1 VALUES(?,?,?,?,?,?,?)",(T,T+1500,T,1,digest(payload()),payload(),4))
        d=self.copy()
        with self.assertRaises(ValueError):self.seal(d)
if __name__=="__main__":unittest.main()
