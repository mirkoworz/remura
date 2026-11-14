#!/usr/bin/env python3
# REMURA v0.8.83 LAB — 14/11/2026 20:31 CET
"""Bounded private local state, for a single configured TEST runtime.
Caller holds the stable single-flight lock for the entire transaction.
No history, raw exports, secrets, transport, or automatic retry.
"""
import os,stat,json,secrets
from hashlib import sha256
from contextlib import contextmanager
from datetime import datetime,timezone
from zoneinfo import ZoneInfo

NAME="remura-d-preview-state-v1.json"
SCHEMA="remura.tv.private.preview.state.v1"
MAX_BYTES=256*1024
PERIOD=900000
DELAY=180000

def bucket(now):
    if type(now) is not int or now<1000000000000:raise ValueError("state_clock")
    return (now-DELAY)//PERIOD*PERIOD+DELAY

def encoded(obj):
    return json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def digest(obj):return sha256(encoded(obj)).hexdigest()

def _private(s,kind):
    if not kind(s.st_mode) or s.st_uid!=os.geteuid() or s.st_mode&0o077:
        raise ValueError("state_permissions")

def _no_duplicates(items):
    result={}
    for k,v in items:
        if k in result:raise ValueError("state_duplicate_key")
        result[k]=v
    return result

def _check_record(r):
    if (type(r) is not dict or set(r)!={"cutoff_ms","html","notice","coverage","diagnostic_content_sha256","completed_ms"} or
        type(r["cutoff_ms"]) is not int or bucket(r["cutoff_ms"])!=r["cutoff_ms"] or
        type(r["completed_ms"]) is not int or r["completed_ms"]<r["cutoff_ms"] or
        type(r["html"]) is not str or not r["html"].startswith("<!doctype html>") or
        type(r["notice"]) is not dict or type(r["coverage"]) is not dict or
        any(r["notice"].get(k) is not False for k in ("would_send","sent","orders_enabled")) or
        r["diagnostic_content_sha256"]!=notice_digest(r["notice"])):
        raise ValueError("state_record_invalid")

def notice_digest(n):
    # Not an event identity. Same aggregate content across intervals is only
    # a diagnostic equivalence; different underlying decisions may coexist.
    keys={"schema","notice_id","state","text","candidate_count","tv_cvd_match_count","tv_cvd_reasons","auxiliary_summary","would_send","sent","orders_enabled"}
    if type(n) is not dict or set(n)!=keys or n["schema"]!="remura.tv.diagnostic.notice.preview.v1":
        raise ValueError("state_notice_invalid")
    return digest({k:v for k,v in n.items() if k!="notice_id"})

def _validate(s,origin):
    if (type(s) is not dict or set(s)!={"schema","origin","claim_ms","last_success"} or
        s["schema"]!=SCHEMA or s["origin"]!=origin or
        (s["claim_ms"] is not None and (type(s["claim_ms"]) is not int or bucket(s["claim_ms"])!=s["claim_ms"]))):
        raise ValueError("state_invalid")
    if s["last_success"] is not None:
        _check_record(s["last_success"])
        if s["claim_ms"] is None or s["last_success"]["cutoff_ms"]>s["claim_ms"]:
            raise ValueError("state_claim_order")
    return s

class State:
    def __init__(self,fd,origin,guard):
        self.fd=fd;self.origin=origin;self.guard=guard
    def read(self):
        self.guard()
        try:f=os.open(NAME,os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=self.fd)
        except FileNotFoundError:
            return {"schema":SCHEMA,"origin":self.origin,"claim_ms":None,"last_success":None}
        try:
            st=os.fstat(f);_private(st,stat.S_ISREG)
            if st.st_nlink!=1 or not 1<=st.st_size<=MAX_BYTES:raise ValueError("state_file_invalid")
            with os.fdopen(os.dup(f),"rb") as stream:raw=stream.read(MAX_BYTES+1)
            if len(raw)!=st.st_size:raise ValueError("state_size_changed")
            wrapper=json.loads(raw,object_pairs_hook=_no_duplicates)
            if type(wrapper) is not dict or set(wrapper)!={"state","sha256"} or wrapper["sha256"]!=digest(wrapper["state"]):
                raise ValueError("state_digest_invalid")
            return _validate(wrapper["state"],self.origin)
        finally:os.close(f)
    def write(self,s):
        self.guard();_validate(s,self.origin)
        raw=encoded({"state":s,"sha256":digest(s)})
        if len(raw)>MAX_BYTES:raise ValueError("state_max_bytes")
        tmp=".remura-d-state-"+secrets.token_hex(16)
        f=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600,dir_fd=self.fd)
        try:
            with os.fdopen(f,"wb") as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
            self.guard()
            os.replace(tmp,NAME,src_dir_fd=self.fd,dst_dir_fd=self.fd)
            os.fsync(self.fd)
        finally:
            # Only own uncommitted temporary file; completed state never removed.
            try:os.unlink(tmp,dir_fd=self.fd)
            except FileNotFoundError:pass
    def claim(self,cutoff):
        s=self.read()
        prior=s["claim_ms"]
        if prior is not None and cutoff<prior:raise ValueError("state_clock_regression")
        if cutoff==prior:return False
        s["claim_ms"]=cutoff;self.write(s)
        return True
    def complete(self,cutoff,result,*,now):
        s=self.read()
        if s["claim_ms"]!=cutoff or (s["last_success"] and s["last_success"]["cutoff_ms"]==cutoff):
            raise ValueError("state_claim_mismatch")
        if (type(result) is not dict or result.get("schema")!="remura.tv.private.runtime.preview.v1" or
            result.get("status")!="LOCAL_PREVIEW_ONLY" or result.get("origin")!=self.origin or
            any(result.get(k) is not False for k in ("raw_export_returned","notifications_enabled","orders_enabled")) or
            result.get("edge")!="NOT_ESTABLISHED"):
            raise ValueError("state_preview_invalid")
        notice=result["notice"];fingerprint=notice_digest(notice)
        coverage=result["coverage"]
        if set(coverage)!={"requested_slots","valid_unique_bars","missing_requested_slots","first_requested_close_ms","last_requested_close_ms","basis","latest_immature_bars_not_queried","legacy_fxcm_export_supplied","scientific_benchmarks_computed"}:
            raise ValueError("state_coverage_shape")
        if (coverage["last_requested_close_ms"]!=cutoff-DELAY or
            coverage["scientific_benchmarks_computed"] is not False or
            any(type(coverage[k]) is not int or coverage[k]<0 for k in ("requested_slots","valid_unique_bars","missing_requested_slots")) or
            coverage["valid_unique_bars"]+coverage["missing_requested_slots"]!=coverage["requested_slots"]):
            raise ValueError("state_coverage_invalid")
        html=result["html"]
        old="v0.8.75 LAB | 14/11/2026 CET | Anteprima offline"
        if type(html) is not str or html.count(old)!=1 or html.count("<title>REMURA LAB — 0.8.75</title>")!=1:
            raise ValueError("state_html_version")
        stamp=datetime.fromtimestamp(now/1000,tz=timezone.utc).astimezone(ZoneInfo("Europe/Rome")).strftime("%d/%m/%Y %H:%M:%S %Z")
        html=html.replace(old,"v0.8.83 LAB | "+stamp+" | Anteprima privata non LIVE").replace("<title>REMURA LAB — 0.8.75</title>","<title>REMURA LAB — 0.8.83</title>")
        previous=s["last_success"]
        same=previous is not None and previous["diagnostic_content_sha256"]==fingerprint
        s["last_success"]={"cutoff_ms":cutoff,"completed_ms":now,"html":html,"notice":notice,
                           "coverage":coverage,"diagnostic_content_sha256":fingerprint}
        self.write(s)
        return {"diagnostic_aggregate_unchanged":same,"notice_sent":False}

@contextmanager
def open_state(root,*,origin,guard,explicit=False):
    if explicit is not True or origin not in ("LOCAL_SNAPSHOT","SYNTHETIC") or not callable(guard):
        raise ValueError("private_state_explicit_required")
    fd=os.open(root,os.O_RDONLY|os.O_NOFOLLOW|os.O_DIRECTORY)
    try:
        _private(os.fstat(fd),stat.S_ISDIR)
        yield State(fd,origin,guard)
    finally:os.close(fd)
