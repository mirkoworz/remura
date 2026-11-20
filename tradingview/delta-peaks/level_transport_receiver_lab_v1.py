# REMURA v0.8.110 LAB — 16/11/2026 17:23 CET
"""Offline synthetic receiver core. No HTTP service, real credentials or durable storage."""
import json,re,hmac,threading
from hashlib import sha256
from level_local_probe_v1 import parse,clock,need,unique
from level_local_probe_batch_v1 import IDENTITY
SCHEMA="remura.tv.level.transport.preview.v1"
CAPACITY=12
LAG_MS=120000
MAX_BYTES=15000
def digest(s):
    return sha256(s.encode("utf-8")).hexdigest()
def decode(raw):
    need(type(raw) is str and len(raw.encode("utf-8"))<=MAX_BYTES)
    envelope=json.loads(raw,object_pairs_hook=unique,parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
    need(type(envelope) is dict and set(envelope)=={"schema","snapshot"} and envelope["schema"]==SCHEMA)
    row=envelope["snapshot"]
    need(type(row) is dict and row.get("mode")=="REALTIME_WEBHOOK_PREVIEW" and row.get("version")=="0.9.3-level-preview")
    # Reuse the already-tested structural checks only. Never emit the normalized
    # row as a local log or claim it was produced by the compiled Pine.
    normalized=dict(row,mode="REALTIME_LOCAL_LOG",version="0.9.2-level-lab")
    validated=parse(json.dumps(normalized,allow_nan=False,separators=(",",":")))
    identity=tuple(row[k] for k in IDENTITY)+(validated["configuration_digest"],)
    op,cl=row["snapshot_open_ms"],row["snapshot_close_ms"]
    need(cl%300000==0 and cl-op==300000)
    return row,identity,validated
class Receiver:
    """Single process, explicit synthetic session; lock covers dedup and first receipt.
    Clock is an injected *fixture* receiver clock, not an authenticated timestamp.
    Token hash is provisioned independently; no token or raw market data returned.
    """
    def __init__(self, *, key_hash, expected_identity, after_close_ms, now, enabled=False, synthetic=False):
        need(synthetic is True and type(enabled) is bool and callable(now))
        need(type(key_hash) is str and re.fullmatch(r"[0-9a-f]{64}",key_hash) is not None)
        need(type(expected_identity) is tuple and len(expected_identity)==len(IDENTITY)+1)
        self._cutoff=clock(after_close_ms);need(self._cutoff%300000==0)
        self._key_hash=key_hash;self._identity=expected_identity
        self._now=now;self._enabled=enabled;self._lock=threading.Lock();self._rows={}
    def stop(self):
        with self._lock:self._enabled=False
    def receive(self, raw, *, capability):
        with self._lock:
            if not self._enabled:return {"status":"OFF"}
            if (type(capability) is not str or re.fullmatch(r"[0-9a-f]{64}",capability) is None
                or not hmac.compare_digest(digest(capability),self._key_hash)):
                return {"status":"DENIED"}
            try:
                # Receiver samples its own fixture clock, not a timestamp in JSON.
                received=clock(self._now(),whole_second=False)
                row,identity,validated=decode(raw)
                cl=row["snapshot_close_ms"];sent=row["sender_clock_ms"]
                need(identity==self._identity and self._cutoff<cl<=sent<=received)
                need(received-cl<=LAG_MS)
                body=digest(raw)
                previous=self._rows.get(cl)
                if previous is not None:
                    if hmac.compare_digest(previous["body_digest"],body):
                        return {"status":"DUPLICATE","first_received_ms":previous["first_received_ms"]}
                    return {"status":"CONFLICT"}
                need(not self._rows or (cl>max(self._rows) and received>=max(r["first_received_ms"] for r in self._rows.values())))
                if len(self._rows)>=CAPACITY:return {"status":"CAPACITY"}
                self._rows[cl]={"body_digest":body,"first_received_ms":received,
                    "present_levels":validated["present_levels"]}
                return {"status":"ACCEPTED_SYNTHETIC","first_received_ms":received}
            except (ValueError,TypeError,OverflowError,RecursionError,KeyError):
                return {"status":"INVALID"}
    def summary(self):
        with self._lock:
            return {"schema":"remura.tv.level.transport.synthetic.audit.v1","accepted":len(self._rows),
                "present_slots":sum(r["present_levels"] for r in self._rows.values()),
                "enabled":self._enabled,"capacity":CAPACITY,"origin":"SYNTHETIC",
                "durable_receipt":False,"receipt_authenticated":False,"source_attested":False,
                "calendar_equivalence_attested":False,"scientific_admission":False,
                "comparison_admitted":False,"operational_signal":False}
