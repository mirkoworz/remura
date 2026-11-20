# REMURA v0.8.163 LAB — 18/11/2026, sessione successiva alle 13:37 CET
"""Pure manifest-to-journal plan, no filesystem or privileged actions.
Inputs are previously captured immutable application bytes, not private data.
The caller must establish live target quiescence and same-lock custody separately.
"""
import datetime,hashlib,re
from abc_v165_stage_bundle_v1 import rows,need,sha

STAMP=b"05/11/2026 18:03 (Italia, preparazione)"
LIVE_STAMP=re.compile(rb"\d{2}/\d{2}/20\d{2} \d{2}:\d{2} \(Italia\)")
MAX=4*1024*1024

def blob(b):
    return hashlib.sha1(b"blob "+str(len(b)).encode()+b"\0"+b).hexdigest()

def matches_base(name,data,expected):
    if blob(data)==expected:return True
    if name!="nav.js":return False
    matches=LIVE_STAMP.findall(data)
    if len(matches)!=1:return False
    try:datetime.datetime.strptime(matches[0].decode("ascii"),"%d/%m/%Y %H:%M (Italia)")
    except ValueError:return False
    return blob(data.replace(matches[0],STAMP,1))==expected

def prepare_plan(manifest,application,baseline):
    """Return only 14 original and 90 new mutation bytes, with 65 retained checked.
    The baseline dictionary must be an exact census of existing manifest paths.
    No missing file is inferred from an incomplete scan.
    """
    expected=rows(manifest)
    need(type(application) is dict and type(baseline) is dict)
    need(set(application)==set(expected))
    need(set(baseline)=={p for p,r in expected.items() if r["operation"]!="add"})
    need(len(baseline)==79)
    need(all(type(b) is bytes and 0<len(b)<=2*1024*1024 for d in (application,baseline) for b in d.values()))
    need(sum(len(b) for d in (application,baseline) for b in d.values())<=MAX)
    old={};new={};retained=0
    for p,r in expected.items():
        data=application[p]
        need(len(data)==r["bytes"] and sha(data)==r["candidate_sha256"])
        op=r["operation"]
        if op=="add":
            need(r["base_git_blob"] is None)
            new[p]=data
        else:
            current=baseline[p]
            need(matches_base(p,current,r["base_git_blob"]))
            if op=="replace":
                need(current!=data)
                old[p]=current
                new[p]=data
            else:
                need(op=="retain" and current==data)
                retained+=1
    need(len(old)==14 and len(new)==90 and retained==65)
    return old,new
