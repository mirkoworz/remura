# REMURA v0.8.181 LAB — 19/11/2026, sessione 06:46 CET
"""Bounded encrypted scientific capture candidate; no CLI, scheduler or sink.
Caller must establish owner authorization, budget, host/swap safety, pinned
recipient and independent custody BEFORE invoking with real credentials.
This adapter is not a sandbox or authorization boundary. Never log exceptions
or intermediate plaintext; no claims of memory erasure, origin or completeness.
"""
import hashlib,json,re,subprocess
from urllib.parse import quote
from cvd_test_batch_reader_v4 import plan,unpack,MAX_OBSERVED_READS
from cvd_test_fold_reader_v2 import fetch_page
from cvd_pilot_analytic_reader_v1 import SYMBOL,VERSION,M5
from cloudflare_d1_readonly_audit import AuditError,api_request,require_account_id,require_account_token
from d1_test_target_preflight_v1 import MAIN_DB,TEST_DB,inspect_verified_inventory
from cvd_archive_preview_v1 import validate_windows
from cvd_oos_protocol_preview_v2 import FOLDS,clock,digest
from remura_tv_bridge_preview_v1 import EXPECTED_COLUMNS

MAX_BYTES=16*1024*1024
MAX_SLOTS=288
FPR=re.compile(r"[0-9A-F]{40}\Z")

def need(ok):
    if not ok: raise AuditError("encrypted_capture_denied")

def wire(x):
    return json.dumps(x,sort_keys=True,separators=(",",":"),ensure_ascii=True,allow_nan=False).encode("ascii")

def scope(start,end,now):
    pages=plan(start,end,now)
    need((end-start)//M5+1<=MAX_SLOTS)
    matches=[(name,clock(a),clock(b)) for name,a,b in FOLDS if clock(a)<=start<=end<clock(b)]
    need(len(matches)==1)
    name,_,fold_end=matches[0]
    return name,min(now,fold_end-1),pages

def package(windows,*,start,end,now,reads):
    fold,cutoff,pages=scope(start,end,now)
    need(type(reads) is int and 0<=reads<=MAX_OBSERVED_READS)
    need(type(windows) is list and len(windows)==len(pages))
    for w,(a,b) in zip(windows,pages):
        need(type(w) is dict and set(w)=={"start_ms","end_ms","rows"} and
             (w["start_ms"],w["end_ms"])==(a,b) and type(w["rows"]) is list)
        for r in w["rows"]:
            need(type(r) is dict and set(r)==EXPECTED_COLUMNS and r["symbol"]==SYMBOL and
                 r["timeframe"]=="5" and r["version"]==VERSION and
                 type(r["bar_close_ms"]) is int and a<=r["bar_close_ms"]<=b and
                 type(r["received_at_ms"]) is int and r["received_at_ms"]<=cutoff and
                 type(r["raw_json"]) is str)
    # Preserve original rows even if semantic validation fails, but never
    # admit them. A wrong query scope/shape is a hard failure, not an archive.
    try:
        _,stats=validate_windows(windows,as_of_ms=now)
        quality="VALIDATED_REQUEST_SCOPE_ONLY"
    except (ValueError,TypeError,KeyError,OverflowError,AuditError):
        stats=None
        quality="QUARANTINED_VALIDATION_FAILURE"
    body=wire({"schema":"remura.tv.cvd.encrypted.capture.v1","fold":fold,
        "protocol_sha256":digest(),"symbol":SYMBOL,"sender_version":VERSION,
        "start_ms":start,"end_ms":end,"capture_ms":now,"receipt_cutoff_ms":cutoff,
        "windows":windows,"quality":quality,"coverage":stats,"rows_read":reads,
        "rows_written":0,"snapshot_atomic_across_pages":False,
        "independent_provenance":False,"conflict_ledger_available":False,
        "scientific_admission":False,"outcomes_computed":False})
    need(0<len(body)<=MAX_BYTES)
    return body

def seal(home,recipient,body):
    # home is an owner-prepared isolated public-only keyring. Exact encryption
    # key/subkey fingerprint must be independently verified, not just a UID.
    need(type(recipient) is str and FPR.fullmatch(recipient) and type(body) is bytes and 0<len(body)<=MAX_BYTES)
    base=["/usr/bin/gpg","--no-options","--homedir",str(home),"--batch","--no-tty",
          "--no-auto-key-retrieve","--auto-key-locate","local"]
    def invoke(args,data=None):
        p=subprocess.run(base+args,input=data,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,
                         timeout=60,check=True)
        return p.stdout
    try:
        keys=invoke(["--with-colons","--list-secret-keys"])
        need(not any(line.startswith((b"sec:",b"ssb:")) for line in keys.splitlines()))
        ciphertext=invoke(["--trust-model","always","--cipher-algo","AES256","--compress-algo","none",
                           "--force-mdc","--recipient",recipient+"!","--encrypt","--output","-"],body)
        need(0<len(ciphertext)<=MAX_BYTES+65536)
        return ciphertext
    except (OSError,subprocess.SubprocessError,ValueError):
        raise AuditError("encrypted_capture_crypto_denied") from None

def capture(account_id,token,*,start,end,now,home,recipient,approved=False,guard=None):
    # Guard must be supplied by reviewed host/budget/custody integration.
    # It is invoked before and after each remote operation; it is not proof.
    need(approved is True and callable(guard) and type(recipient) is str and FPR.fullmatch(recipient))
    fold,cutoff,pages=scope(start,end,now)
    try:
        guard()
        account=require_account_id(account_id); token=require_account_token(token)
        base="/accounts/"+quote(account,safe="")+"/d1/database"
        ids=inspect_verified_inventory(api_request("GET",base+"?page=1&per_page=100",token))
        need(ids[MAIN_DB]!=ids[TEST_DB])
        guard()
        windows=[]; reads=0
        for a,b in pages:
            guard()
            rows,meta=unpack(fetch_page(account,ids[TEST_DB],token,a,b,cutoff))
            need(meta[0] is not None and meta[1]==0)
            reads+=meta[0]; need(reads<=MAX_OBSERVED_READS)
            windows.append({"start_ms":a,"end_ms":b,"rows":rows})
            guard()
        body=package(windows,start=start,end=end,now=now,reads=reads)
        guard()
        cipher=seal(home,recipient,body)
        guard()
        # Only encrypted bytes and a non-directional receipt leave adapter.
        # Sink, independent witness, recovery and late-arrival reconciliation
        # remain separate gates; receipt is not an archive durability claim.
        return cipher,{"fold":fold,"start_ms":start,"end_ms":end,
            "capture_ms":now,"receipt_cutoff_ms":cutoff,"query_rows_read":reads,
            "query_rows_written":0,"cipher_sha256":hashlib.sha256(cipher).hexdigest(),
            "cipher_bytes":len(cipher),"outcomes_computed":False,"custody_verified":False}
    except Exception:
        raise AuditError("encrypted_capture_failed_closed") from None
