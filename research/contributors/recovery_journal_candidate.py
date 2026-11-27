# REMURA Contributors v0.22 LAB — 16/11/2026 07:08 CET
"""Pure offline recovery journal candidate. No network, file writes, SQL updates or real enrollment.
Pin must come from independently trusted latest checkpoint; hash chain alone cannot prove recency.
"""
import hashlib, json, re
from datetime import datetime
HEX64=re.compile(r"[a-f0-9]{64}\Z"); HEX32=re.compile(r"[a-f0-9]{32}\Z")
ZERO="0"*64
def deny():raise ValueError("journal_or_restore_denied")
def digest(obj):return hashlib.sha256(json.dumps(obj,sort_keys=True,separators=(",",":"),ensure_ascii=True).encode()).hexdigest()
def valid_hex(x,pattern):return isinstance(x,str) and pattern.fullmatch(x) is not None
def stamp(x):
    if not isinstance(x,str):deny()
    try:
        if datetime.strptime(x,"%Y-%m-%dT%H:%M:%SZ").strftime("%Y-%m-%dT%H:%M:%SZ")!=x:deny()
    except ValueError:deny()
def verify(events,pin):
    if type(events) is not list or len(events)>6 or not valid_hex(pin,HEX64):deny()
    prior=ZERO; at=""; records={}; emails=set(); slots=set()
    for n,e in enumerate(events,1):
        if type(e) is not dict or set(e)!={"seq","prev","kind","at","subject","email_tag","role","slot"}:deny()
        if type(e["seq"]) is not int or e["seq"]!=n or e["prev"]!=prior:deny()
        stamp(e["at"])
        if e["at"]<at:deny()
        s,tag,role,slot=e["subject"],e["email_tag"],e["role"],e["slot"]
        if not valid_hex(s,HEX64) or not valid_hex(tag,HEX64):deny()
        if not ((role=="OWNER" and slot=="owner") or (role=="CONTRIBUTOR" and slot in ("friend-a","friend-b"))):deny()
        if e["kind"]=="ENROLL":
            if s in records or tag in emails or slot in slots:deny()
            if role=="CONTRIBUTOR" and not any(r["role"]=="OWNER" and not r["revoked"] for r in records.values()):deny()
            records[s]={"subject":s,"email_tag":tag,"role":role,"slot":slot,"revoked":False}
            emails.add(tag);slots.add(slot)
        elif e["kind"]=="REVOKE":
            r=records.get(s)
            if not r or r["revoked"] or (r["email_tag"],r["role"],r["slot"])!=(tag,role,slot):deny()
            r["revoked"]=True
        else:deny()
        prior=digest(e);at=e["at"]
    if prior!=pin:deny()
    return records
def append(events,pin,kind,at,subject,email_tag,role,slot):
    verify(events,pin)
    event={"seq":len(events)+1,"prev":pin,"kind":kind,"at":at,"subject":subject,"email_tag":email_tag,"role":role,"slot":slot}
    result=[dict(e) for e in events]+[event];new_pin=digest(event)
    verify(result,new_pin)
    return result,new_pin
def restore_plan(events,pin,snapshot,old_generation,new_generation,*,ingress_closed=False):
    """Pure comparison. Never re-enroll missing identities, un-revoke or authorize opening."""
    records=verify(events,pin)
    if ingress_closed is not True or not valid_hex(old_generation,HEX32) or not valid_hex(new_generation,HEX32) or old_generation==new_generation:deny()
    if not any(r["role"]=="OWNER" and not r["revoked"] for r in records.values()):deny()
    if type(snapshot) is not list or len(snapshot)>3:deny()
    seen=set(); revoke=[]
    for row in snapshot:
        if type(row) is not dict or set(row)!={"subject","email_tag","role","slot","revoked"} or type(row["revoked"]) is not bool:deny()
        s=row["subject"]
        if not valid_hex(s,HEX64) or s in seen or s not in records:deny()
        expected=records[s];seen.add(s)
        if any(row[k]!=expected[k] for k in ("subject","email_tag","role","slot")):deny()
        if row["revoked"] and not expected["revoked"]:deny() # journal stale: never reactivate
        if expected["revoked"] and not row["revoked"]:revoke.append(s)
    if seen!=set(records):deny() # absent tombstone/identity requires separate reconciliation
    return {"generation":new_generation,"journal_pin":pin,"revoke_subjects":sorted(revoke),
            "write_enabled":False,"read_enabled":False,"recovery_enabled":False,"may_open":False}
