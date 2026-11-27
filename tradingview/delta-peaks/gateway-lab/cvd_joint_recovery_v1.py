# REMURA v0.8.100 LAB — 16/11/2026 14:54 CET
"""Synthetic exact-ciphertext recovery into an absent local file. No live adapter."""
import json,os,secrets
from cvd_joint_encrypted_v1 import open_encrypted_joint,NAME,TMP,MAX_CIPHER
from cvd_joint_publication_v1 import validate,MAX_FILE,need
from cvd_runtime_private_state_v1 import encoded,digest,_no_duplicates

def restore(root,custody,*,generation,key,expected,backup,synthetic=False):
    need(synthetic is True and type(backup) is bytes and 0<len(backup)<=MAX_CIPHER)
    with open_encrypted_joint(root,custody,generation=generation,key=key,synthetic=True) as s:
        s.authority(expected,"STABLE");s.check()
        try:os.stat(NAME,dir_fd=s.fd,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise ValueError("synthetic_restore_target_exists")
        # Fully authenticate and semantically validate before creating any file.
        plain=s.decode_file(backup)
        need(0<len(plain)<=MAX_FILE)
        w=json.loads(plain,object_pairs_hook=_no_duplicates)
        need(type(w) is dict and set(w)=={"state","sha256"} and encoded(w)==plain)
        state=w["state"]
        need(w["sha256"]==digest(state)==expected.state_digest)
        ledger=validate(state,generation)
        desc=s.describe(state,ledger)
        need(desc["claim_ms"]==expected.cutoff_ms and ledger.summary()["cycles_recorded"]==expected.sequence)
        s.authority(expected,"STABLE");s.check()
        tmp=TMP+secrets.token_hex(16)
        # Atomic no-clobber publication using link, not replacement. If link or
        # removal fails the orphan blocks other handles. No automatic cleanup.
        f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=s.fd)
        with os.fdopen(f,"wb") as stream:
            stream.write(backup);stream.flush();os.fsync(stream.fileno())
        s.guard();s.authority(expected,"STABLE")
        os.link(tmp,NAME,src_dir_fd=s.fd,dst_dir_fd=s.fd,follow_symlinks=False)
        os.fsync(s.fd)
        os.unlink(tmp,dir_fd=s.fd)
        os.fsync(s.fd)
        verified=s.status(expected)
        need(verified==desc)
        return {"status":"EXACT_SYNTHETIC_BACKUP_RESTORED",
                "state_digest":verified["state_digest"],"sequence":expected.sequence,
                "cutoff_ms":expected.cutoff_ms,"archive":verified["archive"],
                "custody_advanced":False,"independent_custody_verified":False,
                "scientific_admission":False,"live_authorized":False}
