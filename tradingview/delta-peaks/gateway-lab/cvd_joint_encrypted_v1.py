# REMURA v0.8.98 LAB — 16/11/2026 13:56 CET
"""Synthetic encrypted joint storage. No real keys or secure memory-erasure claim."""
import base64,json,os,stat,subprocess
from pathlib import Path
from contextlib import contextmanager
from cvd_joint_publication_v1 import Joint,JointCustody,MAX_FILE,need
from cvd_runtime_private_state_v1 import encoded,_private,_no_duplicates
from cvd_runtime_singleflight_v1 import single_flight
NAME="remura-d-joint-encrypted-synthetic-v1.json"
TMP=".remura-d-joint-encrypted-synthetic-"
NODE=Path(__file__).with_name("cvd_joint_envelope_lab.mjs").resolve()
MAX_CIPHER=4*((MAX_FILE+2)//3)+4096
class EncryptedCustody(JointCustody):
    """Distinct simulated authority; not independently durable."""
class EncryptedJoint(Joint):
    filename=NAME
    prefix=TMP
    def __init__(self,fd,guard,custody,generation,key):
        super().__init__(fd,guard,custody,generation);self._key=key
    def file_limit(self):return MAX_CIPHER
    def _crypt(self,mode,data):
        p=self.c.latest()
        need(p.phase in ("PENDING","STABLE") and p.generation==self.g and 1<=p.sequence<=96)
        if mode=="seal":need(p.phase=="PENDING")
        req={"synthetic":True,"mode":mode,"key":self._key.hex(),"generation":self.g,
             "sequence":p.sequence,"cutoff_ms":p.cutoff_ms,"data":data}
        try:
            wire=encoded(req);need(len(wire)<=MAX_CIPHER+4096)
            r=subprocess.run(["node",str(NODE)],input=wire,stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL,timeout=20,check=True)
            need(0<len(r.stdout)<=MAX_CIPHER)
            out=json.loads(r.stdout,object_pairs_hook=_no_duplicates)
            need(self.c.latest()==p)
            return out
        except (OSError,subprocess.SubprocessError,ValueError,TypeError):
            raise ValueError("synthetic_joint_encryption_denied") from None
    def encode_file(self,plain):
        need(type(plain) is bytes and 0<len(plain)<=MAX_FILE)
        e=self._crypt("seal",base64.b64encode(plain).decode("ascii"))
        need(type(e) is dict and set(e)=={"v","nonce","ct","tag"})
        return encoded(e)
    def decode_file(self,raw):
        try:
            e=json.loads(raw,object_pairs_hook=_no_duplicates)
            need(type(e) is dict and set(e)=={"v","nonce","ct","tag"} and encoded(e)==raw)
            r=self._crypt("open",e)
            need(type(r) is dict and set(r)=={"plaintext"} and type(r["plaintext"]) is str)
            plain=base64.b64decode(r["plaintext"],validate=True)
            need(0<len(plain)<=MAX_FILE and base64.b64encode(plain).decode("ascii")==r["plaintext"])
            return plain
        except (ValueError,TypeError):raise ValueError("synthetic_joint_encryption_denied") from None

@contextmanager
def open_encrypted_joint(root,custody,*,generation,key,synthetic=False):
    need(synthetic is True and type(custody) is EncryptedCustody and custody.latest().generation==generation)
    need(type(key) is bytes and len(key)==32 and any(key))
    fd=os.open(root,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
    try:
        st=os.fstat(fd);_private(st,stat.S_ISDIR);identity=(st.st_dev,st.st_ino)
        with single_flight(root) as held:
            def guard():
                held()
                current=os.stat(root,follow_symlinks=False);_private(current,stat.S_ISDIR)
                need((current.st_dev,current.st_ino)==identity)
            guard()
            yield EncryptedJoint(fd,guard,custody,generation,key)
    finally:os.close(fd)
