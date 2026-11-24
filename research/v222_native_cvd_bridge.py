#!/usr/bin/env python3
"""REMURA A V22.2 LAB — native D1 text pair to a provisional V21.1 freeze.
Offline only. No D1 access, network, publication, alert or order. Receipt
metadata is operator supplied, NOT authenticated by this bridge. D1 text is
not an attestation of original HTTP wire bytes. Never admit TEST automatically.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
import subprocess
import base64

from v214_native_tv_cvd_pair_probe import (
    audit_native_pair, _native, _bounded_number, SOURCE_PIN,
)
from v211_raw_cvd_direction_admission import (
    RAW_SCHEMA, SOURCE_FAMILY, classify_raw, freeze_raw, adjudicate_raw,
)
from v209_private_decision_freezer import REPOSITORY_ROOT
from v208_github_decision_witness import manifest_for

UTC = timezone.utc
GATEWAY_PATH = "tradingview/delta-peaks/gateway-lab/worker_cvd_candidate.mjs"
_NODE = """
import fs from 'node:fs';
try {
  const x=JSON.parse(fs.readFileSync(0,'utf8'));
  const m=await import('data:text/javascript;base64,'+x.gateway);
  for(const r of x.receipts){
    const p=JSON.parse(r.raw);
    const v=m.validateCvdEnvelope(p,r.received);
    if(v.transportTimely!==true || v.timely!==false ||
       v.barCloseMs!==p.snapshot.bar_close_ms) throw Error('gate');
  }
} catch { process.exit(1); }
"""

def _full_gateway(prior: bytes, current: bytes, times: tuple[int,int]) -> None:
    # Load the exact historical validator from an existing local Git object.
    # No fetch, no checkout, no Worker invocation. Missing history fails closed.
    try:
        src = subprocess.run(
            ["git","--no-replace-objects","show",f"{SOURCE_PIN}:{GATEWAY_PATH}"],
            cwd=REPOSITORY_ROOT, capture_output=True, timeout=5, check=True,
        ).stdout
        if not 1 <= len(src) <= 100_000:
            raise ValueError("pinned_gateway_size")
        payload=json.dumps({"gateway":base64.b64encode(src).decode("ascii"),
            "receipts":[{"raw":raw.decode("utf-8"),"received":t}
                for raw,t in zip((prior,current),times)]}).encode("utf-8")
        subprocess.run(["node","--input-type=module","-e",_NODE],
            input=payload,capture_output=True,timeout=5,check=True,
            cwd=REPOSITORY_ROOT)
    except (OSError, subprocess.SubprocessError, UnicodeError):
        raise ValueError("pinned_native_gateway_check_failed") from None

def _iso(t: int) -> str:
    return datetime.fromtimestamp(t//1000,UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

def prepare_pair(prior: bytes, current: bytes, *,
                 prior_received_ms: int, current_received_ms: int):
    """Return DERIVED adapter bytes plus private lineage, never a signal."""
    probe=audit_native_pair(prior,current)
    a,b=_native(prior),_native(current)
    times=(prior_received_ms,current_received_ms)
    for receipt, native in zip(times,(a,b)):
        if type(receipt) is not int or not 0 <= receipt-native["close"] <= 120000:
            raise ValueError("native_receipt_lag_invalid")
    if times[0]>=times[1]:
        raise ValueError("native_receipt_order_invalid")
    _full_gateway(prior,current,times)
    derived=json.dumps({
        "schema":RAW_SCHEMA,"symbol":"FX:EURUSD","timeframe":"M5",
        "source_family":SOURCE_FAMILY,
        "prior_close_utc":_iso(a["close"]),"event_close_utc":_iso(b["close"]),
        "prior_cvd":format(_bounded_number(a["cvd"]["segment_cvd"]),"f"),
        "event_cvd":format(_bounded_number(b["cvd"]["segment_cvd"]),"f"),
    },sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")
    if classify_raw(derived)[0]!=probe["proxy_delta_sign_for_private_research"]:
        raise ValueError("derived_side_mismatch")
    lineage={
        "native_text_sha256":probe["original_source_sha256"],
        "native_received_ms":list(times),"native_bar_close_ms":probe["bar_close_ms"],
        "native_gateway_reference":SOURCE_PIN,
        "native_gateway_test_only":True,
        "native_receipts_independently_authenticated":False,
    }
    return derived,lineage

def freeze_native_candidate(prior: bytes,current: bytes,market: dict,*,
                            prior_received_ms: int,current_received_ms: int):
    """Fresh local candidate only; no writes or witness. Never backdate."""
    derived,lineage=prepare_pair(prior,current,
        prior_received_ms=prior_received_ms,current_received_ms=current_received_ms)
    # Round receipt UP conservatively; actual millisecond clocks remain bound.
    receipt=_iso(((current_received_ms+999)//1000)*1000)
    ledger,_=freeze_raw(derived,receipt,market,as_of=datetime.now(UTC))
    row=ledger["decisions"][0]
    row["native_lineage_v222"]=lineage
    return ledger,manifest_for(row),derived

def audit_binding(ledger: dict, manifest: dict, prior: bytes,current: bytes,*,
                  prior_received_ms: int,current_received_ms: int) -> bytes:
    """Recreate adapter and verify both original hashes and receipt metadata.
    This alone never verifies provider identity or prospective admission.
    """
    derived,lineage=prepare_pair(prior,current,
        prior_received_ms=prior_received_ms,current_received_ms=current_received_ms)
    row=ledger["decisions"][0]
    if row.get("native_lineage_v222")!=lineage or manifest!=manifest_for(row):
        raise ValueError("native_lineage_commitment_mismatch")
    import hashlib
    if hashlib.sha256(derived).hexdigest()!=row.get("source_event_sha256"):
        raise ValueError("derived_source_commitment_mismatch")
    return derived

if __name__=="__main__":
    print(json.dumps({"status":"OFFLINE_BRIDGE_ONLY_NO_PRIVATE_INPUT",
        "admitted_forward_decisions":0,"network_calls":0,"files_written":0}))
