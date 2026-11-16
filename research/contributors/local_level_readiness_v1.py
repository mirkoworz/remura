# REMURA Contributors v0.38 LAB — 16/11/2026 17:23 CET
"""Synthetic metadata comparison only against the actual D local-probe validator.
No source mapping, price-distance test, authenticated availability or enrollment."""
import json
from collections import Counter
from datetime import datetime,timezone
from level_confluence_v1 import compare
from ledger_v1 import _time
from level_local_probe_v1 import parse,need
D_PIN="a44644f653e3f6d423f2120b678dda7eeaecc83e"
FIELDS={"calendar","timezone","session","method","rank","period_end_ms","configuration_digest","known_utc"}
def utc(ms):
    return datetime.fromtimestamp(ms/1000,timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def readiness(raw,manual,*,asof_utc,synthetic=False):
    need(synthetic is True and type(manual) is list and len(manual)<=200)
    cutoff=_time(asof_utc)
    d=parse(raw);p=json.loads(raw)
    need(p["mode"]=="REALTIME_LOCAL_LOG")
    entries=[]
    for item in manual:
        need(type(item) is dict and set(item)=={"entry","declared"})
        m=item["declared"]
        need(type(m) is dict and set(m)==FIELDS)
        need(all(type(m[k]) is str and 0<len(m[k])<=128 for k in ("calendar","timezone","session","method","configuration_digest")))
        need(type(m["rank"]) is int and 1<=m["rank"]<=3 and type(m["period_end_ms"]) is int)
        need(_time(m["known_utc"])>=_time(item["entry"]["data"]["observed_utc"]))
        entries.append(item["entry"])
    e=compare(entries,[],[],asof_utc=asof_utc,synthetic=True)
    approved={r["manual_id"] for r in e["manual"]}
    out={"schema":"remura.de.local.level.readiness.synthetic.v1","d_pin":D_PIN,
        "manual_approved_asof":len(approved),"manual_review_excluded":e["excluded_manual"],
        "automatic_present_slots":None,"declared_match_pairs":0,"mismatch_pair_counts":{},
        "manual_metadata_late":0,"price_comparison_performed":False,
        "receipt_authenticated":False,"source_equivalence_attested":False,
        "source_independence_verified":False,"scientific_admission":False,
        "operational_signal":False,"orders_enabled":False,"notifications_enabled":False,
        "blockers":["RECEIPT_UNATTESTED","INSTRUMENT_PRODUCT_CONTRACT_UNATTESTED",
                    "CONFIGURATION_AND_CALENDAR_DECLARATIONS_UNATTESTED","NO_VALIDATED_PRICE_RULE"]}
    if p["sender_clock_ms"]>int(cutoff.timestamp()*1000):
        return dict(out,status="D_CLAIM_AFTER_CUTOFF")
    out["automatic_present_slots"]=d["present_levels"]
    reasons=Counter()
    for item in manual:
        entry=item["entry"];m=item["declared"];q=entry["data"]
        if entry["id"] not in approved:continue
        if _time(m["known_utc"])>cutoff:
            out["manual_metadata_late"]+=1;continue
        for level in p["levels"]:
            if level["price"] is None:continue
            # No PREVIOUS_MONTH alias: D explicitly means previous OBSERVED month.
            mismatches=[]
            if (q["market"],q["provider"],q["ticker"])!=("EURUSD",p["feed"],p["ticker"]):mismatches.append("DECLARED_LABEL_MISMATCH")
            if q["kind"]!="DELTA_PEAK" or q["period"]!=level["period"] or m["rank"]!=level["rank"]:mismatches.append("PERIOD_OR_RANK_MISMATCH")
            if (q["anchor_utc"]!=utc(level["period_start_ms"]) or m["period_end_ms"]!=level["period_end_ms"]):mismatches.append("PERIOD_BOUNDS_MISMATCH")
            if (m["calendar"],m["timezone"],m["session"])!=(p["calendar"],p["timezone"],p["session"]):mismatches.append("CALENDAR_DECLARATION_MISMATCH")
            if m["method"]!=level["method"]:mismatches.append("METHOD_DECLARATION_MISMATCH")
            if m["configuration_digest"]!=d["configuration_digest"]:mismatches.append("CONFIG_DECLARATION_MISMATCH")
            if mismatches:reasons.update(mismatches)
            else:out["declared_match_pairs"]+=1
    out["mismatch_pair_counts"]=dict(sorted(reasons.items()))
    return dict(out,status="BLOCKED_UNATTESTED_METADATA")
