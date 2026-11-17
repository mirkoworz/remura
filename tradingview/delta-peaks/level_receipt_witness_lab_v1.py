# REMURA v0.8.126 LAB — 17/11/2026 CET
"""Synthetic HMAC custody witness and external latest anchor contract.
Not a real independent custodian, signature, encrypted backup or restore authority.
"""
import hashlib,hmac,re
from level_receipt_custody_lab_v1 import canonical,hashobj,hex64,integer,need,verify_snapshot
ZERO="0"*64
GEN=re.compile(r"[0-9a-f]{32}")
SCHEMA="remura.tv.level.synthetic.custody.witness.v1"
DOMAIN=b"REMURA-LEVEL-CUSTODY-LAB-V1\x00"
MAX_SEQUENCE=10000
def generation(x):return type(x) is str and GEN.fullmatch(x) is not None and x!="0"*32
def key_ok(k):return type(k) is bytes and len(k)==32
def mac(body,key):
    need(key_ok(key))
    return hmac.new(key,DOMAIN+canonical(body),hashlib.sha256).hexdigest()
def validate_body(body):
    need(type(body) is dict and set(body)=={"schema","generation","sequence","previous_anchor","snapshot_pin"})
    need(body["schema"]==SCHEMA and generation(body["generation"]) and integer(body["sequence"],1,MAX_SEQUENCE))
    need(hex64(body["previous_anchor"]) and hex64(body["snapshot_pin"]))
    need(body["snapshot_pin"]!=ZERO and (body["previous_anchor"]==ZERO)==(body["sequence"]==1))
def create(pin,gen,seq,prev,key):
    body={"schema":SCHEMA,"generation":gen,"sequence":seq,"previous_anchor":prev,"snapshot_pin":pin}
    validate_body(body)
    record={"body":body,"mac":mac(body,key)}
    return record,hashobj(record)
def verify_witness(record,key,*,latest_anchor,latest_generation,latest_sequence,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True and key_ok(key))
    need(hex64(latest_anchor) and generation(latest_generation) and integer(latest_sequence,1,MAX_SEQUENCE))
    need(type(record) is dict and set(record)=={"body","mac"} and hex64(record["mac"]))
    body=record["body"];validate_body(body)
    need(body["generation"]==latest_generation and body["sequence"]==latest_sequence)
    need(hmac.compare_digest(mac(body,key),record["mac"]) and hmac.compare_digest(hashobj(record),latest_anchor))
    return body["snapshot_pin"]
def genesis(snapshot_pin,gen,key,*,synthetic=False,ingress_closed=False):
    need(synthetic is True and ingress_closed is True)
    return create(snapshot_pin,gen,1,ZERO,key)
def advance(previous,key,*,latest_anchor,latest_generation,latest_sequence,new_generation,new_snapshot_pin,synthetic=False,ingress_closed=False):
    verify_witness(previous,key,latest_anchor=latest_anchor,latest_generation=latest_generation,latest_sequence=latest_sequence,synthetic=synthetic,ingress_closed=ingress_closed)
    need(generation(new_generation) and new_generation!=latest_generation and latest_sequence<MAX_SEQUENCE)
    # A fixture authority supplies the approved new pin. This function does NOT
    # establish that a candidate is newer, authorize migration, or persist CAS.
    return create(new_snapshot_pin,new_generation,latest_sequence+1,latest_anchor,key)
def verify_recovery(db,record,key,*,latest_anchor,latest_generation,latest_sequence,synthetic=False,ingress_closed=False):
    pin=verify_witness(record,key,latest_anchor=latest_anchor,latest_generation=latest_generation,latest_sequence=latest_sequence,synthetic=synthetic,ingress_closed=ingress_closed)
    out=verify_snapshot(db,pin,synthetic=synthetic,ingress_closed=ingress_closed)
    return {**out,"status":"SYNTHETIC_WITNESS_AND_SNAPSHOT_MATCH","fixture_mac_verified":True,"fixture_latest_anchor_matched":True,
            "generation_migration_verified":False,"independent_pin_verified":False,"restore_authorized":False,"may_open":False}
