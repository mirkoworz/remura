# REMURA v0.8.128 LAB — 17/11/2026 CET
import base64,copy,json,sqlite3,subprocess,unittest
from pathlib import Path
import test_level_receipt_custody_lab_v1 as custody
from level_receipt_witness_lab_v1 import genesis,advance,verify_recovery
KEY=b"e"*32; W=b"w"*32
G="1"*32; N="2"*32
FLAGS=dict(synthetic=True,ingress_closed=True)
SCRIPT=Path(__file__).parent/"level_encrypted_backup_fixture.mjs"
def run(op,context,**kw):
    spec=dict(op=op,context=context,key=KEY.hex(),witness_key=W.hex(),**FLAGS)
    spec.update(kw)
    p=subprocess.run(["node",str(SCRIPT)],input=json.dumps(spec),text=True,capture_output=True,check=True,timeout=5)
    return json.loads(p.stdout)
def encode(b):return base64.b64encode(b).decode("ascii")
class EncryptedBackupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        f=custody.ReceiptCustodyTests("test_exact_sqlite_backup_and_closed_flags")
        try:
            f.setUp()
            old=f.copy();_,p=f.seal(old)
            cls.first,cls.first_anchor=genesis(p,G,W,**FLAGS)
            cls.raw_old=old.serialize()
            f.reserve(custody.T+1600);new=f.copy();_,q=f.seal(new)
            cls.record,cls.anchor=advance(cls.first,W,latest_anchor=cls.first_anchor,latest_generation=G,latest_sequence=1,new_generation=N,new_snapshot_pin=q,**FLAGS)
            cls.raw=new.serialize()
            cls.context=dict(anchor=cls.anchor,generation=N,sequence=2)
            cls.old_context=dict(anchor=cls.first_anchor,generation=G,sequence=1)
            cls.envelope=run("seal",cls.context,data=encode(cls.raw))["envelope"]
        finally:f.doCleanups()
    def decrypt(self,e=None,**kw):return run("open",kw.pop("context",self.context),envelope=self.envelope if e is None else e,**kw)
    def reject(self,e=None,**kw):self.assertEqual(self.decrypt(e,**kw),{"ok":False,"error":"DENIED"})
    def test_sqlite_roundtrip_and_witness(self):
        out=self.decrypt();self.assertTrue(out["ok"])
        raw=base64.b64decode(out["data"],validate=True);self.assertEqual(raw,self.raw)
        db=sqlite3.connect(":memory:");self.addCleanup(db.close)
        db.deserialize(raw);db.execute("PRAGMA query_only=ON")
        r=verify_recovery(db,self.record,W,latest_anchor=self.anchor,latest_generation=N,latest_sequence=2,**FLAGS)
        self.assertTrue(r["fixture_mac_verified"]);self.assertFalse(r["may_open"]);self.assertFalse(r["backup_encrypted"])
    def test_random_nonce_and_ciphertext(self):
        second=run("seal",self.context,data=encode(self.raw))["envelope"]
        self.assertNotEqual(second["nonce"],self.envelope["nonce"])
        self.assertNotEqual(second["ciphertext"],self.envelope["ciphertext"])
        self.assertEqual(self.decrypt(second)["data"],encode(self.raw))
    def test_tamper_ciphertext_nonce_tag(self):
        for field in ("ciphertext","nonce","tag"):
            e=copy.deepcopy(self.envelope);b=bytearray(base64.b64decode(e[field]));b[0]^=1;e[field]=encode(b)
            self.reject(e)
    def test_wrong_key_and_shared_key_denied(self):
        self.reject(key=(b"z"*32).hex())
        self.reject(witness_key=KEY.hex())
        self.assertFalse(run("seal",self.context,data=encode(self.raw),witness_key=KEY.hex())["ok"])
    def test_context_binding_and_old_envelope(self):
        self.reject(context=self.old_context)
        old=run("seal",self.old_context,data=encode(self.raw_old))["envelope"]
        self.reject(old)
        old["context"]=self.context
        self.reject(old)
    def test_old_plaintext_reencrypted_with_latest_context(self):
        # An authorized encryptor can encrypt stale bytes. The independent witness must still reject them.
        e=run("seal",self.context,data=encode(self.raw_old))["envelope"]
        raw=base64.b64decode(self.decrypt(e)["data"])
        db=sqlite3.connect(":memory:");self.addCleanup(db.close);db.deserialize(raw);db.execute("PRAGMA query_only=ON")
        with self.assertRaises(ValueError):verify_recovery(db,self.record,W,latest_anchor=self.anchor,latest_generation=N,latest_sequence=2,**FLAGS)
    def test_malformed_and_scope(self):
        for e in ({},dict(self.envelope,extra=True),dict(self.envelope,tag="!"),dict(self.envelope,ciphertext="A"*1398110)):
            self.reject(e)
        self.reject(synthetic=False);self.reject(ingress_closed=False)
        self.assertFalse(run("seal",self.context,data=encode(b"not sqlite"))["ok"])
if __name__=="__main__":unittest.main()
