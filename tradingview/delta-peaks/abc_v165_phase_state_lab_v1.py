"""REMURA v0.8.174 LAB — 18/11/2026, sessione successiva alle 17:48 CET.
Read-only classification of a disposable authenticated journal and file state.
No mutation, repair, retry, service action or authorization.
A jointly replayed local witness/journal remains possible; external custody required.
"""
from collections import Counter
import hashlib
import hmac
import json
from abc_rollback_disk_lab_v1 import Journal,canonical,owned,require

def inspect(journal,*,synthetic=False):
    require(synthetic is True and type(journal) is Journal
            and journal.auth_key is not None and journal.witness is not None)
    # Caller must already hold the outer maintenance and journal lock.
    # Do not create a lock, witness or missing journal.
    d=journal.read_doc()
    s=owned(journal.witness)
    require(not s.st_mode&0o077 and 0<s.st_size<=2048)
    env=json.loads(journal.witness.read_bytes())
    require(type(env) is dict and set(env)=={"payload","mac"})
    body=env["payload"]
    require(type(body) is dict and type(body.get("phase")) is str)
    phase=body["phase"]
    allowed={"prepared":{"prepared","applying","rolling_back"},
             "applied":{"applied","rolling_back"},
             "rolled_back":{"rolled_back"}}
    require(phase in allowed[d["phase"]])
    require(body==journal.witness_payload(d,phase))
    require(type(env["mac"]) is str and hmac.compare_digest(env["mac"],
            hmac.new(journal.auth_key,canonical(body),hashlib.sha256).hexdigest()))
    counts=Counter()
    for row in d["rows"]:
        current=journal.current(row["path"])
        counts["before" if current==row["before"] else
               "after" if current==row["after"] else "unknown"]+=1
    n=len(d["rows"])
    if counts["unknown"]:
        status="STOP_UNKNOWN_FILE_STATE"
    elif phase in ("prepared","rolled_back") and counts["before"]!=n:
        status="STOP_PHASE_FILE_MISMATCH"
    elif phase=="applied" and counts["after"]!=n:
        status="STOP_PHASE_FILE_MISMATCH"
    elif phase in ("applying","rolling_back"):
        status="INTERRUPTED_PHASE_REVIEW_REQUIRED"
    else:
        status="LOCAL_PHASE_MATCH"
    return {"schema":"remura.abc.phase.state.lab.v1","phase":phase,"status":status,
            "counts":{k:counts[k] for k in ("before","after","unknown")},
            "independent_latest_anchor_attested":False,"writes":False,
            "install_authorized":False,"restore_authorized":False}
