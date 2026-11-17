# REMURA Contributors v0.39 LAB — 17/11/2026 06:44 CET
"""Pure synthetic closed-generation exclusion contract. NOT deletion or recovery.
The supplied journal pin and manifest digest are fixture authority, not independent custody.
No SQL, identities enrolled, D1, public export or real privacy request handling.
"""
from recovery_journal_candidate import verify,digest,valid_hex,HEX32,HEX64

def need(ok):
    if not ok:raise ValueError("generation_exclusion_denied")

def plan(events,pin,old_generation,new_generation,*,subject,ingress_closed=False,synthetic=False):
    need(synthetic is True and ingress_closed is True)
    need(valid_hex(old_generation,HEX32) and valid_hex(new_generation,HEX32) and old_generation!=new_generation)
    need(valid_hex(subject,HEX64))
    records=verify(events,pin)
    target=records.get(subject)
    need(target is not None and target["role"]=="CONTRIBUTOR" and target["revoked"] is True)
    need(any(r["role"]=="OWNER" and not r["revoked"] for r in records.values()))
    # Minimal slot retirement rehearsal. It does not prove a human cannot present a different account.
    retired=sorted(r["slot"] for r in records.values() if r["role"]=="CONTRIBUTOR" and r["revoked"])
    retained=sorted((dict(r) for r in records.values() if r["slot"] not in retired),key=lambda r:r["slot"])
    body={"schema":"remura.contributors.synthetic.closed_generation.v1","old_generation":old_generation,
          "new_generation":new_generation,"retired_slots":retired,"retained_inventory_digest":digest(retained),
          "new_enrollment_allowed":False,"write_enabled":False,"read_enabled":False,"recovery_enabled":False}
    return body,digest(body)

def check_candidate(manifest,expected_digest,*,candidate_generation,inventory,ingress_closed=False,synthetic=False):
    need(synthetic is True and ingress_closed is True and valid_hex(expected_digest,HEX64))
    need(type(manifest) is dict and set(manifest)=={"schema","old_generation","new_generation","retired_slots",
         "retained_inventory_digest","new_enrollment_allowed","write_enabled","read_enabled","recovery_enabled"})
    need(digest(manifest)==expected_digest and manifest["schema"]=="remura.contributors.synthetic.closed_generation.v1")
    old,new=manifest["old_generation"],manifest["new_generation"]
    need(valid_hex(old,HEX32) and valid_hex(new,HEX32) and old!=new and candidate_generation==new)
    need(all(manifest[k] is False for k in ("new_enrollment_allowed","write_enabled","read_enabled","recovery_enabled")))
    retired=manifest["retired_slots"]
    need(type(retired) is list and 1<=len(retired)<=2 and all(x in ("friend-a","friend-b") for x in retired) and retired==sorted(set(retired)))
    need(valid_hex(manifest["retained_inventory_digest"],HEX64))
    need(type(inventory) is list and 1<=len(inventory)<=3)
    slots=set();subjects=set();tags=set()
    for r in inventory:
        need(type(r) is dict and set(r)=={"subject","email_tag","role","slot","revoked"})
        need(valid_hex(r["subject"],HEX64) and valid_hex(r["email_tag"],HEX64) and r["revoked"] is False)
        need((r["role"]=="OWNER" and r["slot"]=="owner") or (r["role"]=="CONTRIBUTOR" and r["slot"] in ("friend-a","friend-b")))
        need(r["slot"] not in retired and r["slot"] not in slots and r["subject"] not in subjects and r["email_tag"] not in tags)
        slots.add(r["slot"]);subjects.add(r["subject"]);tags.add(r["email_tag"])
    need("owner" in slots and digest(sorted(inventory,key=lambda r:r["slot"]))==manifest["retained_inventory_digest"])
    return {"status":"SYNTHETIC_IDENTITY_EXCLUSION_ONLY","retired_count":len(retired),"retained_count":len(inventory),
            "independent_pin_verified":False,"all_copies_erased":False,"entry_migration_verified":False,
            "restore_authorized":False,"enrollment_authorized":False,"may_open":False}
