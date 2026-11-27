"""REMURA v0.8.179 LAB — 18/11/2026, sessione successiva alle 18:50 CET.
Bind a supplied, owner-signed external phase receipt to authenticated local
journal state in a disposable fixture. No service, install, repair or writes
to application/journal/register. Caller holds cooperative LAB locks.
No independent latest-anchor or privileged executable attestation.
"""
import hashlib
from abc_rollback_disk_lab_v1 import canonical,require
from abc_v165_phase_state_lab_v1 import inspect
from abc_v165_external_phase_receipt_lab_v1 import verify

def plan_digest(doc):
    # Immutable rows include actual before/after bytes and modes; phase excluded.
    return hashlib.sha256(b"REMURA-LAB-PLAN-V1\x00"+canonical(doc["rows"])).hexdigest()

def check(journal,body,signature,*,keyring,signer,latest_anchor,sequence,
          expected_plan,challenge,synthetic=False):
    require(synthetic is True)
    initial=inspect(journal,synthetic=True)
    require(initial["status"] in ("LOCAL_PHASE_MATCH","INTERRUPTED_PHASE_REVIEW_REQUIRED"))
    doc=journal.read_doc()
    digest=hashlib.sha256(canonical(doc)).hexdigest()
    require(plan_digest(doc)==expected_plan)
    # Ensure the phase being matched belongs to the authenticated document.
    journal.witness_check(doc,{initial["phase"]})
    verify(body,signature,keyring=keyring,signer=signer,
           latest_anchor=latest_anchor,transaction=journal.transaction_id,
           plan=expected_plan,sequence=sequence,phase=initial["phase"],
           journal=digest,challenge=challenge,synthetic=True)
    require(journal.read_doc()==doc)
    journal.witness_check(doc,{initial["phase"]})
    require(inspect(journal,synthetic=True)==initial)
    return {"status":"LOCAL_PHASE_AND_SUPPLIED_SIGNED_RECEIPT_MATCH",
            "phase":initial["phase"],"local_status":initial["status"],
            "counts":initial["counts"],"independent_latest_anchor_attested":False,
            "mutation_authorized":False,"install_authorized":False,
            "restore_authorized":False}
