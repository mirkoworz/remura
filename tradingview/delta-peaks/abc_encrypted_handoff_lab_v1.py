# REMURA v0.8.139 LAB — 17/11/2026 17:27 CET
"""Synthetic encrypted handoff using GnuPG, no live data or recovery keys."""
import hashlib,io,json,os,re,subprocess,zipfile
from abc_sqlite_backup_lab_v1 import NAMES,MAX
from abc_overlay_transaction_lab_v1 import need
LIMIT=2*MAX+65536
HEX=re.compile(r"[0-9a-f]{64}\Z")
FPR=re.compile(r"[0-9A-F]{40}\Z")
def sha(b):return hashlib.sha256(b).hexdigest()
def gpg(home,*args,data=None,ok=True):
    env={"PATH":os.environ["PATH"],"HOME":str(home),"LANG":"C","LC_ALL":"C"}
    r=subprocess.run(["gpg","--no-options","--homedir",str(home),"--batch","--no-tty",
                      "--no-auto-key-retrieve","--auto-key-locate","local",
                      "--pinentry-mode","loopback","--passphrase","",*args],
                     input=data,capture_output=True,env=env,timeout=30)
    if ok:need(r.returncode==0)
    return r
def identity(home,label):
    need(label in ("recovery","wrong"))
    gpg(home,"--quick-generate-key",f"REMURA synthetic {label} <{label}@example.invalid>","rsa2048","encr","0")
    rows=gpg(home,"--with-colons","--list-keys").stdout.decode().splitlines()
    fingerprints=[row.split(":")[9] for row in rows if row.startswith("fpr:")]
    need(len(fingerprints)==1 and FPR.fullmatch(fingerprints[0]))
    return fingerprints[0]
def archive(fixture,manifest):
    with io.BytesIO() as out:
        with zipfile.ZipFile(out,"w",compression=zipfile.ZIP_STORED) as z:
            z.writestr("manifest.json",json.dumps(manifest,sort_keys=True,separators=(",",":")))
            for name in NAMES:
                body=fixture.path("snapshot",name).read_bytes()
                need(0<len(body)<=MAX and sha(body)==manifest["files"][name]["sha256"])
                z.writestr(name,body)
        b=out.getvalue()
    need(len(b)<=LIMIT)
    return b
def seal(sender,recipient,body,*,synthetic=False):
    need(synthetic is True and FPR.fullmatch(recipient) and 0<len(body)<=LIMIT)
    need(not any(l.startswith(b"sec:") for l in gpg(sender,"--with-colons","--list-secret-keys").stdout.splitlines()))
    r=gpg(sender,"--trust-model","always","--cipher-algo","AES256","--compress-algo","none",
          "--force-mdc","--recipient",recipient+"!","--encrypt","--output","-",data=body)
    need(0<len(r.stdout)<=LIMIT+65536)
    return r.stdout
def witness(cipher,manifest_pin,generation,recipient):
    need(HEX.fullmatch(manifest_pin) and type(generation) is int and generation>=1 and FPR.fullmatch(recipient))
    return {"schema":"remura.abc.synthetic.recovery.witness.v1","cipher_sha256":sha(cipher),
            "manifest_sha256":manifest_pin,"generation":generation,"recipient":recipient}
def recover(receiver,cipher,expected,fixture,*,generation,recipient,synthetic=False):
    need(synthetic is True and 0<len(cipher)<=LIMIT+65536)
    need(type(expected) is dict and expected==witness(cipher,expected.get("manifest_sha256",""),generation,recipient))
    # No decrypted bytes are passed to parser or returned until GPG has verified MDC.
    r=gpg(receiver,"--status-fd","2","--decrypt","--output","-",data=cipher,ok=False)
    need(r.returncode==0 and b"[GNUPG:] DECRYPTION_OKAY" in r.stderr and b"[GNUPG:] GOODMDC" in r.stderr)
    need(0<len(r.stdout)<=LIMIT)
    with zipfile.ZipFile(io.BytesIO(r.stdout)) as z:
        infos=z.infolist()
        need(len(infos)==3 and {x.filename for x in infos}=={"manifest.json",*NAMES})
        need(all(not x.is_dir() and x.compress_type==zipfile.ZIP_STORED and 0<x.file_size<=MAX for x in infos))
        need(z.getinfo("manifest.json").file_size<=16384)
        m=json.loads(z.read("manifest.json"))
        need(m.get("schema")=="remura.abc.synthetic.sqlite.snapshot.v1" and m.get("manifest_sha256")==expected["manifest_sha256"])
        rows=m.get("files");need(type(rows) is dict and set(rows)==set(NAMES))
        need(sha(json.dumps(rows,sort_keys=True,separators=(",",":")).encode())==expected["manifest_sha256"])
        bodies={name:z.read(name) for name in NAMES}
        need(all(sha(bodies[n])==rows[n]["sha256"] and len(bodies[n])==rows[n]["bytes"] for n in NAMES))
    need(not any((fixture.root/"snapshot").iterdir()) and not any((fixture.root/"restore").iterdir()))
    for n,b in bodies.items():
        p=fixture.path("snapshot",n)
        with p.open("xb") as f:f.write(b)
        p.chmod(0o600)
    result=fixture.restore(m,expected["manifest_sha256"])
    return {**result,"synthetic_encryption_verified":True,"independent_live_custody_verified":False}
