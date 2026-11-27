# REMURA v0.8.138 LAB — 17/11/2026 CET
"""Disposable SQLite WAL backup/restore rehearsal only; no live path accepted."""
import contextlib,hashlib,json,sqlite3,tempfile
from pathlib import Path
from abc_overlay_transaction_lab_v1 import need
NAMES=("prices.sqlite3","evidence.sqlite3")
MAX=2*1024*1024
def digest(path):
    need(path.is_file() and not path.is_symlink() and 0<path.stat().st_size<=MAX)
    return hashlib.sha256(path.read_bytes()).hexdigest()
def readonly(path):
    return sqlite3.connect(path.as_uri()+"?mode=ro",uri=True,timeout=2)
def logical(path):
    with contextlib.closing(readonly(path)) as db:
        need(db.execute("PRAGMA integrity_check").fetchall()==[("ok",)])
        need(not db.execute("PRAGMA foreign_key_check").fetchall())
        return hashlib.sha256("\n".join(db.iterdump()).encode()).hexdigest()
def copy_db(src,dst):
    need(src.is_file() and not src.is_symlink() and not dst.exists())
    with contextlib.closing(readonly(src)) as a,contextlib.closing(sqlite3.connect(dst,timeout=2)) as b:
        a.backup(b,pages=16,sleep=0.01)
    dst.chmod(0o600)
    return {"bytes":dst.stat().st_size,"sha256":digest(dst),"logical_sha256":logical(dst)}
class Fixture:
    def __init__(self,*,synthetic=False):
        need(synthetic is True)
        self._temp=tempfile.TemporaryDirectory(prefix="remura-sqlite-fixture-")
        self.root=Path(self._temp.name)
        for name in ("source","snapshot","restore"):
            (self.root/name).mkdir(mode=0o700)
    def __enter__(self):return self
    def __exit__(self,*args):self._temp.cleanup()
    def path(self,folder,name):
        need(folder in ("source","snapshot","restore") and name in NAMES)
        return self.root/folder/name
    def capture(self):
        # Independent per-DB SQLite snapshots. No common cut is asserted.
        result={name:copy_db(self.path("source",name),self.path("snapshot",name)) for name in NAMES}
        return {"schema":"remura.abc.synthetic.sqlite.snapshot.v1","files":result,
                "manifest_sha256":hashlib.sha256(json.dumps(result,sort_keys=True,separators=(",",":")).encode()).hexdigest(),
                "cross_db_atomicity_verified":False,"external_custody_verified":False,
                "encryption_verified":False,"live_backup_verified":False,"release_authorized":False}
    def restore(self,manifest,expected_pin):
        need(type(manifest) is dict and manifest.get("schema")=="remura.abc.synthetic.sqlite.snapshot.v1")
        files=manifest.get("files");need(type(files) is dict and set(files)==set(NAMES))
        actual=hashlib.sha256(json.dumps(files,sort_keys=True,separators=(",",":")).encode()).hexdigest()
        need(actual==expected_pin==manifest.get("manifest_sha256"))
        # Entire snapshot is checked before any restore is started.
        for name,row in files.items():
            p=self.path("snapshot",name)
            need(type(row) is dict and set(row)=={"bytes","sha256","logical_sha256"})
            need(digest(p)==row["sha256"] and p.stat().st_size==row["bytes"] and logical(p)==row["logical_sha256"])
        for name,row in files.items():
            new=copy_db(self.path("snapshot",name),self.path("restore",name))
            need(new["logical_sha256"]==row["logical_sha256"])
        return {"restored_databases":len(files),"logical_restore_verified":True,"release_authorized":False}
