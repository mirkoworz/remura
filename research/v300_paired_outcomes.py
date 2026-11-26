"""REMURA V30.0 LAB — offline paired outcome calculation.
No prospective admission: requires separate independently witnessed freeze.
Footprint is not native M1 CVD. Costs illustrative unless measured externally.
"""
from decimal import Decimal
M15=900000
ARMS=("price_only","footprint_only","footprint_plus_cot")

def dec(x):
    if type(x) not in (int,str,Decimal,float):
        raise ValueError("numeric")
    d=Decimal(str(x))
    if not d.is_finite():raise ValueError("finite")
    return d

def evaluate(decision,bars,asof_ms,cost_pips,hours):
    if hours not in (1,4,24) or type(hours) is not int:
        raise ValueError("horizon")
    frozen=decision["frozen_ms"]
    if type(frozen) is not int or type(asof_ms) is not int or not 0<frozen<=asof_ms:
        raise ValueError("clock")
    if decision["symbol"]!="EURUSD" or decision["mode"]!="TEST_DESCRIPTIVE_ONLY":
        raise ValueError("scope")
    sides=decision["sides"]
    if set(sides)!=set(ARMS) or any(type(v) is not int or v not in (-1,0,1) for v in sides.values()):
        raise ValueError("side")
    entry=(frozen//M15+1)*M15
    end=entry+hours*3600000
    if end>asof_ms:return {"status":"NOT_MATURE","prospective_admitted":False}
    grid={}
    for row in bars:
        t=row["open_ms"]
        if type(t) is not int or t%M15 or t in grid:raise ValueError("bar_clock")
        o,h,l,c=(dec(row[k]) for k in ("o","h","l","c"))
        if min(o,h,l,c)<=0 or h<max(o,l,c) or l>min(o,h,c):
            raise ValueError("ohlc")
        grid[t]=(o,c)
    times=list(range(entry,end,M15))
    if not all(t in grid for t in times):
        return {"status":"MISSING_CONTIGUOUS_BARS","prospective_admitted":False}
    cost=dec(cost_pips)
    if cost<0:raise ValueError("cost")
    change=(grid[times[-1]][1]-grid[entry][0])*10000
    result={name:str(Decimal(side)*change-(cost if side else 0)) for name,side in sides.items()}
    return {"status":"RETROSPECTIVE_ONLY","entry_ms":entry,"end_ms":end,
            "net_pips":result,"prospective_admitted":False}
