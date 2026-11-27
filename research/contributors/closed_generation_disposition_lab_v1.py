# REMURA Contributors v0.40 LAB — 17/11/2026 07:04 CET (session start)
"""Closed synthetic disposition of contributions/reviews; no migration, deletion or opening."""
import sqlite3,json
from recovery_journal_candidate import verify,digest,valid_hex,HEX64,stamp
from closed_generation_exclusion_lab_v1 import plan,check_candidate,need
from subject_projection_rehearsal_v1 import ENTRY,MAX_ENTRIES,MAX_REVIEWS,MAX_BYTES

FIELDS=tuple(x for x in ENTRY if x!="request_id")+("source_group",)
def bounded(x):
    need(len(json.dumps(x,ensure_ascii=True,separators=(",",":"),allow_nan=False).encode("ascii"))<=MAX_BYTES)

def disposition(db,events,pin,old_generation,new_generation,*,subject,synthetic=False,ingress_closed=False):
    identity_manifest,identity_digest=plan(events,pin,old_generation,new_generation,subject=subject,synthetic=synthetic,ingress_closed=ingress_closed)
    records=verify(events,pin)
    need(isinstance(db,sqlite3.Connection) and not db.in_transaction)
    need([tuple(r) for r in db.execute("PRAGMA database_list")]==[(0,"main","")])
    need(db.execute("PRAGMA query_only").fetchone()[0]==1)
    db.execute("BEGIN")
    try:
        need([tuple(r) for r in db.execute("SELECT id,write_enabled,read_enabled,recovery_enabled FROM lab_state")]==[(1,0,0,0)])
        need([tuple(r) for r in db.execute("SELECT id,generation,journal_pin FROM lab_generation")]==[(1,old_generation,pin)])
        old=[]
        for table,role,cols in (("lab_owner","OWNER","subject,email_tag,'owner',revoked"),("lab_identities","CONTRIBUTOR","subject,email_tag,slot,revoked")):
            rows=db.execute("SELECT "+cols+" FROM "+table+" LIMIT 4").fetchall()
            for s,t,slot,revoked in rows:
                need(type(revoked) is int and revoked in (0,1))
                old.append(dict(subject=s,email_tag=t,role=role,slot=slot,revoked=bool(revoked)))
        need(len(old)==len(records) and sorted(old,key=lambda r:r["slot"])==sorted(records.values(),key=lambda r:r["slot"]))
        retained=[r for r in old if not r["revoked"]]
        check_candidate(identity_manifest,identity_digest,candidate_generation=new_generation,inventory=retained,synthetic=True,ingress_closed=True)
        entries=db.execute("SELECT id,subject,"+",".join(FIELDS)+" FROM lab_entries ORDER BY id LIMIT ?",(MAX_ENTRIES+1,)).fetchall()
        reviews=db.execute("SELECT id,entry_id,owner,action,at_utc FROM lab_reviews ORDER BY id LIMIT ?",(MAX_REVIEWS+1,)).fetchall()
        need(len(entries)<=MAX_ENTRIES and len(reviews)<=MAX_REVIEWS)
        included=[]; audited={}; kept_ids=set(); kept_reviews=[]; states={}; previous_review=""
        for eid,s,*values in entries:
            need(type(eid) is int and eid>0 and eid not in audited and s in records and records[s]["role"]=="CONTRIBUTOR")
            need(len(values)==len(FIELDS) and all(type(v) is str and len(v)<=280 for v in values))
            row=dict(zip(FIELDS,values))
            for k in ("anchor_utc","observed_utc","received_utc"):stamp(row[k])
            need(row["anchor_utc"]<=row["observed_utc"]<=row["received_utc"])
            audited[eid]=row["received_utc"]
            if not records[s]["revoked"]:
                kept_ids.add(eid);included.append(dict(entry_id=eid,slot=records[s]["slot"],**row))
        owners={r["subject"] for r in retained if r["role"]=="OWNER"}
        seen=set()
        for rid,eid,owner,action,at in reviews:
            need(type(rid) is int and rid>0 and rid not in seen and eid in audited and owner in owners)
            seen.add(rid);stamp(at)
            need(at>=audited[eid] and at>=previous_review)
            previous_review=at
            status=states.get(eid,"UNREVIEWED")
            need(action in (("APPROVED","REJECTED") if status=="UNREVIEWED" else ("REVOKED",) if status=="APPROVED" else ()))
            states[eid]=action
            if eid in kept_ids:kept_reviews.append(dict(review_id=rid,entry_id=eid,action=action,at_utc=at))
        candidate={"generation":new_generation,"entries":included,"historical_reviews":kept_reviews,"quarantine":True,"may_open":False,"scientific_admission":False}
        bounded(candidate)
        manifest={"schema":"remura.contributors.synthetic.disposition.v1","old_generation":old_generation,"new_generation":new_generation,
                  "identity_manifest_digest":identity_digest,"candidate_digest":digest(candidate),
                  "retained_entries":len(included),"excluded_entries":len(entries)-len(included),
                  "retained_reviews":len(kept_reviews),"excluded_reviews":len(reviews)-len(kept_reviews),
                  "free_text_omitted":True,"request_ids_omitted":True,"migration_authorized":False}
        return manifest,digest(manifest),candidate
    finally:db.rollback()

def check_disposition(manifest,pin,candidate,*,expected_generation,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and valid_hex(pin,HEX64))
    need(type(manifest) is dict and manifest.get("schema")=="remura.contributors.synthetic.disposition.v1" and digest(manifest)==pin)
    need(manifest.get("new_generation")==expected_generation and manifest.get("old_generation")!=expected_generation)
    need(manifest.get("migration_authorized") is False and type(candidate) is dict)
    bounded(candidate)
    need(candidate.get("generation")==expected_generation and digest(candidate)==manifest.get("candidate_digest"))
    need(candidate.get("quarantine") is True and candidate.get("may_open") is False and candidate.get("scientific_admission") is False)
    return {"status":"SYNTHETIC_DISPOSITION_MATCH","migration_authorized":False,"may_open":False,"all_copies_erased":False,
            "independent_pin_verified":False,"retained_entries":manifest["retained_entries"],"excluded_entries":manifest["excluded_entries"],
            "retained_reviews":manifest["retained_reviews"],"excluded_reviews":manifest["excluded_reviews"]}
