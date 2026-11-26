"""V30.5 LAB — offline request preparation only, no network.
A timestamp establishes existence by its signed time, not source truth.
"""
import hashlib,json,secrets,subprocess
OPENSSL="/usr/bin/openssl"
CA_SHA256="2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438"
TSA_SHA256="8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467"
def prepare(commitment,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    if type(commitment) is not str or len(commitment)!=64 or any(c not in "0123456789abcdef" for c in commitment):
        raise ValueError("commitment")
    # Salt remains private, preventing guessing from an externally sent digest.
    envelope=json.dumps({"schema":"remura-v305-witness-v1","commitment":commitment,
        "salt":secrets.token_hex(32)},sort_keys=True,separators=(",",":")).encode()
    h=hashlib.sha256(envelope).hexdigest()
    q=subprocess.run([OPENSSL,"ts","-query","-digest",h,"-sha256","-cert"],
        capture_output=True,timeout=5,check=True).stdout
    if not 0<len(q)<16384:raise ValueError("query_size")
    return envelope,q
