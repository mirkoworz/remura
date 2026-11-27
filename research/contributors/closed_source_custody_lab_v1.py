# REMURA Contributors v0.41 LAB — 17/11/2026 09:32 CET
"""Exact closed-source snapshot pin before disposition. Synthetic only."""
import sqlite3,json,hmac
from pathlib import Path
from recovery_journal_candidate import digest,verify,valid_hex,HEX32,HEX64
from closed_generation_disposition_lab_v1 import disposition,check_disposition
from closed_generation_exclusion_lab_v1 import need
from subject_projection_rehearsal_v1 import MAX_ENTRIES,MAX_REVIEWS
DDL=Path(__file__).with_name("d1_access_candidate.sql")
TABLES=(("lab_state","id",1),("lab_generation","id",1),("lab_owner","id",1),
        ("lab_identities","subject",2),("lab_catalog","market,provider,ticker,product,contract",256),
        ("lab_entries","id",MAX_ENTRIES),("lab_reviews","id",MAX_REVIEWS),
        ("lab_identity_revocations","subject",2),("lab_intent_used","nonce",1300),("lab_admin_events","seq",6))
MAX=2*1024*1024
def scope(db):
    need(isinstance(db,sqlite3.Connection) and not db.in_transaction)
    need(db.execute("PRAGMA query_only").fetchone()[0]==1)
    need([tuple(r) for r in db.execute("PRAGMA database_list")] in ([(0,"main","")],[(0,"main",""),(1,"temp","")]))
    need(db.execute("SELECT 1 FROM temp.sqlite_master LIMIT 1").fetchone() is None)
def catalog(db):
    return [tuple(r) for r in db.execute("SELECT type,name,tbl_name,sql FROM main.sqlite_master ORDER BY type,name LIMIT 100")]
def expected_schema():
    db=sqlite3.connect(":memory:")
    try:
        db.executescript(DDL.read_text())
        return catalog(db)
    finally:db.close()
def source_pin(db,events,journal_pin,generation,*,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and valid_hex(generation,HEX32))
    records=verify(events,journal_pin)
    scope(db)
    db.execute("BEGIN")
    try:
        schema=catalog(db);need(schema==expected_schema())
        need(db.execute("PRAGMA main.quick_check").fetchall()==[("ok",)])
        need(db.execute("PRAGMA main.foreign_key_check").fetchone() is None)
        inventory={}
        for table,order,limit in TABLES:
            rows=[tuple(r) for r in db.execute("SELECT * FROM main."+table+" ORDER BY "+order+" LIMIT ?",(limit+1,))]
            need(len(rows)<=limit)
            need(all(type(v) in (int,str) and (type(v) is int or len(v)<=280) for row in rows for v in row))
            inventory[table]=rows
        need(inventory["lab_state"]==[(1,0,0,0)] and inventory["lab_generation"]==[(1,generation,journal_pin)])
        actual=[dict(subject=s,email_tag=e,role="OWNER",slot="owner",revoked=bool(r)) for _,s,e,r in inventory["lab_owner"]]
        actual += [dict(subject=s,email_tag=e,role="CONTRIBUTOR",slot=slot,revoked=bool(r)) for s,e,slot,r in inventory["lab_identities"]]
        need(sorted(actual,key=lambda r:r["slot"])==sorted(records.values(),key=lambda r:r["slot"]))
        revocations={s:at for s,_,at in inventory["lab_identity_revocations"]}
        need(revocations=={e["subject"]:e["at"] for e in events if e["kind"]=="REVOKE" and e["role"]=="CONTRIBUTOR"})
        body={"schema":"remura.contributors.synthetic.closed_source.v1","generation":generation,"journal_pin":journal_pin,
              "catalog":schema,"tables":inventory}
        need(len(json.dumps(body,ensure_ascii=True,separators=(",",":")).encode("ascii"))<=MAX)
        return digest(body)
    finally:db.rollback()
def bound_disposition(db,events,journal_pin,old_generation,new_generation,*,subject,expected_source_pin,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and valid_hex(expected_source_pin,HEX64))
    scope(db)
    # One coherent backup, private to this call. Both checks use the same bytes.
    clone=sqlite3.connect(":memory:")
    try:
        db.backup(clone)
        clone.execute("PRAGMA query_only=ON")
        measured=source_pin(clone,events,journal_pin,old_generation,synthetic=True,ingress_closed=True)
        need(hmac.compare_digest(measured,expected_source_pin))
        # v0.40 disposition requires a fresh connection with main-only scope.
        fresh=sqlite3.connect(":memory:")
        try:
            clone.backup(fresh);fresh.execute("PRAGMA query_only=ON")
            m,p,c=disposition(fresh,events,journal_pin,old_generation,new_generation,subject=subject,synthetic=True,ingress_closed=True)
        finally:fresh.close()
        binding={"schema":"remura.contributors.synthetic.bound_disposition.v1","source_pin":measured,
                 "journal_pin":journal_pin,"old_generation":old_generation,"new_generation":new_generation,"disposition_pin":p}
        return binding,digest(binding),m,c
    finally:clone.close()
def verify_bound(binding,expected_binding_pin,manifest,candidate,*,expected_source_pin,latest_journal_pin,old_generation,new_generation,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True)
    need(all(valid_hex(x,HEX64) for x in (expected_binding_pin,expected_source_pin,latest_journal_pin)))
    need(type(binding) is dict and set(binding)=={"schema","source_pin","journal_pin","old_generation","new_generation","disposition_pin"})
    need(binding["schema"]=="remura.contributors.synthetic.bound_disposition.v1" and digest(binding)==expected_binding_pin)
    need(binding["source_pin"]==expected_source_pin and binding["journal_pin"]==latest_journal_pin)
    need(binding["old_generation"]==old_generation and binding["new_generation"]==new_generation and manifest.get("old_generation")==old_generation)
    out=check_disposition(manifest,binding["disposition_pin"],candidate,expected_generation=new_generation,synthetic=True,ingress_closed=True)
    return {**out,"status":"SYNTHETIC_SOURCE_AND_DISPOSITION_MATCH","fixture_source_pin_matched":True,
            "independent_pin_verified":False,"restore_authorized":False,"may_open":False,"scientific_admission":False}
