"""REMURA V30.3 LAB — 26/11/2026 Europe/Rome.
Pre-registered candidate classifier, no I/O, no orders, no prospective admission.
Inputs must be frozen together before evaluating outcomes. No tuning on results.
"""
from decimal import Decimal
def sign(v):
    d=Decimal(str(v))
    if not d.is_finite():raise ValueError("nonfinite")
    return (d>0)-(d<0)
def candidate(price_closes,footprint,cot):
    if type(price_closes) is not list or len(price_closes)!=4:raise ValueError("four_closed_m15")
    p=[Decimal(str(v)) for v in price_closes]
    if any(not d.is_finite() or d<=0 for d in p):raise ValueError("price")
    if (footprint.get("status")!="DESCRIPTIVE_ONLY" or
        type(footprint.get("segment_bars")) is not int or footprint["segment_bars"]<12 or
        cot.get("status")!="PUBLIC_DESCRIPTIVE_ONLY"):
        return {"status":"INELIGIBLE","prospective_admitted":False}
    a=sign(p[-1]-p[0]);b=sign(footprint["segment_cvd"])
    c=sign(cot["asset_manager_weekly_change_pp"])
    return {"status":"EXPLORATORY_RULE","sides":{"price_only":a,"footprint_only":b,
        "footprint_plus_cot":b if b==c else 0},"prospective_admitted":False}
