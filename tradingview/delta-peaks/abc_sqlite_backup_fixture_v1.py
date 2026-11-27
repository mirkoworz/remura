# REMURA v0.8.138 LAB — 17/11/2026 CET
import contextlib,sqlite3,unittest
from abc_sqlite_backup_lab_v1 import Fixture,NAMES
def seed(f):
    for name in NAMES:
        with contextlib.closing(sqlite3.connect(f.path("source",name))) as db:
            db.execute("CREATE TABLE evidence(id INTEGER PRIMARY KEY, original TEXT NOT NULL)")
            db.execute("INSERT INTO evidence VALUES(1,'original-cutoff')")
            db.commit()
def rows(path):
    with contextlib.closing(sqlite3.connect(path)) as db:
        return db.execute("SELECT * FROM evidence ORDER BY id").fetchall()
class Tests(unittest.TestCase):
    def test_wal_snapshot_and_uncommitted_excluded(self):
        with Fixture(synthetic=True) as f:
            seed(f)
            with contextlib.closing(sqlite3.connect(f.path("source",NAMES[0]))) as writer:
                self.assertEqual(writer.execute("PRAGMA journal_mode=WAL").fetchone()[0],"wal")
                writer.execute("PRAGMA wal_autocheckpoint=0")
                writer.execute("INSERT INTO evidence VALUES(2,'committed-in-wal')");writer.commit()
                self.assertTrue(f.path("source",NAMES[0]).with_name(NAMES[0]+"-wal").stat().st_size>0)
                writer.execute("INSERT INTO evidence VALUES(3,'uncommitted')")
                m=f.capture()
                writer.rollback()
                writer.execute("INSERT INTO evidence VALUES(4,'after-snapshot')");writer.commit()
                r=f.restore(m,m["manifest_sha256"])
                self.assertEqual(r["restored_databases"],2)
                self.assertEqual(rows(f.path("restore",NAMES[0])),[(1,"original-cutoff"),(2,"committed-in-wal")])
                self.assertEqual(rows(f.path("source",NAMES[0])),[(1,"original-cutoff"),(2,"committed-in-wal"),(4,"after-snapshot")])
                self.assertFalse(m["cross_db_atomicity_verified"])
                self.assertFalse(m["release_authorized"])
    def test_corrupt_second_database_refuses_before_restore(self):
        with Fixture(synthetic=True) as f:
            seed(f);m=f.capture()
            with f.path("snapshot",NAMES[1]).open("ab") as fh:fh.write(b"tamper")
            with self.assertRaises(ValueError):f.restore(m,m["manifest_sha256"])
            self.assertFalse(any((f.root/"restore").iterdir()))
    def test_external_pin_and_manifest_binding(self):
        with Fixture(synthetic=True) as f:
            seed(f);m=f.capture()
            with self.assertRaises(ValueError):f.restore(m,"0"*64)
            m["files"][NAMES[0]]["bytes"]+=1
            with self.assertRaises(ValueError):f.restore(m,m["manifest_sha256"])
    def test_scope_and_non_overwrite(self):
        with self.assertRaises(ValueError):Fixture()
        with Fixture(synthetic=True) as f:
            seed(f);m=f.capture()
            with self.assertRaises(ValueError):f.path("source","../outside")
            with self.assertRaises(ValueError):f.capture()
            f.restore(m,m["manifest_sha256"])
            with self.assertRaises(ValueError):f.restore(m,m["manifest_sha256"])
if __name__=="__main__":unittest.main()
