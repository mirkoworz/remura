# REMURA Contributors v0.33 LAB — 16/11/2026 13:21 CET
"""Synthetic-only subject-scoped projection, NOT a privacy-rights export service.
No authentication, file/device/HTTP access, real accounts, or retention/deletion.
Requires disposable in-memory SQLite and closed, query-only snapshot.
"""
import json,re,sqlite3
MAX_ENTRIES=200
MAX_REVIEWS=400
MAX_BYTES=256*1024
HEX64=re.compile(r"[0-9a-f]{64}")
HEX32=re.compile(r"[0-9a-f]{32}")
ENTRY=("request_id","market","provider","ticker","product","contract","period","kind","price","anchor_utc","observed_utc","received_utc")
REVIEW=("request_id","action","at_utc")
def need(ok):
    if not ok:raise ValueError("synthetic_projection_denied")
def matches(s,pattern):return type(s) is str and pattern.fullmatch(s) is not None

def project(db,*,subject,generation,pin,synthetic=False):
    need(synthetic is True and isinstance(db,sqlite3.Connection) and not db.in_transaction)
    need(matches(subject,HEX64) and matches(generation,HEX32) and matches(pin,HEX64))
    # This rehearsal allows only a memory database. It is not a production
    # authorization boundary: a caller could copy real records into memory.
    need([tuple(r) for r in db.execute("PRAGMA database_list")]==[(0,"main","")])
    need(db.execute("PRAGMA query_only").fetchone()[0]==1)
    db.execute("BEGIN")
    try:
        need([tuple(r) for r in db.execute("SELECT id,write_enabled,read_enabled,recovery_enabled FROM lab_state")]==[(1,0,0,0)])
        need([tuple(r) for r in db.execute("SELECT id,generation,journal_pin FROM lab_generation")]==[(1,generation,pin)])
        identity=db.execute("SELECT revoked FROM lab_identities WHERE subject=?",(subject,)).fetchall()
        need(len(identity)==1 and identity[0][0] in (0,1))
        entries=db.execute("SELECT "+",".join(ENTRY)+" FROM lab_entries WHERE subject=? ORDER BY id LIMIT ?",(subject,MAX_ENTRIES+1)).fetchall()
        reviews=db.execute("SELECT e.request_id,r.action,r.at_utc FROM lab_reviews r JOIN lab_entries e ON e.id=r.entry_id WHERE e.subject=? ORDER BY r.id LIMIT ?",(subject,MAX_REVIEWS+1)).fetchall()
        need(len(entries)<=MAX_ENTRIES and len(reviews)<=MAX_REVIEWS)
        e=[dict(zip(ENTRY,r)) for r in entries]
        v=[dict(zip(REVIEW,r)) for r in reviews]
        receipt_ids={x["request_id"] for x in e}
        need(len(receipt_ids)==len(e) and all(x["request_id"] in receipt_ids for x in v))
        need(all(type(x) is str and len(x)<=280 for r in e+v for x in r.values()))
        out={"schema":"remura.contributors.synthetic.subject_projection.v1","origin":"SYNTHETIC",
             "revoked":bool(identity[0][0]),"entries":e,"reviews":v,
             "free_text_omitted":True,"identity_tags_omitted":True,
             "complete_privacy_export":False,"independent_pin_verified":False,
             "delivery_enabled":False,"deletion_performed":False,"enrollment_authorized":False}
        need(len(json.dumps(out,ensure_ascii=True,allow_nan=False,separators=(",",":")).encode("ascii"))<=MAX_BYTES)
        return out
    finally:db.rollback()
