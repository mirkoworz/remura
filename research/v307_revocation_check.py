"""V30.7 — new revocation check on existing synthetic proof only.
One public CRL GET. No timestamp POST, no private data sent.
"""
import hashlib,os,sys,stat,subprocess
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
PINS={"cacert.pem":"2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438","tsa.crt":"8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467"}
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def run():
    os.umask(0o077)
    base=Path.home()/".remura-v296";d=base/"v306-tsa-synthetic"
    for p in (base,d):
        s=p.lstat()
        if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise ValueError("directory")
    for name in (*PINS,"response.tsr"):
        p=d/name;s=p.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600 or not 0<s.st_size<=65536:raise ValueError("file")
        if name in PINS and hashlib.sha256(p.read_bytes()).hexdigest()!=PINS[name]:raise ValueError("pin")
    def ssl(*args,stdin=None):
        return subprocess.run(["/usr/bin/openssl",*args],cwd=d,input=stdin,capture_output=True,timeout=10,check=True).stdout
    # New check: bind the existing timestamp signer to the pinned leaf certificate.
    token=ssl("ts","-reply","-in","response.tsr","-token_out")
    ssl("cms","-verify","-inform","DER","-nointern","-certfile","tsa.crt","-noverify","-out","/dev/null",stdin=token)
    print("FIRMATARIO_PINNED=OK",flush=True)
    with (d/"v307-crl-attempt.lock").open("x") as f:
        f.write("ONE_SHOT\n");f.flush();os.fsync(f.fileno())
    print("CRL_GET_TENTATO=1",flush=True)
    opener=build_opener(ProxyHandler({}),NoRedirect())
    with opener.open(Request("https://www.freetsa.org/crl/root_ca.crl"),timeout=15) as res:
        if res.status!=200:raise ValueError("http")
        raw=res.read(1000001)
    if not 0<len(raw)<=1000000:raise ValueError("size")
    with (d/"v307-root-ca.crl").open("xb") as f:f.write(raw)
    fmt="PEM" if raw.startswith(b"-----BEGIN X509 CRL-----") else "DER"
    pem=ssl("crl","-inform",fmt,"-in","v307-root-ca.crl","-outform","PEM")
    with (d/"v307-root-ca.pem").open("xb") as f:f.write(pem)
    ssl("verify","-CAfile","cacert.pem","-CRLfile","v307-root-ca.pem","-crl_check","-purpose","timestampsign","tsa.crt")
    print("CRL_FIRMA_VALIDITA_REVOCA=OK")
    print(ssl("crl","-in","v307-root-ca.pem","-noout","-lastupdate","-nextupdate").decode("ascii").strip())
    print("TSA_POST=0")
    print("PROSPECTIVE_ADMITTED=NO")
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("V307 CRL STOP",type(e).__name__);sys.exit(2)
