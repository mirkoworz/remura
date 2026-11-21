# REMURA TradingView v0.8.186 LAB — 21/11/2026 Europe/Rome
# Domain-separated SHA256 request for a FUTURE independent timestamp anchor.
# No external requests, secrets, uploads, or assertions of verified provenance.
"""Prepare a reproducible request digest from a locally validated synthetic ledger.

This tool only produces a hash to be anchored. It does not verify RFC3161
tokens, GitHub commit times or third-party signatures; no service is called.
"""
from __future__ import annotations
from hashlib import sha256
import json
import re
import sys

from local_capture_ledger_v0185_lab import review as review_chain
from holdout_freeze_v0182_lab import guard, FreezeError

DOMAIN = b"REMURA_TV_HOLDOUT_V0186_ANCHOR_REQUEST\0"
ALGORITHM = "SHA256_DOMAIN_SEPARATED_V1"
HEX = re.compile(r"^[0-9a-f]{64}$")

class AnchorRequestError(ValueError):
    pass

def canonical(x: object) -> bytes:
    # SHA256 over canonical UTF-8 JSON, no floating points permitted in ledger.
    return json.dumps(x, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")

def request(ledger: object) -> dict[str,object]:
    output: dict[str,object] = {
        "schema":"remura.tradingview.anchor_request.v0186.lab",
        "version":"0.8.186",
        "status":"INVALID_OR_NOT_PREPARED",
        "mode":"OFFLINE_UNANCHORED",
        "hash_algorithm":ALGORITHM,
        "request_digest_sha256":None,
        "fold":"UNKNOWN",
        "entries":None,
        "capture_chain_self_consistent":False,
        "request_submitted_to_tsa":False,
        "independent_timestamp_token_verified":False,
        "trusted_anchor_established":False,
        "capture_clock_proven":False,
        "trade_edge_proven":False,
        "network_calls_performed":0,
        "decision":"NO_GO_LIVE",
    }
    try:
        validity=review_chain(ledger)
        if validity.get("status")!="OFFLINE_UNANCHORED_CHAIN_CONSISTENT":
            raise AnchorRequestError("local_ledger_invalid")
        protocol=guard()
        if protocol.get("protocol")!="CVD_PROSPECTIVE_V2_PINNED":
            raise AnchorRequestError("frozen_protocol_drift")
        # Reuse complete, checked ledger bytes. Never emit the raw ledger,
        # identity, decision details or potentially sensitive slot timestamps.
        payload={
            "schema":"remura.tradingview.anchor_payload.v0186.lab",
            "protocol":"CVD_PROSPECTIVE_V2_PINNED",
            "fold":validity["fold"],
            "ledger":ledger,
        }
        digest=sha256(DOMAIN+canonical(payload)).hexdigest()
        output.update(
            status="REQUEST_HASH_READY_UNSUBMITTED",
            request_digest_sha256=digest,
            fold=validity["fold"],
            entries=validity["entries"],
            capture_chain_self_consistent=True,
        )
    except (AnchorRequestError, FreezeError, ValueError,TypeError, KeyError,UnicodeError,OSError,OverflowError):
        pass
    return output

def receipt_review(request_result: object, alleged_receipt: object) -> dict[str,object]:
    """Structural mismatch detection ONLY; no signature verification possible here."""
    status="RECEIPT_UNVERIFIED_OR_INVALID"
    if isinstance(request_result,dict) and request_result.get("status")=="REQUEST_HASH_READY_UNSUBMITTED":
        digest=request_result.get("request_digest_sha256")
        if (isinstance(digest,str) and HEX.fullmatch(digest)
                and isinstance(alleged_receipt,dict)
                and set(alleged_receipt)=={"request_digest_sha256","token_format","issuer"}
                and alleged_receipt.get("request_digest_sha256")==digest
                and alleged_receipt.get("token_format")=="RFC3161_UNVERIFIED_PLACEHOLDER"
                and alleged_receipt.get("issuer")=="UNVERIFIED"):
            status="DIGEST_MATCH_ONLY_SIGNATURE_NOT_VERIFIED"
    return {
        "schema":"remura.tradingview.anchor_receipt_structure.v0186.lab",
        "version":"0.8.186",
        "status":status,
        "signature_verified":False,
        "independent_timestamp_attested":False,
        "capture_clock_proven":False,
        "decision":"NO_GO_LIVE",
    }

def main(argv:list[str])->int:
    if argv != ["--synthetic-self-check"]:
        print("REMURA_TV_V0186_ANCHOR=NO_GO_BAD_ARGUMENTS")
        return 2
    from local_capture_ledger_v0185_lab import demo
    output=request(demo())
    if output["status"]!="REQUEST_HASH_READY_UNSUBMITTED" or not output["request_digest_sha256"]:
        print("REMURA_TV_V0186_ANCHOR=NO_GO_INVALID_SAMPLE")
        return 3
    print(json.dumps(output,sort_keys=True,separators=(",",":")))
    return 0

if __name__=="__main__":
    sys.exit(main(sys.argv[1:]))
