#!/usr/bin/env python3
# REMURA v0.8.81 LAB — 14/11/2026 19:58 CET
"""Fail-closed Linux local host sample, with visible cgroup v2 constraints.
No subprocess, credentials, network, or host identity output.
Not a proof of available capacity throughout a run.
"""
from pathlib import Path,PurePosixPath
import os,time

def _text(path):
    with open(path,"r",encoding="ascii") as f:
        value=f.read(65537)
    if len(value)>65536:
        raise ValueError("host_metric_size")
    return value.strip()

def bounds(mem,cpus,levels):
    if type(mem) is not int or mem<0 or type(cpus) is not int or cpus<1 or not levels:
        raise ValueError("host_metric_shape")
    for memmax,current,cpu in levels:
        if memmax!="max":
            limit=int(memmax); used=int(current)
            if limit<0 or used<0:raise ValueError("host_memory_limit")
            mem=min(mem,max(0,limit-used))
        quota,period=cpu.split()
        period=int(period)
        if period<=0:raise ValueError("host_cpu_period")
        if quota!="max":
            n=int(quota)
            if n<=0:raise ValueError("host_cpu_quota")
            cpus=min(cpus,n//period)
    if cpus<1:raise ValueError("host_fractional_cpu_unavailable")
    return mem,cpus

def _levels():
    # Only unified cgroup v2 mounted at the conventional root is supported.
    # A non-root mount may hide ancestors; refuse rather than claim headroom.
    mounts=[x.split() for x in _text("/proc/self/mountinfo").splitlines()]
    matches=[x for x in mounts if len(x)>6 and x[4]=="/sys/fs/cgroup" and x[x.index("-")+1]=="cgroup2"]
    if len(matches)!=1 or matches[0][3]!="/":
        raise ValueError("host_cgroup_mount_unknown")
    entries=_text("/proc/self/cgroup").splitlines()
    if len(entries)!=1 or not entries[0].startswith("0::/"):
        raise ValueError("host_cgroup_v2_required")
    rel=PurePosixPath(entries[0][3:])
    if ".." in rel.parts:raise ValueError("host_cgroup_path")
    root=Path("/sys/fs/cgroup")
    leaf=root.joinpath(*rel.parts[1:])
    levels=[]
    for p in (leaf,*leaf.parents):
        if p==root:
            # Global root has no controller limit files on a bare-metal host.
            # Missing files lower in the hierarchy are not silently ignored.
            if not p.is_dir():raise ValueError("host_cgroup_root")
            if not (p/"memory.max").exists() and not (p/"cpu.max").exists():
                levels.append(("max","0","max 100000"))
            else:
                levels.append((_text(p/"memory.max"),_text(p/"memory.current"),_text(p/"cpu.max")))
            break
        levels.append((_text(p/"memory.max"),_text(p/"memory.current"),_text(p/"cpu.max")))
    return levels

def sample_host():
    try:
        start=time.time_ns()//1000000
        lines=[s.split() for s in _text("/proc/meminfo").splitlines() if s.startswith("MemAvailable:")]
        if len(lines)!=1 or len(lines[0])!=3 or lines[0][2]!="kB":
            raise ValueError("host_meminfo")
        mem=int(lines[0][1])*1024
        mem,cpus=bounds(mem,len(os.sched_getaffinity(0)),_levels())
        load=os.getloadavg()[0]
        if not 0<=time.time_ns()//1000000-start<=10000:
            raise ValueError("host_sample_slow")
        return {"observed_ms":start,"available_bytes":mem,"visible_cpus":cpus,"load1":load}
    except (OSError,ValueError,IndexError,AttributeError):
        raise ValueError("host_evidence_unavailable") from None
