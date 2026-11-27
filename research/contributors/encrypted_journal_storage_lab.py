# REMURA Contributors v0.29 LAB — 16/11/2026 08:24 CET
"""Synthetic encrypted journal rehearsal using existing POSIX append/lock/fsync protocol.
Node built-in AES-GCM only, no third-party dependencies. No real identities or keys permitted.
Key and decrypted data can exist in process memory; no promise of secure memory erasure.
"""
import json,subprocess
from pathlib import Path
from recovery_journal_candidate import valid_hex,HEX32
from recovery_journal_storage_lab import Journal,deny
NODE=Path(__file__).with_name("journal_envelope_lab.mjs").resolve()
def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()
class EncryptedJournal(Journal):
    max_bytes=3072
    def __init__(self,root,expected_pin,*,key,journal_id,synthetic=False,initialize=False):
        if synthetic is not True or type(key) is not bytes or len(key)!=32 or not any(key) or not valid_hex(journal_id,HEX32):deny()
        self._key=key;self._journal_id=journal_id
        super().__init__(root,expected_pin,synthetic=True,initialize=initialize)
    def _crypt(self,mode,seq,data):
        req={"synthetic":True,"mode":mode,"key":self._key.hex(),"journal":self._journal_id,"seq":seq,"data":data}
        # No key or plaintext in argv, env, logs or temporary files. Trusted local Node executable/module assumed.
        try:
            r=subprocess.run(["node",str(NODE)],input=canonical(req),stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,timeout=5,check=True)
            if not 0<len(r.stdout)<=3072:deny()
            return json.loads(r.stdout)
        except (OSError,subprocess.SubprocessError,ValueError):raise ValueError("encrypted_journal_denied") from None
    def _encode(self,event,seq):
        raw=canonical(event)
        if not 0<len(raw)<=1024:deny()
        return canonical(self._crypt("seal",seq,raw.hex()))
    def _decode(self,raw,seq):
        e=json.loads(raw)
        if canonical(e)!=raw:deny()
        r=self._crypt("open",seq,e)
        if type(r) is not dict or set(r)!={"plaintext"} or type(r["plaintext"]) is not str:deny()
        plain=bytes.fromhex(r["plaintext"])
        if not 0<len(plain)<=1024:deny()
        event=json.loads(plain)
        if canonical(event)!=plain:deny()
        return event
