# REMURA v0.8.139 LAB — 17/11/2026 17:27 CET
import tempfile,unittest,shutil
from pathlib import Path
from abc_sqlite_backup_lab_v1 import Fixture,NAMES
from abc_sqlite_backup_fixture_v1 import seed,rows
from abc_encrypted_handoff_lab_v1 import gpg,identity,archive,seal,witness,recover,sha
class Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if shutil.which("gpg") is None:raise RuntimeError("GPG_REQUIRED_NO_SKIP")
        cls.tmp=tempfile.TemporaryDirectory(prefix="remura-key-lab-")
        cls.addClassCleanup(cls.tmp.cleanup)
        root=Path(cls.tmp.name)
        cls.sender=root/"sender";cls.receiver=root/"recovery";cls.wrong=root/"wrong"
        for h in (cls.sender,cls.receiver,cls.wrong):h.mkdir(mode=0o700)
        cls.recipient=identity(cls.receiver,"recovery")
        identity(cls.wrong,"wrong")
        public=gpg(cls.receiver,"--export",cls.recipient).stdout
        gpg(cls.sender,"--import",data=public)
        with Fixture(synthetic=True) as source:
            seed(source);m=source.capture()
            body=archive(source,m)
            cls.cipher=seal(cls.sender,cls.recipient,body,synthetic=True)
        cls.pin=witness(cls.cipher,m["manifest_sha256"],2,cls.recipient)
    def restore(self,f,**kw):
        kwargs=dict(generation=2,recipient=self.recipient,synthetic=True)
        kwargs.update(kw)
        return recover(self.receiver,self.cipher,self.pin,f,**kwargs)
    def test_only_encrypted_handoff_survives(self):
        with Fixture(synthetic=True) as f:
            out=self.restore(f)
            self.assertEqual(out["restored_databases"],2)
            self.assertTrue(out["synthetic_encryption_verified"])
            self.assertFalse(out["independent_live_custody_verified"])
            self.assertEqual(rows(f.path("restore",NAMES[1])),[(1,"original-cutoff")])
    def test_wrong_key_and_sender_cannot_decrypt(self):
        for home in (self.wrong,self.sender):
            with Fixture(synthetic=True) as f:
                with self.assertRaises(ValueError):
                    recover(home,self.cipher,self.pin,f,generation=2,recipient=self.recipient,synthetic=True)
                self.assertFalse(any((f.root/"snapshot").iterdir()))
    def test_tamper_even_if_cipher_hash_recomputed(self):
        for b in (self.cipher[:-20],self.cipher[:-10]+bytes([self.cipher[-10]^1])+self.cipher[-9:]):
            with Fixture(synthetic=True) as f:
                pin={**self.pin,"cipher_sha256":sha(b)}
                with self.assertRaises(ValueError):
                    recover(self.receiver,b,pin,f,generation=2,recipient=self.recipient,synthetic=True)
                self.assertFalse(any((f.root/"snapshot").iterdir()))
    def test_wrong_generation_or_recipient(self):
        with Fixture(synthetic=True) as f:
            for kw in ({"generation":3},{"recipient":"0"*40},{"synthetic":False}):
                with self.assertRaises(ValueError):self.restore(f,**kw)
            self.assertFalse(any((f.root/"snapshot").iterdir()))
if __name__=="__main__":unittest.main()
