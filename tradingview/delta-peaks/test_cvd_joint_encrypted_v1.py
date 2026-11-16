# REMURA v0.8.98 LAB — 16/11/2026 13:56 CET
import json,sqlite3,sys,tempfile,types,unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parent/"gateway-lab"))
import cvd_joint_encrypted_v1 as m
import cvd_joint_publication_v1 as plain
from cvd_runtime_singleflight_v1 import NAME as LOCK
from cvd_runtime_private_state_v1 import PERIOD,DELAY,encoded
from cvd_incremental_preview_v1 import repage,RollingPreview
from cvd_private_runtime_preview_v1 import plan,preview
from test_cvd_batch_nonoverlap_preview_v1 import triples
from test_cvd_telemetry_preview_v1 import T0
from test_research_dossier_preview_v1 import mock_audit
G="a"*32;KEY=b"\x42"*32
class EncryptedJointTests(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory();self.addCleanup(t.cleanup)
        self.root=Path(t.name);(self.root/LOCK).touch(mode=0o600)
        self.path=self.root/m.NAME;self.c=m.EncryptedCustody(G,synthetic=True)
        self.db=sqlite3.connect(":memory:");self.addCleanup(self.db.close)
        self.db.execute("PRAGMA query_only=ON")
        p=types.ModuleType("scripts");p.shark_causal_pair_audit=types.SimpleNamespace(audit=mock_audit([]))
        ctx=patch.dict(sys.modules,{"scripts":p});ctx.start();self.addCleanup(ctx.stop)
        self.now=T0+DELAY
        self.rows=[r for r,_,_ in triples(18,events=(0,14))]
    def store(self,key=KEY):
        return m.open_encrypted_joint(self.root,self.c,generation=G,key=key,synthetic=True)
    def full(self,now):return repage(plan(now),self.rows)
    def step(self,p):
        nxt=self.now+PERIOD
        old=RollingPreview(now=self.now,windows=self.full(self.now),synthetic=True)
        with self.store() as s:return s.cycle(self.db,expected=p,cutoff=nxt,windows=repage(old.next_ranges(nxt),self.rows))
    def boot(self):
        with self.store() as s:return s.bootstrap(self.db,expected=self.c.latest(),cutoff=self.now,windows=self.full(self.now),cycles=3)
    def test_roundtrip_no_plaintext_or_old_file(self):
        p,r=self.boot();raw=self.path.read_bytes()
        self.assertEqual(set(json.loads(raw)),{"v","nonce","ct","tag"})
        for s in (b"raw_json",b"EURUSD",b"DATI SINTETICI",KEY.hex().encode(),b"archive"):
            self.assertNotIn(s,raw)
        self.assertFalse((self.root/plain.NAME).exists())
        with self.store() as j:self.assertEqual(j.status(p),r)
        q,v=self.step(p)
        self.assertNotEqual(json.loads(raw)["nonce"],json.loads(self.path.read_bytes())["nonce"])
        self.assertEqual(v["preview"],preview(self.db,self.full(self.now+PERIOD),now=self.now+PERIOD,origin="SYNTHETIC"))
        self.assertEqual(v["archive"]["cycles_recorded"],2)
        self.assertEqual(self.db.total_changes,0)
        self.assertEqual({x.name for x in self.root.iterdir()},{LOCK,m.NAME})
        self.assertLessEqual(self.path.stat().st_size,m.MAX_CIPHER)
    def test_wrong_key_no_mutation(self):
        p,_=self.boot();old=self.path.read_bytes()
        with self.store(b"\x43"*32) as s:
            with self.assertRaises(ValueError):s.status(p)
        self.assertEqual(self.path.read_bytes(),old);self.assertEqual(self.c.latest(),p)
    def test_tamper_tag_nonce_and_ciphertext(self):
        p,_=self.boot();old=self.path.read_bytes()
        for field in ("tag","nonce","ct"):
            e=json.loads(old);e[field]=("A" if e[field][0]!="A" else "B")+e[field][1:] if field=="ct" else ("0" if e[field][0]!="0" else "1")+e[field][1:]
            self.path.write_bytes(encoded(e))
            with self.store() as s:
                with self.assertRaises(ValueError):s.status(p)
        self.path.write_bytes(old)
        with self.store() as s:self.assertEqual(s.status(p)["archive"]["cycles_recorded"],1)
    def test_old_valid_ciphertext_denied(self):
        p,_=self.boot();old=self.path.read_bytes();q,_=self.step(p)
        self.path.write_bytes(old)
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(q)
            with self.assertRaises(ValueError):s.status(p)
    def test_failed_seal_after_reservation_blocks_retry(self):
        p,_=self.boot();old=self.path.read_bytes()
        with patch.object(m.EncryptedJoint,"encode_file",side_effect=ValueError("synthetic failure")):
            with self.assertRaises(ValueError):self.step(p)
        self.assertEqual(self.path.read_bytes(),old);self.assertEqual(self.c.latest().phase,"PENDING")
        with self.store() as s:
            with self.assertRaises(ValueError):s.status(p)
    def test_rename_failure_candidate_is_ciphertext_only(self):
        p,_=self.boot();old=self.path.read_bytes()
        with patch.object(plain.os,"replace",side_effect=OSError("fault")):
            with self.assertRaises(OSError):self.step(p)
        self.assertEqual(self.path.read_bytes(),old)
        files=list(self.root.glob(m.TMP+"*"));self.assertEqual(len(files),1)
        self.assertEqual(set(json.loads(files[0].read_bytes())),{"v","nonce","ct","tag"})
        self.assertNotIn(b"raw_json",files[0].read_bytes())
        self.assertEqual(self.c.latest().phase,"PENDING")
    def test_explicit_key_and_authority_gate(self):
        for k in (b"",b"\0"*32,"bad"):
            with self.assertRaises(ValueError):
                with self.store(k):pass
        with self.assertRaises(ValueError):
            with m.open_encrypted_joint(self.root,plain.JointCustody(G,synthetic=True),generation=G,key=KEY,synthetic=True):pass
        with self.assertRaises(ValueError):
            with m.open_encrypted_joint(self.root,self.c,generation=G,key=KEY):pass
