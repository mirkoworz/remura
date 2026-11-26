"""V30.6 LAB. Build the experimental packet directly from captured bytes.
No I/O or automatic activation. Capture times must be attested by caller.
"""
import json
from v299_source_correlation import observe,ms
from v306_observation_prepare import prepare,M15

def assemble(raw,capture_ms,clock,rule_bytes,*,enabled=False):
    if enabled is not True:raise ValueError("disabled")
    if set(raw)!={"price","footprint","cot"}:raise ValueError("sources")
    if any(type(v) is not bytes or not 0<len(v)<=4000000 for v in raw.values()):raise ValueError("source_bytes")
    symbol,provider,broker,updated,payload=json.loads(raw["price"])
    p=json.loads(payload)
    if symbol!="EURUSD" or provider!="ctrader" or not broker or p.get("providerSymbol")!=broker:raise ValueError("identity")
    records=json.loads(raw["footprint"]);cot=json.loads(raw["cot"])
    for record in records:
        record["original"]=bytes.fromhex(record.pop("original_hex"))
    if type(records) is not list or len(records)>288:raise ValueError("window")
    now=clock()
    if type(now) is not int or type(capture_ms) is not int or not 0<=now-capture_ms<=30000:raise ValueError("capture")
    report=observe(records,cot,p,updated,capture_ms,now,symbol=symbol)
    if report["price"]["status"]!="DESCRIPTIVE_ONLY":
        return {"status":"INELIGIBLE","prospective_admitted":False}
    bound=min(capture_ms,ms(updated))
    bars=[{"open_ms":ms(v["t"]),"close":v["c"]} for v in p["timeframes"]["M15"] if ms(v["t"])+M15<=bound][-4:]
    if len(bars)!=4 or any(y["open_ms"]-x["open_ms"]!=M15 for x,y in zip(bars,bars[1:])):
        return {"status":"INELIGIBLE","prospective_admitted":False}
    return prepare(bars,report["footprint"],report["cot"],raw,capture_ms,clock,rule_bytes,enabled=True)
