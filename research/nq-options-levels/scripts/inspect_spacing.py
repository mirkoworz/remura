#!/usr/bin/env python3
"""Inspect sorted operational-zone spacing. Exploratory only; no trading."""
import argparse
import json
from pathlib import Path

def inspect(levels):
    if (not isinstance(levels,list) or len(levels)<3 or
        any(type(x) not in (int,float) or x<=0 for x in levels) or
        len(set(levels)) != len(levels) or levels != sorted(levels,reverse=True)):
        raise ValueError("levels must be >=3 unique positive descending numbers")
    gaps=[levels[i]-levels[i+1] for i in range(len(levels)-1)]
    step0=min(gaps)
    hops=[max(1,round(g/step0)) for g in gaps]
    indices=[0]
    for hop in hops:
        indices.append(indices[-1]+hop)
    mx=sum(indices)/len(indices)
    my=sum(levels)/len(levels)
    denom=sum((x-mx)**2 for x in indices)
    slope=sum((x-mx)*(y-my) for x,y in zip(indices,levels))/denom
    intercept=my-slope*mx
    residuals=[round(y-(intercept+slope*x),2) for x,y in zip(indices,levels)]
    return {
        "adjacent_gaps_points":gaps,
        "inferred_hops_descriptive":hops,
        "estimated_grid_spacing_points":round(-slope,2),
        "max_abs_fit_residual_points":max(abs(r) for r in residuals),
        "fit_residuals_points":residuals,
        "publication_time_verified":False,
        "status":"POST_HOC_PATTERN_ONLY_NOT_A_TRADING_SIGNAL",
        "caution":"Fitted lattice does not prove options/GEX/volatility/formula; unpublished intermediate grid positions are NOT operational zones."
    }

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("manual",type=Path)
    args=p.parse_args()
    with args.manual.open(encoding="utf-8") as f:
        doc=json.load(f)
    print(json.dumps(inspect(doc["levels"]),ensure_ascii=False,indent=2))

if __name__=="__main__":
    main()
