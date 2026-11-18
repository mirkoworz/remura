"""REMURA v0.8.169 LAB — 18/11/2026, sessione successiva alle 16:28 CET.
External owner-signed phase receipt contract; offline, nonprivileged LAB.
No signing key generation, ledger writes, mutation, installation or recovery permission.
The latest anchor must be obtained independently of the server; signatures alone
do not prove freshness, independent storage or a durable external compare-and-set.
"""
import hashlib
import re
from abc_prices_recovery_v2 import canon, gpg, private_dir, verify_signature
from abc_v165_stage_bundle_v1 import PIN
import subprocess

ZERO="0"*64
SCHEMA="remura.v165.external.phase.receipt.lab.v1"
PHASES={"prepared":{"applying","rolling_back"},
        "applying":{"applied","rolling_back"},
        "applied":{"rolling_back"},
        "rolling_back":{"rolled_back"},
        "rolled_back":set()}

def need(ok):
    if not ok:raise ValueError("EXTERNAL_PHASE_GATE")

def hex64(x):
    return type(x) is str and re.fullmatch(r"[0-9a-f]{64}",x) is not None

def validate(body):
    need(type(body) is dict and set(body)=={"schema","manifest","transaction","plan",
         "sequence","previous","phase","journal","challenge","install_authorized"})
    need(body["schema"]==SCHEMA and body["manifest"]==PIN and body["install_authorized"] is False)
    need(all(hex64(body[k]) and body[k]!=ZERO for k in ("transaction","plan","journal","challenge")))
    need(hex64(body["previous"]) and type(body["sequence"]) is int and 1<=body["sequence"]<=5)
    need(type(body["phase"]) is str and body["phase"] in PHASES)
    need((body["sequence"]==1)==(body["previous"]==ZERO))
    if body["sequence"]==1:need(body["phase"]=="prepared")
    return body

def anchor(body,signature):
    validate(body)
    need(type(signature) is bytes and 0<len(signature)<=16384)
    return hashlib.sha256(b"REMURA-EXTERNAL-PHASE-LAB-V1\\0"+canon(body)+
                          len(signature).to_bytes(4,"big")+signature).hexdigest()

def statement(*,transaction,plan,sequence,previous,phase,journal,challenge):
    return validate(dict(schema=SCHEMA,manifest=PIN,transaction=transaction,plan=plan,
                         sequence=sequence,previous=previous,phase=phase,journal=journal,
                         challenge=challenge,install_authorized=False))

def verify(body,signature,*,keyring,signer,latest_anchor,transaction,plan,
           sequence,phase,journal,challenge,synthetic=False):
    need(synthetic is True)
    expected=statement(transaction=transaction,plan=plan,sequence=sequence,
                       previous=validate(body)["previous"],phase=phase,journal=journal,challenge=challenge)
    need(body==expected and hex64(latest_anchor) and latest_anchor!=ZERO)
    need(anchor(body,signature)==latest_anchor)
    private_dir(keyring)
    listing=gpg(keyring,"--with-colons","--list-secret-keys",stdout=subprocess.PIPE).stdout
    need(not any(line.startswith((b"sec:",b"ssb:")) for line in listing.splitlines()))
    verify_signature(keyring,canon(body),signature,signer)
    return {"status":"LAB_SIGNATURE_AND_SUPPLIED_ANCHOR_MATCH",
            "sequence":sequence,"phase":phase,"independent_latest_anchor_attested":False,
            "mutation_authorized":False,"install_authorized":False,"restore_authorized":False}

def successor(previous,previous_signature,*,latest_anchor,phase,journal,challenge):
    # Only constructs the next statement; previous signature verification and
    # external durable compare-and-set must occur in the owner custody system.
    validate(previous)
    need(anchor(previous,previous_signature)==latest_anchor)
    need(phase in PHASES[previous["phase"]] and challenge!=previous["challenge"])
    return statement(transaction=previous["transaction"],plan=previous["plan"],
                     sequence=previous["sequence"]+1,previous=latest_anchor,
                     phase=phase,journal=journal,challenge=challenge)
