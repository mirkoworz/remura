"""REMURA V30.4 LAB — 26/11/2026 06:57 CET.
Existing snapshots only; no network, no live signal, no prospective admission.
"""
from datetime import datetime
from math import isfinite
from v299_source_correlation import cot_context,ms

def number(x):
    return type(x) in (int,float) and isfinite(x)

def sentiment(doc,captured_ms,asof):
    if type(captured_ms) is not int or type(asof) is not int or not 0<captured_ms<=asof:
        raise ValueError("capture_clock")
    if doc.get("status")!="ok" or doc.get("source")!="Myfxbook Community Outlook":
        return {"status":"UNAVAILABLE"}
    row=doc.get("symbols",{}).get("EURUSD")
    if not isinstance(row,dict):return {"status":"MISSING_SYMBOL"}
    t=ms(row["t"]); updated=ms(doc["updatedAt"])
    if not 0<t<=updated<=captured_ms:raise ValueError("source_clock")
    if asof-t>3600000:return {"status":"STALE"}
    l,s=row.get("lPct"),row.get("sPct")
    if not all(number(v) and 0<=v<=100 for v in (l,s)) or abs(l+s-100)>1:
        raise ValueError("percentages")
    return {"status":"RETAIL_DESCRIPTIVE_ONLY","observed_ms":t,
            "capture_ms":captured_ms,"long_pct":l,"short_pct":s,
            "imbalance_pp":l-s,"vendor_freshness_verified":False,
            "independent_first_seen_verified":False}

def eurusd_cot(doc,asof):
    base=cot_context(doc,asof)
    if base["status"]!="PUBLIC_DESCRIPTIVE_ONLY":return base
    d=doc["dashboard"]
    cross=[c for c in d["crosses"] if c.get("symbol")=="EURUSD"]
    if len(cross)!=1:raise ValueError("cross_identity")
    x=cross[0]
    if x.get("legs")!=[{"currency":"EUR","weight":1}] or x.get("derivedNotDirectSpot") is not True or x.get("reportDate")!=base["report_date"]:
        raise ValueError("cross_mapping")
    a=x["assetManagerWeeklyRelativeChangePp"];l=x["leveragedFundsWeeklyRelativeChangePp"]
    if not number(a) or not number(l) or abs(a-base["asset_manager_weekly_change_pp"])>1e-9:
        raise ValueError("cross_numeric")
    return {**base,"symbol":"EURUSD","mapping":"EUR_FUTURES_VS_USD_REFERENCE",
            "asset_manager_relative_change_pp":a,"leveraged_relative_change_pp":l,
            "independent_usd_leg":"NOT_AVAILABLE","bilateral_independent":False,
            "direct_spot":False}

def combine_report(report,cot,retail,captured_ms,asof):
    if report.get("symbol")!="EURUSD" or report.get("prospective_admitted") is not False or report.get("asof_ms")!=asof:
        raise ValueError("report_scope")
    return {**report,"cot":eurusd_cot(cot,asof),
            "sentiment":sentiment(retail,captured_ms,asof),
            "prospective_admitted":False}
