#!/usr/bin/env python3
# REMURA v0.8.78 LAB — 14/11/2026 18:00 CET
"""Conservative preflight for one private TEST preview, NOT a live admission gate.
Caller must supply genuine recent local host and account evidence.
No network here except the explicitly delegated existing read-only collector.
Adaptive analytics are not exact billing; no tamper-proof attestations.
"""
from datetime import datetime,timezone
from math import isfinite
import re
from readonly_budget_report import filtered_fields,STATUS_KEYS
from cvd_private_runtime_preview_v1 import collect_test_preview,MAX_OBSERVED_READS

MAX_BUDGET_AGE_MS=30*60*1000
MAX_HOST_AGE_MS=60*1000
MIN_MEMORY_BYTES=256*1024*1024
MAX_LOAD_PER_CPU=0.75
LIMITS={"D1_ACCOUNT_ROWS_READ_ESTIMATE":5000000,
        "D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE":100000,
        "WORKERS_ACCOUNT_REQUESTS_ESTIMATE":100000,
        "REMURA_D1_TEST_STORAGE_BYTES":500000000,
        "D1_ACCOUNT_DATABASE_COUNT":10,
        "D1_ACCOUNT_STORAGE_BYTES":5000000000,
        "D1_ACCOUNT_LARGEST_DB_BYTES":500000000}
KEYS={"d1":("D1_ACCOUNT_ROWS_READ_ESTIMATE","D1_ACCOUNT_ROWS_WRITTEN_ESTIMATE"),
      "workers":("WORKERS_ACCOUNT_REQUESTS_ESTIMATE",),
      "storage":("REMURA_D1_TEST_STORAGE_BYTES",),
      "account_storage":("D1_ACCOUNT_DATABASE_COUNT","D1_ACCOUNT_STORAGE_BYTES","D1_ACCOUNT_LARGEST_DB_BYTES")}
def fresh(stamp,now,age):
    return type(stamp) is int and 0<=now-stamp<=age

def assess(*,now,host,budget):
    if type(now) is not int or now<1000000000000:
        raise ValueError("gate_clock")
    reasons=[]
    if type(host) is not dict or set(host)!={"observed_ms","available_bytes","load1","visible_cpus"}:
        reasons.append("HOST_UNKNOWN")
    elif not fresh(host["observed_ms"],now,MAX_HOST_AGE_MS):
        reasons.append("HOST_STALE_OR_FUTURE")
    else:
        mem,cpu,load=host["available_bytes"],host["visible_cpus"],host["load1"]
        if type(mem) is not int or mem<0 or type(cpu) is not int or cpu<=0 or type(load) not in (int,float) or not isfinite(load) or load<0:
            reasons.append("HOST_METRICS_INVALID")
        else:
            if mem<MIN_MEMORY_BYTES:reasons.append("HOST_MEMORY_LOW")
            if load/cpu>MAX_LOAD_PER_CPU:reasons.append("HOST_LOAD_HIGH")
    vals={}
    if type(budget) is not dict or set(budget)!={"observed_ms","complete","reports"}:
        reasons.append("BUDGET_UNKNOWN")
    elif not fresh(budget["observed_ms"],now,MAX_BUDGET_AGE_MS) or datetime.fromtimestamp(budget["observed_ms"]//1000,tz=timezone.utc).date()!=datetime.fromtimestamp(now//1000,tz=timezone.utc).date():
        reasons.append("BUDGET_STALE_OR_FUTURE_OR_DAY_CHANGED")
    elif budget["complete"] is not True or type(budget["reports"]) is not dict or set(budget["reports"])!=set(KEYS):
        reasons.append("BUDGET_INCOMPLETE")
    else:
        day=datetime.fromtimestamp(now//1000,tz=timezone.utc).date().isoformat()
        for category,keys in KEYS.items():
            txt=budget["reports"][category]
            try:
                if type(txt) is not str or len(txt)>16000:raise ValueError("report_size")
                fields=filtered_fields(txt)
                if fields.get(STATUS_KEYS[category][0])!="OK":
                    reasons.append("BUDGET_"+category.upper()+"_NOT_OK")
                if category in ("d1","workers"):
                    prefix="UTC_DAY=" if category=="d1" else "WORKERS_UTC_DAY="
                    stamps=[l for l in txt.splitlines() if l.startswith(prefix)]
                    if stamps!=[prefix+day+"; SOURCE=ADAPTIVE_GRAPHQL_ESTIMATE; NOT_EXACT_BILLING"]:
                        raise ValueError("budget_utc_day")
                for key in keys:
                    s=fields.get(key,"")
                    if not re.fullmatch(r"[0-9]{1,14}",s):raise ValueError("missing_metric")
                    vals[key]=int(s)
            except (ValueError,TypeError):
                reasons.append("BUDGET_"+category.upper()+"_INVALID")
        for key,v in vals.items():
            reserve=MAX_OBSERVED_READS if key=="D1_ACCOUNT_ROWS_READ_ESTIMATE" else 0
            if (v+reserve)*100>=70*LIMITS[key]:reasons.append("HEADROOM_"+key)
        if all(k in vals for k in ("D1_ACCOUNT_DATABASE_COUNT","D1_ACCOUNT_STORAGE_BYTES","D1_ACCOUNT_LARGEST_DB_BYTES","REMURA_D1_TEST_STORAGE_BYTES")):
            if not (vals["D1_ACCOUNT_DATABASE_COUNT"]>=2 and vals["REMURA_D1_TEST_STORAGE_BYTES"]<=vals["D1_ACCOUNT_LARGEST_DB_BYTES"]<=vals["D1_ACCOUNT_STORAGE_BYTES"]):
                reasons.append("STORAGE_INCOHERENT")
    return {"schema":"remura.tv.runtime.preflight.preview.v1","version":"0.8.78-lab",
            "status":"ONE_SHOT_TEST_PREVIEW_PLAUSIBLE" if not reasons else "BLOCKED",
            "reasons":sorted(set(reasons)),"local_evidence_only":True,
            "host_capacity_attested":False,"cost_verified_zero":False,
            "live_authorized":False,"orders_enabled":False,"notifications_enabled":False}

def guarded_collect(core,account_id,token,*,now,host,budget,explicit=False,private=None,secret=None,retail_root=None,authorized_at=None):
    if explicit is not True:
        raise ValueError("explicit_guarded_preview_required")
    gate=assess(now=now,host=host,budget=budget)
    if gate["status"]=="BLOCKED":
        return {"preflight":gate,"preview":None,"collection_attempted":False}
    result=collect_test_preview(core,account_id,token,now=now,explicit=True,private=private,
                                secret=secret,retail_root=retail_root,authorized_at=authorized_at)
    return {"preflight":gate,"preview":result,"collection_attempted":True}
