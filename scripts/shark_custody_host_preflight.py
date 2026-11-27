"""REMURA Shark Science — owner custody preflight v0.3 LAB,
18/11/2026, session after 16:28 CET.
Read-only host metadata; no archive, private files, identifiers, network or writes.
No preflight result authorizes plaintext handling or the backup swap gate.
"""
import json
import os
import re
import resource
import sqlite3
import subprocess
import sys

def mac_swap(raw):
    m=re.fullmatch(r"\s*total\s*=\s*([0-9]+(?:\.[0-9]+)?)[KMG]\s+used\s*=\s*([0-9]+(?:\.[0-9]+)?)[KMG]\s+free\s*=\s*[0-9]+(?:\.[0-9]+)?[KMG]\s*(\(encrypted\))?\s*",raw)
    if not m:return {"swap_allocated_reported":None,"swap_used_reported":None,"swap_encryption_reported":None}
    return {"swap_allocated_reported":float(m[1])>0,
            "swap_used_reported":float(m[2])>0,
            "swap_encryption_reported":True if m[3] else None}

def filevault(raw):
    return True if raw.strip()=="true" else False if raw.strip()=="false" else None

def read_command(*args):
    try:
        r=subprocess.run(args,capture_output=True,text=True,timeout=5,check=True)
        return r.stdout if len(r.stdout)<4096 else ""
    except (OSError,subprocess.SubprocessError,UnicodeError):return ""

def linux_swap(meminfo,swaps):
    values=re.findall(r"^SwapTotal:\s*(\d+)\s+kB\s*$",meminfo,re.M)
    lines=[x.split() for x in swaps.splitlines() if x.strip()]
    if len(values)!=1 or not lines or lines[0]!=["Filename","Type","Size","Used","Priority"]:
        return None
    if int(values[0])==0 and len(lines)==1:return False
    if int(values[0])>0 and len(lines)>1:return True
    return None

def preflight():
    r={"schema":"remura.shark.owner.custody.preflight.v1",
       "version":"0.3-lab","platform":"macOS" if sys.platform=="darwin" else
       "Linux" if sys.platform.startswith("linux") else "OTHER",
       "ordinary_user":os.geteuid()!=0,
       "sqlite_deserialize_available":hasattr(sqlite3.Connection,"deserialize"),
       "core_dump_zero_limit":resource.getrlimit(resource.RLIMIT_CORE)[0]==0,
       "filevault_reported":None,
       "swap_allocated_reported":None,"swap_used_reported":None,
       "swap_encryption_reported":None,"linux_swap_active_observed":None,
       "archive_opened":False,"archive_volume_encryption_attested":False,
       "memory_non_swappable_attested":False,"plaintext_processing_authorized":False,
       "backup_gate_bypassed":False}
    if sys.platform=="darwin":
        r.update(mac_swap(read_command("/usr/sbin/sysctl","-n","vm.swapusage")))
        r["filevault_reported"]=filevault(read_command("/usr/bin/fdesetup","isactive"))
    elif sys.platform.startswith("linux"):
        try:
            with open("/proc/meminfo") as m,open("/proc/swaps") as s:
                r["linux_swap_active_observed"]=linux_swap(m.read(65536),s.read(65536))
        except OSError:pass
    return r

if __name__=="__main__":
    print(json.dumps(preflight(),sort_keys=True))
