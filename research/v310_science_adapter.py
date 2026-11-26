"""V31.0 LAB — same-feed research adapter, no network or activation.
The comparison with cTrader is descriptive, not a basis for price substitution.
"""
from v310_multifeed import TV,M15,m15,tv_bar
from v303_science_candidate import candidate
from v300_paired_outcomes import evaluate
def prepare(records,asof,footprint,cot):
    bars=m15([tv_bar(m,raw,h,asof) for m,raw,h in records],asof)
    last=bars[-4:]
    if len(last)!=4 or any(b["open_ms"]-a["open_ms"]!=M15 for a,b in zip(last,last[1:])) or not 0<=asof-last[-1]["close_ms"]<=1800000:
        return {"status":"WAIT_COMPLETE_TV_M15","prospective_admitted":False}
    if not 0<=asof-footprint.get("bar_close_ms",0)<=600000 or not 0<cot.get("public_read_ms",0)<=asof:
        return {"status":"WAIT_SOURCE_CONTEXT","prospective_admitted":False}
    d=candidate([b["c"] for b in last],footprint,cot)
    if d["status"]!="EXPLORATORY_RULE":return d
    return {"status":"TV_LOCAL_CANDIDATE_ONLY","price_source":TV,"symbol":"EURUSD",
            "frozen_ms":asof,"entry_ms":(asof//M15+1)*M15,
            "sides":d["sides"],"input_evidence":[h for b in last for h in b["evidence"]],
            "prospective_admitted":False}
def outcomes(packet,records,asof,cost,hours):
    if packet.get("status")!="TV_LOCAL_CANDIDATE_ONLY" or packet.get("price_source")!=TV or packet.get("prospective_admitted") is not False or packet.get("entry_ms")!=(packet["frozen_ms"]//M15+1)*M15:raise ValueError("packet")
    bars=m15([tv_bar(m,raw,h,asof) for m,raw,h in records],asof)
    result=evaluate({"symbol":"EURUSD","mode":"TEST_DESCRIPTIVE_ONLY","frozen_ms":packet["frozen_ms"],"sides":packet["sides"]},bars,asof,cost,hours)
    return {**result,"price_source":TV,"execution_price_verified":False}
