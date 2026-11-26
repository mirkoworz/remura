"""V30.6 synthetic RFC3161 proof. One POST, no redirect/retry, no private data."""
import os,sys,hashlib,subprocess,secrets,stat
from pathlib import Path
from urllib.request import Request,build_opener,HTTPRedirectHandler,ProxyHandler
class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
PINS={"cacert.pem":"2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438","tsa.crt":"8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467"}
def run():
    os.umask(0o077)
    base=Path.home()/".remura-v296"
    s=base.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o700:raise ValueError("base")
    d=base/"v306-tsa-synthetic"
    d.mkdir(mode=0o700)
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def fetch(url,body=None):
        headers={"Content-Type":"application/timestamp-query"} if body is not None else {}
        with opener.open(Request(url,data=body,headers=headers),timeout=15) as r:
            if r.status!=200:raise ValueError("http")
            if body is not None and r.headers.get_content_type()!="application/timestamp-reply":raise ValueError("content_type")
            data=r.read(65537)
            if not 0<len(data)<=65536:raise ValueError("size")
            return data
    def ssl(*args):
        return subprocess.run(["/usr/bin/openssl",*args],cwd=d,check=True,timeout=10,capture_output=True).stdout
    for name,pin in PINS.items():
        data=fetch("https://freetsa.org/files/"+name)
        if hashlib.sha256(data).hexdigest()!=pin:raise ValueError("certificate_pin")
        (d/name).write_bytes(data)
    print("CERTIFICATI_PIN=2/2",flush=True)
    ssl("verify","-purpose","timestampsign","-CAfile","cacert.pem","tsa.crt")
    (d/"synthetic.txt").write_text("REMURA V30.6 SYNTHETIC ONLY "+secrets.token_hex(32))
    ssl("ts","-query","-data","synthetic.txt","-sha256","-cert","-out","request.tsq")
    print("POST_TENTATO=1",flush=True)
    response=fetch("https://freetsa.org/tsr",(d/"request.tsq").read_bytes())
    (d/"response.tsr").write_bytes(response)
    for mode,file in (("-queryfile","request.tsq"),("-data","synthetic.txt")):
        ssl("ts","-verify","-in","response.tsr",mode,file,"-CAfile","cacert.pem","-untrusted","tsa.crt")
    print("RFC3161_VERIFICA_QUERY_E_DATI=OK")
    info=ssl("ts","-reply","-in","response.tsr","-text").decode("ascii",errors="replace")
    for line in info.splitlines():
        if line.startswith("Time stamp:"):print(line)
    print("REVOCA_NON_VERIFICATA")
    print("PROSPECTIVE_ADMITTED=NO")
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("TSA_STOP",type(e).__name__);sys.exit(2)
