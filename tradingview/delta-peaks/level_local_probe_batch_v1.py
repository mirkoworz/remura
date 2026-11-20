# REMURA v0.8.109 LAB — 16/11/2026
"""Bounded review of user-supplied v0.9.2 local realtime-log claims.
No trusted receive clock, no prospective admission, no E wire, no persistence.
"""
import json
from decimal import Decimal
from collections import Counter
from level_local_probe_v1 import parse,clock,need

IDENTITY=("schema","version","symbol","feed","ticker","chart_type","timezone","session",
          "timeframe","calendar","product_status","contract","method_er")

def review(logs, *, after_close_ms):
    """A caller-declared exclusive cutoff scopes NEW closes; not trusted enrollment time.
    Preserve order, reject duplicate closes and calendar/config changes. Missing M5
    slots count elapsed grid slots, not expected tradable slots (sessions unattested).
    """
    cutoff=clock(after_close_ms)
    need(cutoff%300000==0 and type(logs) is list and 1<=len(logs)<=12)
    identity=None;previous_close=cutoff;previous_sender=None
    totals=Counter();snapshots=[]
    for raw in logs:
        diagnostic=parse(raw)
        row=json.loads(raw)
        need(row["mode"]=="REALTIME_LOCAL_LOG")
        close=row["snapshot_close_ms"];opened=row["snapshot_open_ms"]
        sender=row["sender_clock_ms"]
        need(close%300000==0 and close-opened==300000 and close>previous_close)
        need(previous_sender is None or sender>previous_sender)
        signature=tuple(row[k] for k in IDENTITY)+(diagnostic["configuration_digest"],)
        if identity is None:identity=signature
        need(identity==signature)
        gap=(close-previous_close)//300000-1
        totals["elapsed_grid_slots_missing"]+=gap
        previous_close=close;previous_sender=sender
        present=[r for r in row["levels"] if r["price"] is not None]
        # Same reported origin close on same chart is ONE origin group even if
        # price/method differs: disagreement is retained, not extra evidence.
        grouped={}
        for level in present:
            grouped.setdefault(level["peak_origin_close_ms"],[]).append(level)
        shared=sum(len(g)>1 for g in grouped.values())
        conflict=sum(len({Decimal(x["price"]) for x in g})>1 for g in grouped.values())
        snapshot={"close_ms":close,"present_slots":len(present),"missing_slots":6-len(present),
            "origin_groups":len(grouped),"shared_origin_groups":shared,
            "same_origin_price_disagreement_groups":conflict,
            "sender_minus_close_ms":sender-close,"elapsed_grid_slots_missing_before":gap}
        snapshots.append(snapshot)
        for k in ("present_slots","missing_slots","origin_groups","shared_origin_groups",
                  "same_origin_price_disagreement_groups"):
            totals[k]+=snapshot[k]
    return {"schema":"remura.tv.level.local.batch.diagnostic.v1","status":"UNATTESTED_LOCAL_LOG_SEQUENCE",
        "symbol":"FX:EURUSD","rows":len(snapshots),"declared_cutoff_ms":cutoff,
        "configuration_digest":identity[-1],"snapshots":snapshots,"totals":dict(totals),
        "continuous_elapsed_grid":totals["elapsed_grid_slots_missing"]==0,
        "source_attested":False,"receipt_authenticated":False,"calendar_equivalence_attested":False,
        "prospective_admission":False,"comparison_admitted":False,
        "independent_sources_established":False,"operational_signal":False}
