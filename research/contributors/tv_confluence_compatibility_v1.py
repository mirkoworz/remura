# REMURA Contributors v0.34 LAB — 16/11/2026 15:59 CET
"""Synthetic D -> E compatibility gate, no relabeling, private rows or signal.
Uses the actual pinned D validator in the cross-track CI, not a replacement.
"""
from collections import Counter
from datetime import datetime,timezone
from level_confluence_v1 import compare
from ledger_v1 import _time
from cvd_telemetry_preview_v1 import validate,SYMBOL,VERSION
from cvd_radar_preview_v1 import describe

def bridge(envelope,*,received_ms,manual,asof_utc,synthetic=False):
    if synthetic is not True:raise ValueError("synthetic_only")
    cutoff=_time(asof_utc)
    asof_ms=int(cutoff.timestamp())*1000
    v=validate(envelope,received_ms=received_ms)
    t=v["bar_close_ms"]
    if not t<=received_ms<=t+120000:raise ValueError("receipt_clock")
    # Existing E validator owns manual eligibility at the same cutoff; no
    # automatic rows constructed until exact identity/method/anchor is proven.
    e=compare(manual,[],[],asof_utc=asof_utc,synthetic=True)
    eligible={item["manual_id"] for item in e["manual"]}
    groups=Counter(r["data"]["provider"] for r in manual if r["id"] in eligible)
    result={"schema":"remura.de.level.compatibility.synthetic.v1","asof_utc":asof_utc,
        "source_symbol":SYMBOL,"source_version":VERSION,"manual_approved_asof":len(eligible),
        "manual_excluded":e["excluded_manual"],"manual_provider_counts":dict(sorted(groups.items())),
        "automatic_levels":[],"descriptive_near_count":0,"price_comparison_performed":False,
        "source_equivalence_attested":False,"source_independence_verified":False,
        "scientific_admission":False,"operational_signal":False,"orders_enabled":False,"notifications_enabled":False}
    if received_ms>asof_ms:
        return {**result,"status":"D_NOT_KNOWN_AT_CUTOFF","radar_status":None}
    r=describe(envelope,received_ms=received_ms,as_of_ms=asof_ms)
    p=envelope["snapshot"]
    # D's level origin is when a level was established, not E period anchor.
    # D's FX prefix does not identify OANDA/FXCM, product, contract or method.
    # Retain only public schema-level labels and reasons, never manual IDs/price.
    for name,price in sorted(p["levels"].items()):
        if price is None:continue
        result["automatic_levels"].append({"level":name,"status":"NOT_COMPARABLE",
            "reasons":["EXACT_FEED_PRODUCT_NOT_ATTESTED","PERIOD_ANCHOR_NOT_ATTESTED","LEVEL_METHOD_NOT_ATTESTED"]})
    return {**result,"status":"COMPATIBILITY_BLOCKED" if result["automatic_levels"] else "NO_LEVELS",
            "radar_status":r["status"],"available_at_utc":datetime.fromtimestamp(received_ms/1000,timezone.utc).isoformat(timespec="milliseconds")}
