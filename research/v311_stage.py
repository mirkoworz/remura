"""V31.1 LAB staging. Only public GitHub source downloads; new synthetic tests.
No market provider requests and no writes to previous archives.
"""
import hashlib,json,os,stat,sys,time,unittest,shutil
from pathlib import Path
from urllib.request import urlopen
BASE=Path.home()/".remura-v296";LAB=BASE/"v311"
SCI="5592e5d82e99126af9173ce8ea26cbf144ff1096"
CME="8855d7854d9e88a425702a709f56e792a2f28dd5"
FILES={
"v311_science.py":(SCI,"fead3f5779b66198a79ecc2690cb805c33017928"),
"v311_pilot.py":(SCI,"b1e05ce8414494980305a2abb8a92534574de103"),
"test_v311_science.py":(SCI,"90d6c6037fadac2ce107d858cf003e537502356b"),
"v310_multifeed.py":(SCI,"aba14a0d7d19e92eeb2af542d4432308fa33c5c3"),
"v310_science_adapter.py":(SCI,"838709c4952a0d843e61f79fc5aa134c2f644165"),
"v294_footprint_cvd.py":(SCI,"b74b152a72fb824cf65a1e0ce470d243549671fc"),
"v299_source_correlation.py":(SCI,"1c9241a477f93a6f0851c6701a6a3105550478a0"),
"v300_paired_outcomes.py":(SCI,"a85c703d55f6eef8f0faa38f746c27a816f61027"),
"v303_science_candidate.py":(SCI,"5600a8db0db3cace2fa909a5551c05daf89e649d"),
"v311_futures_window.py":(CME,"123746a60cdd06c87cfb1966aab153f59d965ec2"),
"test_v311_futures_window.py":(CME,"6f68b7f7336020f714f30866e5233f875f01288f"),
"v310_cme_contract.py":(CME,"44ab0886bd074c870e0aaecd2980c5171ca3d49d")}
def private(p,d=False):
    s=p.lstat()
    if not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600):raise ValueError("permissions")
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,BASE/"v301"):private(p,True)
    for p in (BASE/"tv-custody.sqlite3",BASE/"v301"/"v303-public-cot.json"):private(p)
    if shutil.disk_usage(BASE).free<512*1024*1024:raise ValueError("disk")
    LAB.mkdir(mode=0o700,exist_ok=True);private(LAB,True)
    for n in ("permit.json","science-tv.sqlite3","STOP","manifest.json"):
        if os.path.lexists(LAB/n):raise ValueError("already_prepared")
    manifest={}
    for n,(ref,h) in FILES.items():
        p=LAB/n
        if os.path.lexists(p):
            private(p);data=p.read_bytes()
        else:
            with urlopen("https://raw.githubusercontent.com/mirkoworz/remura/"+ref+"/research/"+n,timeout=15) as f:data=f.read(100001)
        if len(data)>100000 or hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=h:raise ValueError("hash")
        compile(data,n,"exec")
        if not p.exists():
            with p.open("xb") as f:f.write(data)
        manifest[n]=hashlib.sha256(data).hexdigest()
    print("V311_FILE_VERIFICATI=12/12",flush=True)
    sys.path.insert(0,str(LAB))
    suite=unittest.defaultTestLoader.loadTestsFromNames(["test_v311_science","test_v311_futures_window"])
    res=unittest.TextTestRunner(verbosity=1).run(suite)
    if not res.wasSuccessful() or res.testsRun!=8:raise ValueError("tests")
    print("V311_NUOVI_TEST=8/8",flush=True)
    with (LAB/"manifest.json").open("x") as f:json.dump(manifest,f,sort_keys=True);f.flush();os.fsync(f.fileno())
    start=int(time.time()*1000)
    with (LAB/"permit.json").open("x") as f:json.dump({"enabled":True,"start_ms":start,"end_ms":start+10800000},f);f.flush();os.fsync(f.fileno())
    print("V311_PREFLIGHT_OK",flush=True)
if __name__=="__main__":
    try:run()
    except Exception as e:print("V311 PREFLIGHT STOP",type(e).__name__,flush=True);sys.exit(2)
