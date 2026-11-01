"""Sanitized local-only resource metrics; never claims OCI billing data."""
from __future__ import annotations
import datetime as dt
import os
import shutil
from pathlib import Path

def read(path):
    try: return Path(path).read_text(encoding="ascii")
    except (OSError,UnicodeError): return ""

def memory():
    info={}
    for line in read("/proc/meminfo").splitlines():
        name,sep,value=line.partition(":")
        if sep:
            parts=value.split()
            if parts and parts[0].isdigit(): info[name]=int(parts[0])*1024
    total=info.get("MemTotal",0)
    avail=info.get("MemAvailable",0)
    return {"total":total or None,"used":max(0,total-min(total,avail)) if total else None,
            "swapTotal":info.get("SwapTotal",0),"swapUsed":max(0,info.get("SwapTotal",0)-info.get("SwapFree",0))}

def network():
    default=None
    for line in read("/proc/net/route").splitlines()[1:]:
        row=line.split()
        if len(row)>2 and row[1]=="00000000" and row[0]!="lo":
            default=row[0];break
    if default:
        for line in read("/proc/net/dev").splitlines()[2:]:
            name,sep,raw=line.partition(":")
            if sep and name.strip()==default:
                vals=raw.split()
                if len(vals)>=9 and vals[0].isdigit() and vals[8].isdigit():
                    return {"rxSinceInterfaceStart":int(vals[0]),"txSinceInterfaceStart":int(vals[8])}
    return {"rxSinceInterfaceStart":None,"txSinceInterfaceStart":None}

def snapshot(requests=None):
    try:
        du=shutil.disk_usage("/")
        disk={"total":du.total,"used":du.used}
    except OSError:
        disk={"total":None,"used":None}
    try: load=round(os.getloadavg()[0],3)
    except (AttributeError,OSError): load=None
    try: uptime=int(float(read("/proc/uptime").split()[0]))
    except (IndexError,ValueError,OverflowError): uptime=None
    counts=requests if isinstance(requests,dict) else {}
    return {"schema":"remura-resources-v1",
            "sampledAt":dt.datetime.now(dt.timezone.utc).isoformat(),
            "memory":memory(),"cpu":{"logical":os.cpu_count(),"load1":load},
            "disk":disk,"network":network(),"uptimeSeconds":uptime,
            "webApi":{"allGet":int(counts.get("allGet",0)),"privateGet":int(counts.get("privateGet",0))},
            "oracle":{"bill":"unverified","limits":"unverified","networkMonthly":None,"externalApiCalls":None}}
