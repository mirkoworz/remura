# REMURA Contributors v0.23 LAB — 16/11/2026 07:14 CET
"""Pure administrative planning and reconciliation; no SQL or cloud API.
Identity evidence and closure/quiescence are trusted operator attestations, not independently verified.
"""
from recovery_journal_candidate import verify,append,valid_hex,HEX32,deny
CLOSED={"write_enabled":False,"read_enabled":False,"recovery_enabled":False}
def exact_inventory(records,snapshot):
    if type(snapshot) is not list or len(snapshot)!=len(records):deny()
    seen=set()
    for row in snapshot:
        if type(row) is not dict or set(row)!={"subject","email_tag","role","slot","revoked"} or type(row["revoked"]) is not bool:deny()
        s=row["subject"]
        if not isinstance(s,str) or s in seen or s not in records or row!=records[s]:deny()
        seen.add(s)
def closure(gates,ingress_closed,quiesced):
    if type(gates) is not dict or set(gates)!=set(CLOSED) or any(gates[k] is not False for k in CLOSED):deny()
    if ingress_closed is not True or quiesced is not True:deny()
def plan_change(events,pin,snapshot,generation,new_generation,*,kind,at,subject,email_tag,role,slot,gates,ingress_closed=False,quiesced=False,identity_verified=False,owner_authorized=False):
    closure(gates,ingress_closed,quiesced)
    if owner_authorized is not True or identity_verified is not True:deny()
    if not valid_hex(generation,HEX32) or not valid_hex(new_generation,HEX32) or generation==new_generation:deny()
    old=verify(events,pin);exact_inventory(old,snapshot)
    if old and not any(r["role"]=="OWNER" and not r["revoked"] for r in old.values()):deny()
    updated,new_pin=append(events,pin,kind,at,subject,email_tag,role,slot)
    desired=verify(updated,new_pin)
    return {"old_pin":pin,"new_pin":new_pin,"old_generation":generation,"generation":new_generation,
            "event":updated[-1],"expected_inventory":sorted(desired.values(),key=lambda x:x["slot"]),
            "gates":dict(CLOSED),"may_open":False}
def reconcile(events,external_pin,snapshot,*,expected_generation,db_generation,db_pin,gates,ingress_closed=False,quiesced=False):
    closure(gates,ingress_closed,quiesced)
    if not valid_hex(expected_generation,HEX32) or db_generation!=expected_generation or db_pin!=external_pin:deny()
    desired=verify(events,external_pin);exact_inventory(desired,snapshot)
    owner_active=any(r["role"]=="OWNER" and not r["revoked"] for r in desired.values())
    return {"inventory_matches":True,"owner_active":owner_active,"may_open":False,"gates":dict(CLOSED)}
