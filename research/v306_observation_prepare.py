"""REMURA V30.6 LAB. Prepare a complete local observation packet, no I/O.
Not an independent witness. Never admit an observation from this module alone.
The caller must capture actual source bytes, preserve them privately and
verify a signed timestamp before the entry boundary.
"""
import hashlib,json
from v303_science_candidate import candidate
from v304_local_freeze import canonical
M15=900000
def h(data):return hashlib.sha256(data).hexdigest()
def prepare(price_bars,footprint,cot,source_bytes,capture_ms,clock,rule_bytes,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    now=clock()
    if type(now) is not int or type(capture_ms) is not int or not 0<=now-capture_ms<=30000:raise ValueError("capture")
    if set(source_bytes)!={"price","footprint","cot"} or any(type(v) is not bytes or not 0<len(v)<=4000000 for v in source_bytes.values()):raise ValueError("source_bytes")
    if type(rule_bytes) is not bytes or not rule_bytes:raise ValueError("rule")
    if len(price_bars)!=4:raise ValueError("bars")
    times=[v["open_ms"] for v in price_bars]
    if any(type(t) is not int or t%M15 for t in times) or any(b-a!=M15 for a,b in zip(times,times[1:])) or not 0<=capture_ms-times[-1]-M15<=1800000:raise ValueError("bar_clock")
    if footprint.get("status")!="DESCRIPTIVE_ONLY" or cot.get("status")!="PUBLIC_DESCRIPTIVE_ONLY":return {"status":"INELIGIBLE","prospective_admitted":False}
    close=footprint.get("bar_close_ms")
    if type(close) is not int or not 0<=capture_ms-close<=600000:return {"status":"INELIGIBLE","prospective_admitted":False}
    if type(cot.get("public_read_ms")) is not int or cot["public_read_ms"]>capture_ms:return {"status":"INELIGIBLE","prospective_admitted":False}
    decision=candidate([v["close"] for v in price_bars],footprint,cot)
    if decision["status"]!="EXPLORATORY_RULE":return decision
    packet={"schema":"remura-v306-observation-v1","symbol":"EURUSD",
        "capture_ms":capture_ms,"prepared_ms":now,"entry_not_before_ms":(now//M15+1)*M15,
        "rule_sha256":h(rule_bytes),"source_sha256":{k:h(v) for k,v in source_bytes.items()},
        "sides":decision["sides"],"prospective_admitted":False}
    raw=canonical(packet)
    return {"status":"PREPARED_ONLY","packet":packet,"commitment":h(raw),
            "prospective_admitted":False}
