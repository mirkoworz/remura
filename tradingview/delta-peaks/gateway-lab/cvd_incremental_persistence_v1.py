# REMURA v0.8.92 LAB — 16/11/2026 13:13 CET
"""Isolated synthetic persistence rehearsal. No live adapter or network.

One bounded atomic file combines claim, last complete cache and sanitized preview.
Not the production state format; no scientific archive or independent rollback pin.
A pending or ambiguous claim requires explicit investigation, never auto-retry.
"""
import json,os,stat,secrets
from contextlib import contextmanager
from copy import deepcopy
from cvd_runtime_singleflight_v1 import single_flight
from cvd_runtime_private_state_v1 import encoded,digest,_private,_no_duplicates,notice_digest,DELAY,PERIOD
from cvd_incremental_preview_v1 import RollingPreview,checked_cutoff,MAX_BYTES
from cvd_private_runtime_preview_v1 import preview

NAME="remura-d-incremental-synthetic-v1.json"
TMP_PREFIX=".remura-d-incremental-synthetic-"
SCHEMA="remura.tv.incremental.persistence.synthetic.v1"
PREVIEW_BYTES=256*1024
FILE_BYTES=MAX_BYTES+PREVIEW_BYTES+4096

def require(ok):
    if not ok:raise ValueError("incremental_storage_denied")

def validate(s):
    require(type(s) is dict and set(s)=={"schema","claim_ms","last"})
    require(s["schema"]==SCHEMA)
    claim=s["claim_ms"]
    checked_cutoff(claim)
    last=s["last"]
    if last is None:return
    require(type(last) is dict and set(last)=={"cutoff_ms","bootstrap_ms","windows","preview"})
    at,boot=last["cutoff_ms"],last["bootstrap_ms"]
    expected=checked_cutoff(at);checked_cutoff(boot)
    require(boot<=at<=claim and claim-at in (0,PERIOD) and (at-boot)%PERIOD==0)
    rolling=RollingPreview(now=at,windows=last["windows"],synthetic=True)
    # Original admission time follows from consecutive fixed cutoffs. Missing rows
    # are not reconstructed; no proof of first-seen against a malicious writer.
    for page in last["windows"]:
        for row in page["rows"]:
            delta=row["bar_close_ms"]-(boot-DELAY)
            admitted=boot+max(0,(delta+PERIOD-1)//PERIOD)*PERIOD
            require(row["received_at_ms"]<=admitted<=at)
    p=last["preview"]
    require(type(p) is dict and set(p)=={"schema","version","origin","status","html","notice","coverage","raw_export_returned","independent_provenance","notifications_enabled","orders_enabled","edge"})
    require(p["schema"]=="remura.tv.private.runtime.preview.v1" and p["origin"]=="SYNTHETIC" and p["status"]=="LOCAL_PREVIEW_ONLY" and p["edge"]=="NOT_ESTABLISHED")
    require(all(p[k] is False for k in ("raw_export_returned","independent_provenance","notifications_enabled","orders_enabled")))
    require(type(p["html"]) is str and p["html"].startswith("<!doctype html>") and "DATI SINTETICI" in p["html"])
    require(all(p["notice"].get(k) is False for k in ("would_send","sent","orders_enabled")))
    notice_digest(p["notice"])
    summary=rolling.summary()
    c=p["coverage"]
    require(type(c) is dict and set(c)=={"requested_slots","valid_unique_bars","missing_requested_slots","first_requested_close_ms","last_requested_close_ms","basis","latest_immature_bars_not_queried","legacy_fxcm_export_supplied","scientific_benchmarks_computed"})
    require(all(type(c[k]) is int and c[k]==summary[k] for k in ("requested_slots","valid_unique_bars","missing_requested_slots")))
    require(c["first_requested_close_ms"]==expected[0][0] and c["last_requested_close_ms"]==expected[-1][1] and c["basis"]=="MATURE_REQUESTED_SLOTS_NOT_MARKET_CALENDAR")
    require(c["latest_immature_bars_not_queried"] is True and c["legacy_fxcm_export_supplied"] is False and c["scientific_benchmarks_computed"] is False)
    require(len(encoded(last["windows"]))<=MAX_BYTES and len(encoded(p))<=PREVIEW_BYTES)

class Store:
    def __init__(self,fd,guard):
        self.fd=fd;self.guard=guard;self.failed=False
    def _check(self):
        require(not self.failed)
        self.guard()
        # An orphan candidate is an ambiguous interrupted write. Do not delete it
        # or generate more files; this bounded rehearsal stops for inspection.
        require(not any(n.startswith(TMP_PREFIX) for n in os.listdir(self.fd)))
    def _read(self):
        self._check()
        f=os.open(NAME,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        try:
            st=os.fstat(f);_private(st,stat.S_ISREG)
            require(st.st_nlink==1 and 1<=st.st_size<=FILE_BYTES)
            with os.fdopen(os.dup(f),"rb") as stream:raw=stream.read(FILE_BYTES+1)
            require(len(raw)==st.st_size)
            w=json.loads(raw,object_pairs_hook=_no_duplicates)
            require(type(w) is dict and set(w)=={"state","sha256"} and w["sha256"]==digest(w["state"]) and encoded(w)==raw)
            validate(w["state"])
            return w["state"]
        finally:os.close(f)
    def _write(self,s):
        self._check();validate(s)
        raw=encoded({"state":s,"sha256":digest(s)})
        require(len(raw)<=FILE_BYTES)
        tmp=TMP_PREFIX+secrets.token_hex(16)
        # Any write failure poisons this open handle. A surviving orphan blocks
        # future handles. After rename an uncertain fsync is resolved only by
        # explicit readback; no automatic retry.
        try:
            f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
            with os.fdopen(f,"wb") as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.guard()
            os.replace(tmp,NAME,src_dir_fd=self.fd,dst_dir_fd=self.fd)
            os.fsync(self.fd)
        except BaseException:
            self.failed=True
            raise
    def initialize(self,cutoff):
        self._check();checked_cutoff(cutoff)
        try:os.stat(NAME,dir_fd=self.fd,follow_symlinks=False)
        except FileNotFoundError:pass
        else:raise ValueError("incremental_already_initialized")
        self._write({"schema":SCHEMA,"claim_ms":cutoff,"last":None})
    def status(self):
        s=self._read();last=s["last"]
        current=last is not None and last["cutoff_ms"]==s["claim_ms"]
        return {"status":"CURRENT_SYNTHETIC" if current else "INCOMPLETE_CLAIM",
                "claim_ms":s["claim_ms"],"last_cutoff_ms":last["cutoff_ms"] if last else None,
                "preview":deepcopy(last["preview"]) if last else None,
                "state_digest":digest(s),"scientific_admission":False,
                "independent_rollback_protection":False}
    def claim(self,cutoff):
        checked_cutoff(cutoff);s=self._read();last=s["last"]
        if cutoff==s["claim_ms"]:return False
        require(last is not None and last["cutoff_ms"]==s["claim_ms"] and cutoff==s["claim_ms"]+PERIOD)
        s["claim_ms"]=cutoff;self._write(s);return True
    def complete(self,core,*,cutoff,windows):
        s=self._read();last=s["last"]
        require(cutoff==s["claim_ms"] and (last is None or last["cutoff_ms"]!=cutoff))
        if last is None:
            rolling=RollingPreview(now=cutoff,windows=windows,synthetic=True);boot=cutoff
        else:
            rolling=RollingPreview(now=last["cutoff_ms"],windows=last["windows"],synthetic=True)
            rolling.advance(now=cutoff,windows=windows);boot=last["bootstrap_ms"]
        output=preview(core,rolling._windows,now=cutoff,origin="SYNTHETIC")
        s["last"]={"cutoff_ms":cutoff,"bootstrap_ms":boot,"windows":rolling._windows,"preview":output}
        self._write(s)
        return self.status()

@contextmanager
def open_store(root,*,synthetic=False):
    require(synthetic is True)
    # Existing lock, no separate scheduler/lock. Root identity also checked before
    # committing. Trusted private fixture directory only, not adversarial UID.
    fd=os.open(root,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
    try:
        st=os.fstat(fd);_private(st,stat.S_ISDIR)
        identity=(st.st_dev,st.st_ino)
        with single_flight(root) as held:
            def guard():
                held()
                current=os.stat(root,follow_symlinks=False)
                _private(current,stat.S_ISDIR)
                require((current.st_dev,current.st_ino)==identity)
            guard()
            yield Store(fd,guard)
    finally:os.close(fd)
