# REMURA v0.8.96 LAB — 16/11/2026 13:46 CET
"""Single-commit cache + first-observation archive rehearsal, synthetic only.

One bounded canonical file, one rename, an independently simulated reservation.
No real archive, encrypted storage, recovery or automatic collection.
"""
import json,os,stat,secrets
from contextlib import contextmanager
from collections import defaultdict
from cvd_incremental_pinned_v1 import SyntheticCustody,Pin
from cvd_incremental_persistence_v1 import validate as validate_cache,FILE_BYTES as CACHE_BYTES
from cvd_incremental_preview_v1 import RollingPreview,repage,checked_cutoff
from cvd_first_observation_ledger_v1 import Ledger,verify,MAX_BYTES as ARCHIVE_BYTES,MAX_CYCLES
from cvd_private_runtime_preview_v1 import preview
from cvd_runtime_private_state_v1 import encoded,digest,_private,_no_duplicates,PERIOD,DELAY
from cvd_runtime_singleflight_v1 import single_flight
from cvd_telemetry_preview_v1 import M5
NAME="remura-d-joint-synthetic-v1.json"
TMP=".remura-d-joint-synthetic-"
SCHEMA="remura.tv.joint.synthetic.v1"
MAX_FILE=CACHE_BYTES+ARCHIVE_BYTES+8192
def need(ok):
    if not ok:raise ValueError("synthetic_joint_denied")

class JointCustody(SyntheticCustody):
    """Distinct synthetic authority domain, not durable or externally secured."""

def ledger_from(s):
    a=s["archive"]
    need(type(a) is dict and set(a)=={"first_cutoff","cycles","records","head"})
    need(type(a["records"]) is list and 1<=len(a["records"])<=MAX_CYCLES)
    raw=tuple(encoded(x) for x in a["records"])
    summary=verify(cohort=s["generation"],first_cutoff=a["first_cutoff"],cycles=a["cycles"],
                   records=raw,expected_head=a["head"],synthetic=True)
    l=Ledger(cohort=s["generation"],first_cutoff=a["first_cutoff"],cycles=a["cycles"],synthetic=True)
    for w in a["records"]:
        b=w["record"]
        # The standalone ledger can describe gaps, but this joint runtime
        # cannot advance a valid consecutive rolling cache across one.
        need(b["kind"]=="OBSERVED")
        l.observe(cutoff=b["cutoff_ms"],window=b["window"])
    need(l.summary()==summary)
    return l

def groups(windows,low,high):
    out=defaultdict(list)
    for w in windows:
        for r in w["rows"]:
            t=r["bar_close_ms"]
            if low<=t<=high:out[t].append(encoded(r))
    return {t:sorted(v) for t,v in out.items()}

def validate(s,generation):
    need(type(s) is dict and set(s)=={"schema","generation","cache","archive"})
    need(s["schema"]==SCHEMA and s["generation"]==generation)
    c=s["cache"];validate_cache(c)
    last=c["last"];need(last is not None and last["cutoff_ms"]==c["claim_ms"])
    a=s["archive"];ledger=ledger_from(s);summary=ledger.summary()
    need(last["bootstrap_ms"]==a["first_cutoff"])
    need(c["claim_ms"]==a["first_cutoff"]+(summary["cycles_recorded"]-1)*PERIOD)
    ranges=checked_cutoff(c["claim_ms"])
    low=max(ranges[0][0],a["first_cutoff"]-DELAY-2*M5);high=ranges[-1][1]
    archived=[x["record"]["window"] for x in a["records"]]
    # Match complete row multisets across every overlapping slot; absent rows
    # compare as empty. The older bootstrap cache is not scientific history.
    need(groups(last["windows"],low,high)==groups(archived,low,high))
    return ledger

def make_state(generation,rolling,core,ledger,boot,cutoff,cycles):
    output=preview(core,rolling._windows,now=cutoff,origin="SYNTHETIC")
    records=[json.loads(x) for x in ledger.synthetic_records(explicit=True)]
    return {"schema":SCHEMA,"generation":generation,
            "cache":{"schema":"remura.tv.incremental.persistence.synthetic.v1","claim_ms":cutoff,
                     "last":{"cutoff_ms":cutoff,"bootstrap_ms":boot,"windows":rolling._windows,"preview":output}},
            "archive":{"first_cutoff":boot,"cycles":cycles,"records":records,"head":ledger.summary()["head"]}}

class Joint:
    filename=NAME
    prefix=TMP
    def file_limit(self):return MAX_FILE
    def encode_file(self,plain):return plain
    def decode_file(self,raw):return raw
    def __init__(self,fd,guard,custody,generation):
        self.fd=fd;self.guard=guard;self.c=custody;self.g=generation;self.failed=False
    def check(self):
        need(not self.failed);self.guard()
        need(not any(n.startswith(self.prefix) for n in os.listdir(self.fd)))
    def authority(self,p,phase):
        need(type(p) is Pin and p==self.c.latest() and p.generation==self.g and p.phase==phase)
    def read(self):
        self.check()
        f=os.open(self.filename,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        try:
            st=os.fstat(f);_private(st,stat.S_ISREG)
            need(st.st_nlink==1 and 1<=st.st_size<=self.file_limit())
            with os.fdopen(os.dup(f),"rb") as stream:raw=stream.read(self.file_limit()+1)
            need(len(raw)==st.st_size)
            raw=self.decode_file(raw)
            need(1<=len(raw)<=MAX_FILE)
            w=json.loads(raw,object_pairs_hook=_no_duplicates)
            need(type(w) is dict and set(w)=={"state","sha256"} and w["sha256"]==digest(w["state"]) and encoded(w)==raw)
            l=validate(w["state"],self.g)
            return w["state"],l
        finally:os.close(f)
    def write(self,s):
        self.check();validate(s,self.g)
        raw=encoded({"state":s,"sha256":digest(s)})
        need(len(raw)<=MAX_FILE)
        raw=self.encode_file(raw)
        need(1<=len(raw)<=self.file_limit())
        tmp=self.prefix+secrets.token_hex(16)
        try:
            f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
            with os.fdopen(f,"wb") as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.guard()
            os.replace(tmp,self.filename,src_dir_fd=self.fd,dst_dir_fd=self.fd)
            os.fsync(self.fd)
        except BaseException:
            self.failed=True
            raise
    def describe(self,s,l):
        at=s["cache"]["claim_ms"]
        return {"status":"CURRENT_SYNTHETIC","claim_ms":at,"last_cutoff_ms":at,
                "state_digest":digest(s),"preview":s["cache"]["last"]["preview"],"archive":l.summary(),
                "publication_commitment":"CACHE_AND_ARCHIVE_SAME_DIGEST","scientific_admission":False,
                "independent_rollback_protection":False}
    def status(self,p):
        self.authority(p,"STABLE")
        s,l=self.read();result=self.describe(s,l)
        need(result["state_digest"]==p.state_digest and result["claim_ms"]==p.cutoff_ms)
        self.authority(p,"STABLE")
        return result
    def publish(self,pending,s):
        self.authority(pending,"PENDING")
        self.write(s)
        check,l=self.read()
        need(digest(check)==digest(s))
        stable=self.c.finalize(pending,self.describe(check,l))
        return stable,self.status(stable)
    def bootstrap(self,core,*,expected,cutoff,windows,cycles):
        self.authority(expected,"GENESIS");self.check()
        try:os.stat(self.filename,dir_fd=self.fd,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise ValueError("synthetic_joint_existing")
        pending=self.c.reserve(expected,cutoff)
        rolling=RollingPreview(now=cutoff,windows=windows,synthetic=True)
        l=Ledger(cohort=self.g,first_cutoff=cutoff,cycles=cycles,synthetic=True)
        end=cutoff-DELAY
        rows=[r for w in rolling._windows for r in w["rows"]]
        l.observe(cutoff=cutoff,window=repage([(end-2*M5,end)],rows)[0])
        return self.publish(pending,make_state(self.g,rolling,core,l,cutoff,cutoff,cycles))
    def cycle(self,core,*,expected,cutoff,windows):
        self.authority(expected,"STABLE");self.status(expected)
        s,l=self.read();need(digest(s)==expected.state_digest)
        a=s["archive"]
        need(l.summary()["cycles_recorded"]<a["cycles"] and cutoff==expected.cutoff_ms+PERIOD)
        pending=self.c.reserve(expected,cutoff)
        last=s["cache"]["last"]
        rolling=RollingPreview(now=last["cutoff_ms"],windows=last["windows"],synthetic=True)
        rolling.advance(now=cutoff,windows=windows)
        need(len(windows)==1)
        l.observe(cutoff=cutoff,window=windows[0])
        return self.publish(pending,make_state(self.g,rolling,core,l,a["first_cutoff"],cutoff,a["cycles"]))

@contextmanager
def open_joint(root,custody,*,generation,synthetic=False):
    need(synthetic is True and type(custody) is JointCustody and custody.latest().generation==generation)
    fd=os.open(root,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
    try:
        st=os.fstat(fd);_private(st,stat.S_ISDIR);identity=(st.st_dev,st.st_ino)
        with single_flight(root) as held:
            def guard():
                held()
                current=os.stat(root,follow_symlinks=False);_private(current,stat.S_ISDIR)
                need((current.st_dev,current.st_ino)==identity)
            guard()
            yield Joint(fd,guard,custody,generation)
    finally:os.close(fd)
