"""V30.8 staging, only immutable GitHub source downloads and synthetic tests.
No network access to financial providers or timestamp authority.
"""
import os,sys,hashlib,unittest,json,time,stat
from pathlib import Path
from urllib.request import urlopen
BASE=Path.home()/".remura-v296";LAB=BASE/"v308"
REF="b76dd0569878d34594bf43e6c0faa05a64e066c5"
NEW={
"v306_observation_prepare.py":"311ab9dc1651c0ba8275ce52c0bdf9cfd26bbcc0",
"v308_observation_assemble.py":"fd41bd6ea4e8fafbc8f9194e05cda687afdb5837",
"v308_queue.py":"c41e07f7d69e8074e8ebf021393175c1d4980566",
"v308_history.py":"2be1fab1c30b0ebeefa9245bb7cd77c7f842f5a6",
"v308_pilot.py":"a7aae69e98d97b8b5d1b48c8f51eee58d9775f8b",
"test_v308_pilot.py":"3f30309d2a56f3b600ffe2d8020ee0407cab5dc2"
}
EXISTING={
"v297_bounded_collector.py":"fb05f7143de6d320dcba2b9aad59f3c74c7cee75",
"v294_footprint_cvd.py":"b74b152a72fb824cf65a1e0ce470d243549671fc",
"v301/v299_source_correlation.py":"1c9241a477f93a6f0851c6701a6a3105550478a0",
"v301/v303_science_candidate.py":"5600a8db0db3cace2fa909a5551c05daf89e649d",
"v301/v300_paired_outcomes.py":"a85c703d55f6eef8f0faa38f746c27a816f61027",
"v305/v304_local_freeze.py":"38ca7e3054982fe5d6329e36cffc72310ced62a4",
"v301/v303-public-cot.json":"32a83a644f12c670f61247bfbc1d0c22e61356be"
}
def private(p,d=False):
    s=p.lstat()
    if not (stat.S_ISDIR(s.st_mode) if d else stat.S_ISREG(s.st_mode)) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=(0o700 if d else 0o600):raise ValueError("permissions")
def verify(data,h):
    if len(data)>100000 or hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()!=h:raise ValueError("hash")
def run():
    os.umask(0o077)
    if os.getuid()==0:raise ValueError("not_root")
    for p in (BASE,BASE/"v301",BASE/"v305"):private(p,True)
    LAB.mkdir(mode=0o700,exist_ok=True);private(LAB,True)
    for n in ("permit.json","science.sqlite3","STOP"):
        if os.path.lexists(LAB/n):raise ValueError("already_prepared")
    for name,h in EXISTING.items():
        target=BASE/name;private(target);verify(target.read_bytes(),h)
    for name,h in NEW.items():
        target=LAB/name
        if os.path.lexists(target):
            private(target);data=target.read_bytes()
        else:
            url="https://raw.githubusercontent.com/mirkoworz/remura/"+REF+"/research/"+name
            with urlopen(url,timeout=15) as f:data=f.read(100001)
        verify(data,h);compile(data,name,"exec")
        if not target.exists():
            with target.open("xb") as f:f.write(data)
    print("V308_NUOVI_FILE=6/6 DIPENDENZE=7/7",flush=True)
    sys.path[:0]=[str(LAB),str(BASE/"v305"),str(BASE/"v301"),str(BASE)]
    suite=unittest.defaultTestLoader.loadTestsFromName("test_v308_pilot")
    res=unittest.TextTestRunner(verbosity=1).run(suite)
    if not res.wasSuccessful() or res.testsRun!=5:raise ValueError("tests")
    print("V308_NUOVI_TEST=5/5",flush=True)
    import v308_pilot
    start=int(time.time()*1000)
    with (LAB/"permit.json").open("x") as f:
        json.dump({"enabled":True,"start_ms":start,"end_ms":start+1800000},f)
        f.flush();os.fsync(f.fileno())
    print("V308_PREFLIGHT_OK",flush=True)
if __name__=="__main__":
    try:run()
    except Exception as e:
        print("V308 PREFLIGHT STOP",type(e).__name__,flush=True);sys.exit(2)
